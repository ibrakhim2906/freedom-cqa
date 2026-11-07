"""Recompute the fixed v2 experiment from preserved artifacts; makes no API calls."""

import argparse
import json

from cqa.datasets import load_cases
from cqa.models import Checklist, Conversation, Evaluation
from cqa.rubric import load_checklist
from cqa.scoring import validate_evaluation
from cqa.settings import ROOT


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def report():
    folder = ROOT / "artifacts/reliability-v2"
    first, organizer, repeats = [read(folder / name) for name in
                                ["first-pass.json", "organizer-results.json", "repeats.json"]]
    cases = {c.id: c for c in load_cases(ROOT / "evals/reliability-v2.jsonl")}
    cases.update({c.id: c for c in load_cases(folder / "organizer.jsonl")})
    all_records, phases = [], {}
    for name, run in [("fresh_and_regression", first), ("organizer_cli", organizer), ("repeats", repeats)]:
        records = [r["record"] for r in run["rows"]]
        phases[name] = round(sum(r["usage"]["estimated_cost_usd"] for r in records), 6)
        for row in run["rows"]:
            case = cases[row["case_id"]]
            validate_evaluation(Evaluation.model_validate(row["record"]["evaluation"]), case.conversation,
                                case.checklist_override or load_checklist(), require_audit=True)
        all_records.extend(records)
    for name, uid in [("organizer_browser", "8b9493c6-d61f-4fb3-8199-dc33494e40e8"),
                      ("original_failure_browser", "59161e50-f815-438b-9b72-12965374ae86")]:
        job = read(folder / f"evaluation-{uid}.json")
        record = job["record"]
        validate_evaluation(Evaluation.model_validate(record["evaluation"]),
            Conversation.model_validate(job["conversation"]["content"]),
            Checklist.model_validate(job["checklist"]["content"]), require_audit=True)
        phases[name] = record["usage"]["estimated_cost_usd"]
        all_records.append(record)
    replay = read(folder / "repair-replay.json")["record"]
    prior = cases["regression-browser-41"]
    validate_evaluation(Evaluation.model_validate(replay["evaluation"]), prior.conversation,
                        load_checklist(), require_audit=True)
    phases["historical_repair_replay"] = replay["usage"]["estimated_cost_usd"]
    all_records.append(replay)
    preflight = read(folder / "evaluation-646b0161-622d-43a5-872e-07fb0c0dd807.json")["record"]
    assert preflight["attempt_count"] == 0 and preflight["usage"] is None
    fresh = [r for r in first["rows"] if r["case_id"].startswith("fresh-")]
    fresh_checks = [check for row in fresh for check in row["comparison"]["checks"]]
    consistency, matched = [], 0
    for row in repeats["rows"]:
        original = next(r for r in first["rows"] if r["case_id"] == row["case_id"])["record"]
        repeated = row["record"]
        assert original["request_fingerprint"] == repeated["request_fingerprint"]
        before = {j["criterion_id"]: j for j in original["evaluation"]["judgments"]}
        changes = []
        for judgment in repeated["evaluation"]["judgments"]:
            prior = before[judgment["criterion_id"]]
            if (prior["status"], prior["answer"]) == (judgment["status"], judgment["answer"]):
                matched += 1
            else:
                changes.append({"criterion_id": judgment["criterion_id"], "before": prior["answer"],
                                "after": judgment["answer"]})
        consistency.append({"case_id": row["case_id"], "changes": changes,
                            "before_score": original["score"]["total"], "after_score": repeated["score"]["total"]})
    return {
        "reference_warning": "Frozen assistant-authored expectations, not independent organizer Ground Truth",
        "fresh_cases": len(fresh), "fresh_completed": sum(r["record"]["status"] == "completed" for r in fresh),
        "frozen_fresh_matched": sum(c["matched"] for c in fresh_checks), "frozen_fresh_declared": len(fresh_checks),
        "frozen_mismatches": [{"case_id": r["case_id"], **c} for r in fresh for c in r["comparison"]["checks"]
                              if not c["matched"]],
        "historical_failure_regression": first["rows"][-1]["comparison"],
        "valid_paid_evaluations": len(all_records),
        "first_pass_calls_excluding_historical_repair_replay": len(all_records) - 1,
        "automatic_repairs_needed_in_new_runs": sum(r["attempt_count"] - 1 for r in all_records),
        "numeric_output_count": sum(r["score"]["total"] is not None for r in all_records),
        "provisional_output_count": sum(r["score"]["provisional"] for r in all_records),
        "repeat_matching_judgments": matched, "repeat_total_judgments": 16, "repeat_details": consistency,
        "zero_call_preflight_verified": True, "cost_by_phase_usd": phases,
        "total_estimated_cost_usd": round(sum(phases.values()), 6),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    path = (ROOT / args.output).resolve()
    if not path.is_relative_to((ROOT / "artifacts").resolve()) or path.exists():
        raise ValueError("Use a new file inside ignored artifacts/; never overwrite run evidence")
    value = report()
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: value[k] for k in ["fresh_completed", "frozen_fresh_matched", "frozen_fresh_declared",
        "valid_paid_evaluations", "repeat_matching_judgments", "repeat_total_judgments", "total_estimated_cost_usd"]}))


if __name__ == "__main__":
    main()

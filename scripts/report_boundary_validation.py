"""Recompute boundary-014/015 evidence and promotion checks; no API calls."""

import argparse
import json

from cqa.datasets import load_cases
from cqa.models import Checklist, Conversation, Evaluation
from cqa.rubric import load_checklist
from cqa.scoring import validate_evaluation
from cqa.settings import ROOT


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def vector(record):
    return {j["criterion_id"]: (j["status"], j["answer"]) for j in record["evaluation"]["judgments"]}


def initial_request(record):
    return record["attempt_records"][0]["request_fingerprint"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()) or output.exists():
        raise ValueError("Write a new file in artifacts/; preserve earlier evidence")
    v3, v4 = ROOT / "artifacts/boundary-v3", ROOT / "artifacts/boundary-v4"
    baseline = read(v3 / "baseline.json")
    continuation = read(v3 / "baseline-continuation.json")
    deferred = {r["case_id"] for r in baseline["rows"] if r["record"]["status"] == "skipped_budget"}
    assert deferred == {r["case_id"] for r in continuation["rows"]}
    base_rows = [r for r in baseline["rows"] if r["record"]["status"] == "completed"] + continuation["rows"]
    files = [*sorted(v3.glob("*.json")), *sorted(v4.glob("*.json"))]
    runs = [(p, read(p)) for p in files if not p.name.startswith("evaluation-")]
    runs = [(p, d) for p, d in runs if "rows" in d]
    total_cost = sum(d["summary"]["estimated_known_cost_usd"] for _, d in runs)
    final_runs = [(p, d) for p, d in runs if p.parent == v4]
    final_rows = [r for _, d in final_runs for r in d["rows"]]
    for path, data in final_runs:
        cases = {c.id: c for c in load_cases(path.with_suffix(".suite.jsonl"))}
        for row in data["rows"]:
            c = cases[row["case_id"]]
            assert row["record"]["status"] == "completed"
            validate_evaluation(Evaluation.model_validate(row["record"]["evaluation"]), c.conversation,
                                load_checklist(ROOT / "checklists/freedom-reviewed-015.json"), require_audit=True)
    first = read(v4 / "v3-regression.json")["rows"]
    original = {r["case_id"]: r["record"] for r in first}
    matches, comparisons, drifts = 0, 0, []
    for n in [1, 2]:
        for row in read(v4 / f"repeat-{n}.json")["rows"]:
            before, after = original[row["case_id"]], row["record"]
            assert initial_request(before) == initial_request(after)
            a, b = vector(before), vector(after)
            matches += sum(a[k] == b[k] for k in a)
            comparisons += len(a)
            drifts.append(abs(before["score"]["total"] - after["score"]["total"]))
    old = [read(v4 / f"old-regression-{n}.json")["rows"][0]["record"] for n in [1, 2, 3]]
    assert len({initial_request(r) for r in old}) == 1
    old_scores = [r["score"]["total"] for r in old]
    reserved_checks = [c for r in read(v4 / "reserved-first.json")["rows"] for c in r["comparison"]["checks"]]
    final_checks = [c for r in final_rows for c in r["comparison"]["checks"]]
    ui = []
    for uid in ["524fb3e3-ed8f-419f-adc2-7d717c32c4bb", "6df17903-c7c2-4e59-82f4-ebb4ea9cb016"]:
        job = read(v4 / f"evaluation-{uid}.json")
        record = job["record"]
        validate_evaluation(Evaluation.model_validate(record["evaluation"]),
            Conversation.model_validate(job["conversation"]["content"]),
            Checklist.model_validate(job["checklist"]["content"]), require_audit=True)
        reference = original.get(record["conversation_id"])
        if reference is None:
            reference = next(r for r in read(v4 / "reserved-first.json")["rows"]
                             if r["case_id"] == record["conversation_id"])["record"]
        assert vector(record) == vector(reference)
        ui.append(record)
        total_cost += record["usage"]["estimated_cost_usd"]
    records = [r["record"] for r in final_rows] + ui
    all_checks_correct = all(c["matched"] for c in final_checks)
    promoted = all_checks_correct and matches / comparisons >= .95 and len(set(old_scores)) == 1
    result = {"label_warning": "Assistant-authored and team-reviewed development labels, not independent Ground Truth",
        "baseline_completed_matching": sum(c["matched"] for r in base_rows for c in r["comparison"]["checks"]),
        "baseline_completed_declared": 32, "baseline_zero_call_deferrals_preserved": len(deferred),
        "new_reserved_matching": sum(c["matched"] for c in reserved_checks), "new_reserved_declared": len(reserved_checks),
        "final_cli_matching": sum(c["matched"] for c in final_checks), "final_cli_declared": len(final_checks),
        "repeat_matching": matches, "repeat_comparisons": comparisons, "maximum_repeat_score_drift": max(drifts),
        "old_regression_scores": old_scores, "final_assessments_including_ui": len(records),
        "first_attempt_valid": sum(r["attempt_records"][0]["status"] == "completed" for r in records),
        "inference_attempts_final_candidate": sum(r["attempt_count"] for r in records),
        "all_final_valid": all(r["status"] == "completed" for r in records), "promoted_015": promoted,
        "phase_costs": {str(p.relative_to(ROOT)): d["summary"]["estimated_known_cost_usd"] for p, d in runs},
        "browser_cost_usd": round(sum(r["usage"]["estimated_cost_usd"] for r in ui), 6),
        "total_estimated_cost_usd": round(total_cost, 6)}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "phase_costs"}))


if __name__ == "__main__":
    main()

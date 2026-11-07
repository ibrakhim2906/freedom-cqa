"""Reproduce the core experiment summary without altering or selecting outputs."""

import argparse
import json
from pathlib import Path

from cqa.metrics import summarize
from cqa.models import Evaluation
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score
from cqa.settings import ROOT
from scripts.compare_benchmarks import compare


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def repeat_stability(baseline, repeat):
    comparison = compare(baseline, repeat)
    old = {r["case_id"]: r for r in baseline["rows"]}
    checked, matched, same_request, score_drifts = 0, 0, 0, []
    for row in repeat["rows"]:
        before, after = old[row["case_id"]]["record"], row["record"]
        if before["status"] != "completed" or after["status"] != "completed":
            raise ValueError("Stability requires completed paired results; report failures separately")
        if before["request_fingerprint"] != after["request_fingerprint"]:
            raise ValueError("Repeat changed the actual inference request")
        same_request += 1
        a = {j["criterion_id"]: (j["status"], j["answer"]) for j in before["evaluation"]["judgments"]}
        b = {j["criterion_id"]: (j["status"], j["answer"]) for j in after["evaluation"]["judgments"]}
        if set(a) != set(b):
            raise ValueError("Repeat has different criterion coverage")
        checked += len(a)
        matched += sum(a[c] == b[c] for c in a)
        if before["score"]["total"] != after["score"]["total"]:
            score_drifts.append({"case_id": row["case_id"], "before": before["score"]["total"],
                                 "after": after["score"]["total"]})
    return {"identical_request_pairs": same_request, "judgments_checked": checked,
            "judgments_unchanged": matched, "observed_stability": matched / checked if checked else None,
            "changes": comparison["judgment_changes"], "score_drifts": score_drifts,
            "warning": "One repeat per case; not a population stability estimate."}


def summarize_run(report):
    rows = report["rows"]
    checks = [c for r in rows for c in r["comparison"]["checks"]]
    errors = [r["comparison"]["total_absolute_error"] for r in rows
              if r["comparison"]["total_absolute_error"] is not None]
    return {"cases": len(rows), "complete": report["complete"], "checks": len(checks),
            "matched": sum(c["matched"] for c in checks), "full_score_vectors": len(errors),
            "score_mae": sum(errors) / len(errors) if errors else None,
            "cost_usd": report["summary"]["estimated_known_cost_usd"],
            "p95_latency_seconds": report["summary"]["p95_latency_seconds"],
            "api_attempts": sum(r["record"].get("attempt_count", 0) for r in rows)}


def report(directory):
    baseline = read(directory / "direct-baseline.json")
    candidate = read(directory / "evidence-first.json")
    repeat = read(directory / "direct-repeat.json")
    stress = read(directory / "direct-stress.json")
    continuation = read(directory / "direct-stress-continuation.json")
    runs = {"baseline": baseline, "candidate": candidate, "repeat": repeat,
            "stress_first_segment": stress, "stress_continuation": continuation}
    if not all(d["complete"] for k, d in runs.items() if k != "stress_first_segment"):
        raise ValueError("Do not issue a complete experiment report for incomplete runs")
    deferred = {r["case_id"] for r in stress["rows"] if r["record"]["status"] == "skipped_budget"}
    if deferred != {r["case_id"] for r in continuation["rows"]}:
        raise ValueError("Continuation must cover exactly the unattempted budget deferrals")
    original_cases = {c["id"]: c for c in [json.loads(line) for line in
                      (directory / "direct-stress.suite.jsonl").read_text(encoding="utf-8").splitlines()]}
    for line in (directory / "direct-stress-continuation.suite.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        if case != original_cases[case["id"]]:
            raise ValueError("Continuation changed a frozen case or its reference")
    stress_rows = [r for r in stress["rows"] if r["case_id"] not in deferred] + continuation["rows"]
    if any(r["record"]["status"] != "completed" for r in stress_rows):
        raise ValueError("Every stress case must complete; no best-result selection")
    paired = compare(baseline, candidate)
    rubric = load_checklist(str(directory / "checklist.json"))
    old = ROOT / "artifacts/benchmark/calibrated-v3"
    organizer = []
    for filename in ["pilot-results.json", "remaining-results.json"]:
        for row in read(old / filename)["rows"]:
            record = row["record"]
            if row["source"] != "organizer" or not record["score"]["provisional"]:
                continue
            recalculated = calculate_score(Evaluation.model_validate(record["evaluation"]), rubric)
            if recalculated["total"] != record["score"]["total"]:
                raise ValueError("Adding bounds must not choose a point score for uncertainty")
            organizer.append({"case_id": row["case_id"], "unresolved": recalculated["unresolved_criteria"],
                              "score_bounds": recalculated["score_bounds"]})
    result = {"warning": "AI-authored provisional references; not organizer Ground Truth accuracy.",
              "runs": {k: summarize_run(v) for k, v in runs.items()},
              "stress_completed": summarize(stress_rows),
              "stress_segment_source_hashes": [stress["evaluator_source_sha256"], continuation["evaluator_source_sha256"]],
              "stress_segment_note": "Only the unattempted reservation deferral was continued. Source versions differ "
                                     "after an evidence-first budget-error bookkeeping fix. "
                                     "Direct inference instructions, schema, validation and scoring were unchanged.",
              "candidate_judgment_changes": paired["judgment_changes"],
              "repeat_stability": repeat_stability(baseline, repeat),
              "organizer_uncertainty": organizer,
              "cost_usd": round(sum(r["summary"]["estimated_known_cost_usd"] for r in runs.values()), 6),
              "promotion_decision": "Retain direct default: no observed accuracy gain from evidence-first anchors.",
              "ledger": continuation["ledger"]}
    if result["cost_usd"] > 1.0:
        raise ValueError("Core experiment exceeded its predeclared $1 budget")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=ROOT / "artifacts/benchmark/core-v4")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if not target.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Report must stay in ignored artifacts/")
    result = report(args.directory)
    with target.open("x", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "organizer_uncertainty"}, indent=2))


if __name__ == "__main__":
    main()

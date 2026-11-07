"""Compare preserved first outcomes and a declared schema-fix recheck; no calls."""

import hashlib
import json

from cqa.datasets import load_cases
from cqa.ledger import Ledger
from cqa.models import Evaluation
from cqa.output_contract import decode_evaluation
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT, Settings

BASE = ROOT / "artifacts/claim-dependencies-v1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def vector(record):
    if record.get("evaluation"):
        result = record["evaluation"]
    elif record.get("raw_output_text"):
        result = decode_evaluation(record["raw_output_text"]).model_dump()
    else:
        return {}
    return {j["criterion_id"]: (j["status"], j["answer"]) for j in result["judgments"]}


def main():
    baseline, first, recheck = [read(BASE / name) for name in
                                ["paired-baseline.json", "focused-candidate.json", "role-constrained.json"]]
    organizer = read(ROOT / "artifacts/organizer-65-v1/merged.json")
    old_rows = {r["case_id"]: r for report in [baseline, organizer] for r in report["rows"]}
    selected = {r["case_id"]: r for r in first["rows"]}
    assert {r["case_id"] for r in recheck["rows"]} == {
        "p1-ru-018", "clarity-recovery-corrected", "timing-dependent-unknown"}
    for row in recheck["rows"]:
        previous = selected[row["case_id"]]["record"]
        if row["case_id"] == "p1-ru-018":
            assert previous["status"] == "failed" and previous["validation_reason"] == "Audit source has the wrong speaker role"
            assert first["evaluator_source_sha256"] != recheck["evaluator_source_sha256"]
        else:
            assert previous["status"] == "skipped_budget" and not previous.get("attempt_records")
        selected[row["case_id"]] = row
    cases = {c.id: c for c in load_cases(BASE / "focused-candidate.suite.jsonl")}
    for c in load_cases(BASE / "role-constrained.suite.jsonl"):
        assert c == cases[c.id]
    for path in [BASE / "paired-baseline.suite.jsonl", ROOT / "artifacts/organizer-65-v1/merged.suite.jsonl"]:
        for case in load_cases(path):
            if case.id in cases:
                assert case == cases[case.id], "Input or frozen provisional labels changed"
    checklist = load_checklist(ROOT / "checklists/freedom-reviewed-015.json")
    rows = []
    for cid, row in selected.items():
        rec, old = row["record"], old_rows[cid]["record"]
        if rec["status"] == "completed":
            result = Evaluation.model_validate(rec["evaluation"])
            assert all(c.assessment is not None for c in result.factual_claims)
            validate_evaluation(result, cases[cid].conversation, cases[cid].checklist_override or checklist,
                                require_audit=True)
            assert calculate_score(result, cases[cid].checklist_override or checklist) == rec["score"]
        previous, current = vector(old), vector(rec)
        rows.append({"case_id": cid, "source": row["source"], "old_status": old["status"],
                     "first_candidate_status": next(r["record"]["status"] for r in first["rows"] if r["case_id"] == cid),
                     "final_status": rec["status"], "score": rec.get("score"),
                     "judgments": current,
                     "old_rejected_candidate_comparison_not_reference": old["status"] != "completed",
                     "changed_judgments": [{"criterion": k, "old": previous.get(k), "new": v}
                                           for k, v in current.items() if previous.get(k) != v],
                     "checks": row["comparison"]["checks"], "validation_reason": rec.get("validation_reason")})
    attempts = [a for report in [baseline, first, recheck] for row in report["rows"]
                for a in row["record"].get("attempt_records", [])]
    ids = [a["ledger_call_id"] for a in attempts]
    assert len(ids) == len(set(ids))
    known_cost = round(sum((a.get("usage") or {}).get("estimated_cost_usd", 0) for a in attempts), 6)
    settings = Settings.load()
    ledger = Ledger(settings.ledger_path, settings.max_spend)
    with ledger.connect() as db:
        settled = [db.execute("SELECT cost FROM usage WHERE id=?", (cid,)).fetchone()[0] for cid in ids]
    assert all(c is not None for c in settled)
    assert abs(sum(settled) - known_cost) < 0.000002
    old_paired = [old_rows[r["case_id"]] for r in rows if r["source"] == "authored"]
    before_checks = [c for r in old_paired for c in r["comparison"]["checks"]]
    after_checks = [c for r in rows if r["source"] == "authored" for c in r["checks"]]
    summary = {"warning": "Provisional assistant-authored labels and source review, not independent organizer GT.",
               "focused_cases": len(rows), "final_completed": sum(r["final_status"] == "completed" for r in rows),
               "paired_checks_before": {"matched": sum(c["matched"] for c in before_checks), "checked": len(before_checks)},
               "paired_checks_after": {"matched": sum(c["matched"] for c in after_checks), "checked": len(after_checks)},
               "organizer_failures_before": 4,
               "organizer_completed_after": sum(r["source"] == "organizer" and r["final_status"] == "completed" for r in rows),
               "first_candidate_statuses": first["summary"]["statuses"],
               "cost_baseline_usd": baseline["summary"]["estimated_known_cost_usd"],
               "cost_first_candidate_usd": first["summary"]["estimated_known_cost_usd"],
               "cost_schema_recheck_usd": recheck["summary"]["estimated_known_cost_usd"],
               "total_known_cost_usd": known_cost,
               "unknown_cost_attempts": sum(a.get("usage") is None and a.get("settled_cost_usd") is None for a in attempts),
               "selection_policy": "All initial outcomes retained. Only one failed case retested after a source-role schema fix; two deferred cases had no earlier request.",
               "rows": rows}
    summary["files"] = [{"file": name, "sha256": hashlib.sha256((BASE / name).read_bytes()).hexdigest()}
                        for name in ["paired-baseline.json", "focused-candidate.json", "role-constrained.json"]]
    (BASE / "report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in {"rows", "files"}}, indent=2))


if __name__ == "__main__":
    main()

"""Revalidate saved organizer results and create a private, source-linked review index.

No API calls, label changes, or evaluator modifications are performed.
"""

import hashlib
import json
from collections import Counter

from cqa.datasets import load_cases
from cqa.ledger import Ledger
from cqa.models import Evaluation
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT, Settings

BASE = ROOT / "artifacts/organizer-65-v1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    report, protocol = read(BASE / "merged.json"), read(BASE / "protocol.json")
    source = ROOT / "data/private/dev.json"
    checklist_path = ROOT / "checklists/freedom-reviewed-015.json"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == protocol["original_source_sha256"]
    assert hashlib.sha256(checklist_path.read_bytes()).hexdigest() == protocol["checklist_sha256"]
    assert hashlib.sha256(b"\n".join(
        p.read_bytes() for p in sorted((ROOT / "cqa").glob("*.py")))).hexdigest() == report["evaluator_source_sha256"]
    cases = {c.id: c for c in load_cases(BASE / "merged.suite.jsonl")}
    notes = read(BASE / "manual-review.json")
    assert len(notes["rows"]) == len(cases) == 65
    reviews = {r["case_id"]: r for r in notes["rows"]}
    assert set(reviews) == set(cases) == {r["case_id"] for r in report["rows"]}
    checklist = load_checklist(checklist_path)
    settings = Settings.load()
    ledger = Ledger(settings.ledger_path, settings.max_spend)
    status, criterion_reviews, claim_states = Counter(), Counter(), Counter()
    groups, index, attempts = {}, [], []
    for row in report["rows"]:
        cid, rec = row["case_id"], row["record"]
        case = cases[cid]
        assert set(reviews[cid]["source_ids"]) <= {m.id for m in case.conversation.messages}
        assert rec.get("attempt_count", 0) > 0
        current_attempts = rec["attempt_records"]
        attempts.extend(current_attempts)
        if rec["status"] == "completed":
            evaluation = Evaluation.model_validate(rec["evaluation"])
            validate_evaluation(evaluation, case.conversation, checklist, require_audit=True)
            assert calculate_score(evaluation, checklist) == rec["score"]
            outcome = "provisional" if rec["score"]["provisional"] else "numeric"
            criterion_reviews.update(j.criterion_id for j in evaluation.judgments if j.status == "needs_review")
            claim_states.update(c.status for c in evaluation.factual_claims if c.material)
        else:
            outcome = "failed"
        status[outcome] += 1
        for group in [row["language"], row["channel"]]:
            groups.setdefault(group, Counter())[outcome] += 1
        score = rec.get("score") or {}
        judgments = (rec.get("evaluation") or {}).get("judgments", [])
        index.append({"case_id": cid, "language": row["language"], "channel": row["channel"],
                      "outcome": outcome, "total": score.get("total"),
                      "serious": score.get("flags", {}).get("serious"),
                      "unresolved": score.get("unresolved_criteria", []),
                      "judgments": [{k: j[k] for k in ["criterion_id", "status", "answer"]} for j in judgments],
                      "validation_reason": rec.get("validation_reason"), "manual_review": reviews[cid]})
    call_ids = [a["ledger_call_id"] for a in attempts]
    assert len(call_ids) == len(set(call_ids)), "A paid attempt was counted more than once"
    with ledger.connect() as db:
        costs = [db.execute("SELECT cost FROM usage WHERE id=?", (cid,)).fetchone()[0] for cid in call_ids]
    assert all(cost is not None for cost in costs), "Unknown provider charge; keep reservation visible"
    assert abs(sum(costs) - report["summary"]["estimated_known_cost_usd"]) < 0.000002
    checks = [c for r in report["rows"] for c in r["comparison"]["checks"]]
    repaired = [r["case_id"] for r in report["rows"] if r["record"]["status"] == "completed"
                and any(a.get("error", "").startswith("invalid_evaluation_")
                        for a in r["record"]["attempt_records"] if a.get("error"))]
    audit = {"source_review_provenance": notes["reviewer"], "outcomes": dict(status),
             "groups": groups, "unresolved_criteria": dict(criterion_reviews),
             "material_claim_statuses": dict(claim_states), "all_cases_submitted": True,
             "reviewed_source_transcripts": len(reviews), "revalidated_assessments": 65 - status["failed"],
             "provider_requests": len(attempts), "paid_responses": sum(c > 0 for c in costs),
             "provider_rejected_zero_cost": sum(a.get("billing_state") == "provider_rejected" for a in attempts),
             "repaired_completed_ids": repaired,
             "first_output_valid": sum(r["record"]["attempt_records"][0]["status"] == "completed" for r in report["rows"]),
             "known_cost_usd": round(sum(costs), 6), "unknown_cost_attempts": 0,
             "provisional_label_comparison": {"checked": len(checks), "matched": sum(c["matched"] for c in checks),
                  "warning": "Sparse AI-authored development labels, not organizer Ground Truth or independent accuracy",
                  "mismatches": [{"case_id": r["case_id"], **c} for r in report["rows"]
                                 for c in r["comparison"]["checks"] if not c["matched"]]},
             "cases": index}
    (BASE / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in audit.items() if k != "cases"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

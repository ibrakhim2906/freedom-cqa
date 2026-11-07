from collections import Counter, defaultdict

from .models import Evaluation, Judgment, TestCase
from .scoring import calculate_score


def compare_case(case: TestCase, record, checklist):
    predictions = {j["criterion_id"]: j for j in (record.get("evaluation") or {}).get("judgments", [])}
    comparisons = []
    for expected in case.expectations:
        actual = predictions.get(expected.criterion_id)
        matched = bool(actual and actual["status"] == expected.status and actual["answer"] == expected.answer)
        comparisons.append({"criterion_id": expected.criterion_id, "matched": matched,
                            "expected_status": expected.status, "expected_answer": expected.answer,
                            "actual_status": actual["status"] if actual else None,
                            "actual_answer": actual["answer"] if actual else None})
    full_reference = {x.criterion_id for x in case.expectations} == {c.id for c in checklist.criteria}
    total_error = None
    reference_total = None
    if full_reference:
        reference = Evaluation(judgments=[Judgment(criterion_id=x.criterion_id, status=x.status,
            answer=x.answer, explanation=x.rationale, evidence=[], counterevidence=[],
            checked_message_ids=[], uncertainty=None) for x in case.expectations],
            request_coverage=[], scope_notes=[])
        reference_total = calculate_score(reference, checklist)["total"]
        actual_total = (record.get("score") or {}).get("total")
        if reference_total is not None and actual_total is not None:
            total_error = abs(actual_total - reference_total)
    return {"checks": comparisons, "full_reference": full_reference,
            "reference_total": reference_total, "total_absolute_error": total_error}


def summarize(rows):
    statuses = Counter(r["record"]["status"] for r in rows)
    groups = defaultdict(list)
    for row in rows:
        groups[row["source"]].append(row)
    def group_summary(items):
        attempted = [r for r in items if r["record"]["status"] != "skipped_budget"]
        completed = [r for r in attempted if r["record"]["status"] == "completed"]
        checks = [c for r in attempted for c in r["comparison"]["checks"]]
        completed_checks = [c for r in completed for c in r["comparison"]["checks"]]
        errors = [r["comparison"]["total_absolute_error"] for r in completed
                  if r["comparison"]["total_absolute_error"] is not None]
        per_criterion = {}
        for criterion in sorted({c["criterion_id"] for c in checks}):
            selected = [c for c in checks if c["criterion_id"] == criterion]
            per_criterion[criterion] = {"checked": len(selected), "matched": sum(c["matched"] for c in selected)}
        return {"selected": len(items), "attempted": len(attempted), "completed": len(completed),
                "expected_judgments_attempted": len(checks),
                "end_to_end_agreement": sum(c["matched"] for c in checks) / len(checks) if checks else None,
                "completed_only_agreement": sum(c["matched"] for c in completed_checks) / len(completed_checks)
                if completed_checks else None,
                "full_reference_score_cases": len(errors),
                "mean_total_absolute_error": sum(errors) / len(errors) if errors else None,
                "per_criterion": per_criterion,
                "no_na_confusions": sum(c["actual_status"] is not None and
                    {c["expected_status"], c["actual_status"]} == {"scored", "not_applicable"} for c in checks),
                "serious_false_negatives": sum(c["criterion_id"] == "serious" and
                    c["expected_answer"] == "yes" and c["actual_status"] == "scored" and
                    c["actual_answer"] == "no" for c in checks)}
    costs = [r["record"].get("usage", {}).get("estimated_cost_usd", 0)
             for r in rows if r["record"].get("usage")]
    latencies = sorted(r["record"]["latency_seconds"] for r in rows if "latency_seconds" in r["record"])
    return {"case_count": len(rows), "statuses": dict(statuses),
            "label_warning": "Agreement with AI-authored provisional expectations, NOT organizer Ground Truth accuracy.",
            "by_source": {k: group_summary(v) for k, v in groups.items()},
            "by_language": {lang: group_summary([r for r in rows if r["language"] == lang])
                            for lang in sorted({r["language"] for r in rows})},
            "by_channel": {ch: group_summary([r for r in rows if r["channel"] == ch])
                           for ch in sorted({r["channel"] for r in rows})},
            "estimated_known_cost_usd": round(sum(costs), 6),
            "unknown_cost_attempts": sum(r["record"]["status"] == "failed" and not r["record"].get("usage") for r in rows),
            "p95_latency_seconds": latencies[max(0, int(len(latencies) * .95 + .999999) - 1)] if latencies else None}

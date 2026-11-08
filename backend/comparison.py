"""Compare saved effective assessments without inference or causal attribution."""

from decimal import Decimal


def compare_evaluations(before_detail, after_detail):
    """Compare original/reviewed results currently effective in two job details.

    Criterion contributions are the scorer's saved points before N/A normalization,
    not an attribution of the normalized total delta. A changed rule and a changed
    answer can coexist; this helper does not claim one caused the other.
    """
    snapshots = []
    for detail in (before_detail, after_detail):
        effective = detail.get("effective")
        if effective is None:
            raise ValueError("Both evaluations need a saved effective result before comparison")
        criteria = detail["checklist"]["content"]["criteria"]
        configured = {criterion["id"]: criterion for criterion in criteria}
        judgments = {judgment["criterion_id"]: judgment for judgment in effective["judgments"]}
        if len(configured) != len(criteria) or len(judgments) != len(effective["judgments"]) or (
            set(configured) != set(judgments)
        ):
            raise ValueError("Effective judgments must match their saved checklist exactly")
        contributions = {item["criterion_id"]: item["points"]
                         for item in effective["score"]["contributions"]}
        snapshots.append((configured, judgments, contributions, effective))

    before_rules, before_judgments, before_points, before_effective = snapshots[0]
    after_rules, after_judgments, after_points, after_effective = snapshots[1]
    criterion_ids = list(before_rules) + [cid for cid in after_rules if cid not in before_rules]

    def side(cid, rules, judgments, contributions):
        if cid not in rules:
            return None
        judgment = judgments[cid]
        return {"status": judgment["status"], "answer": judgment["answer"],
                "contribution": contributions.get(cid), "explanation": judgment["explanation"],
                "uncertainty": judgment.get("uncertainty")}

    rows = []
    for cid in criterion_ids:
        before = side(cid, before_rules, before_judgments, before_points)
        after = side(cid, after_rules, after_judgments, after_points)
        rows.append({
            "criterion_id": cid, "title": (after_rules.get(cid) or before_rules[cid])["title"],
            "before": before, "after": after,
            "outcome_changed": (before is None or after is None or
                                (before["status"], before["answer"]) != (after["status"], after["answer"])),
            "rule_changed": before_rules.get(cid) != after_rules.get(cid),
            "added": cid not in before_rules, "removed": cid not in after_rules,
        })

    before_score = before_effective["score"]["total"]
    after_score = after_effective["score"]["total"]
    def numeric(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    delta = (float(Decimal(str(after_score)) - Decimal(str(before_score)))
             if numeric(before_score) and numeric(after_score) else None)
    before_source = before_detail["conversation"]["content"]
    after_source = after_detail["conversation"]["content"]
    transcript_keys = ("messages", "channel", "language")
    context_keys = ("references", "reference_context", "knowledge_scope", "occurred_on", "occurred_on_origin")
    return {
        "before_id": before_detail["id"], "after_id": after_detail["id"],
        "same_conversation": before_detail["conversation"]["external_id"] == after_detail["conversation"]["external_id"],
        "input_changed": before_detail["conversation"]["content_hash"] != after_detail["conversation"]["content_hash"],
        "source_changed": any(before_source.get(k) != after_source.get(k) for k in transcript_keys),
        "context_changed": any(before_source.get(k) != after_source.get(k) for k in context_keys),
        "checklist_changed": before_detail["checklist"]["content"] != after_detail["checklist"]["content"],
        "before_score": before_score, "after_score": after_score, "score_delta": delta,
        "before_provisional": bool(before_effective["score"].get("provisional")),
        "after_provisional": bool(after_effective["score"].get("provisional")),
        "before_result_source": before_effective["source"], "after_result_source": after_effective["source"],
        "criteria": rows,
    }

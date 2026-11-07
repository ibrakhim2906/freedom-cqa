"""Validate explicit grade dependencies and evidenced corrections.

Quotation, temporal ordering, allowed outcomes and internal consistency are
mechanical checks. Entailment and counterfactual correctness remain semantic
judgments; a plausible explanation is not independent expert validation.
"""

from .grounding import reference_applicable


def validate_claim_assessment(claim, conversation, criteria, judgments, check_quotes):
    assessment = claim.assessment
    messages = {m.id: m for m in conversation.messages}
    order = {m.id: i for i, m in enumerate(conversation.messages)}
    refs = {r.id: r for r in conversation.references}
    impacts = assessment.impacts
    ids = [i.criterion_id for i in impacts]
    if (len(claim.criterion_ids) != len(set(claim.criterion_ids))
            or len(ids) != len(set(ids)) or set(ids) != set(claim.criterion_ids)):
        raise ValueError("Claim impacts must cover each related criterion exactly once")

    correction = assessment.correction
    if (assessment.lifecycle == "corrected") != (correction is not None):
        raise ValueError("Corrected claims require a correction; active claims cannot carry one")
    if correction:
        if not correction.operator_evidence or not correction.explanation.strip():
            raise ValueError("Correction needs a later operator statement and consequence explanation")
        check_quotes(correction.operator_evidence, {"operator"})
        check_quotes(correction.outcome_evidence, {"client", "system"})
        last_original = max(order[e.message_id] for e in claim.operator_evidence)
        first_correction = min(order[e.message_id] for e in correction.operator_evidence)
        if first_correction <= last_original:
            raise ValueError("Correction must follow the original assertion")
        last_correction = max(order[e.message_id] for e in correction.operator_evidence)
        if any(order[e.message_id] <= last_correction for e in correction.outcome_evidence):
            raise ValueError("Independent outcome confirmation must follow the correction")
        for citation in correction.reference_evidence:
            ref = refs.get(citation.reference_id)
            if (ref is None or not citation.quote.strip() or citation.quote not in ref.text
                    or not reference_applicable(ref, conversation)):
                raise ValueError("Correction requires a verbatim applicable reference")
        if not (correction.outcome_evidence or correction.reference_evidence):
            raise ValueError("Operator self-correction alone does not independently establish recovery")

    for impact in impacts:
        criterion, judgment = criteria[impact.criterion_id], judgments[impact.criterion_id]
        rules = [criterion.instruction, *[x.description for x in criterion.levels],
                 *criterion.channel_guidance.values()]
        if not impact.rule_quote.strip() or not any(impact.rule_quote in text for text in rules):
            raise ValueError("Claim impact must quote its configured criterion rule verbatim")
        if not impact.explanation.strip() or not (impact.evidence or impact.checked_message_ids):
            raise ValueError("Claim impact requires a source-linked dependency explanation")
        check_quotes(impact.evidence)
        if any(mid not in messages for mid in impact.checked_message_ids):
            raise ValueError("Claim impact checked span references a nonexistent message")
        for outcome in [impact.when_true, impact.when_false]:
            if outcome.status == "scored":
                if outcome.answer not in {level.value for level in criterion.levels}:
                    raise ValueError("Claim impact outcome is not an allowed criterion level")
            elif outcome.answer is not None:
                raise ValueError("Unscored claim impact outcomes must have null answers")
            elif outcome.status == "not_applicable" and not criterion.na_condition:
                raise ValueError("Claim impact cannot invent N/A applicability")
        sensitive = impact.when_true != impact.when_false
        if sensitive and not claim.material:
            raise ValueError("A grade-changing claim must be marked material")
        if claim.status == "unverified" and sensitive:
            if judgment.status != "needs_review":
                raise ValueError("Grade-changing unverified claims require review of the dependent criterion")
            continue
        established = impact.when_false if claim.status == "contradicted" else impact.when_true
        # Another independent uncertainty may still prevent a final judgment.
        # This claim must never convert an unresolved alternative into certainty.
        if judgment.status == "needs_review":
            continue
        if (judgment.status, judgment.answer) != (established.status, established.answer):
            raise ValueError("Judgment conflicts with the claim's established conditional outcome")

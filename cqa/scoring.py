from decimal import ROUND_HALF_UP, Decimal

from .atomic_dependencies import validate_atomic_dependencies
from .claim_dependencies import validate_claim_assessment
from .grounding import reference_applicable
from .models import Checklist, Conversation, Evaluation
from .semantic_coverage import validate_semantic_coverage
from .span_transport import validate_source_citations


def validate_evaluation(result: Evaluation, conversation: Conversation, checklist: Checklist, *, require_audit=False):
    criteria = {c.id: c for c in checklist.criteria}
    ids = [j.criterion_id for j in result.judgments]
    if len(ids) != len(set(ids)) or set(ids) != set(criteria):
        raise ValueError("Judgments must cover each configured criterion exactly once")
    messages = {m.id: m for m in conversation.messages}
    for judgment in result.judgments:
        criterion = criteria[judgment.criterion_id]
        if not judgment.explanation.strip():
            raise ValueError("Every criterion requires a substantive explanation")
        if judgment.status == "scored":
            if judgment.answer not in {level.value for level in criterion.levels}:
                raise ValueError("Answer is not an allowed criterion level")
        else:
            if judgment.answer is not None:
                raise ValueError("N/A and needs-review answers must be null")
            if judgment.status == "not_applicable" and not criterion.na_condition:
                raise ValueError("N/A is forbidden for this criterion")
            if judgment.status == "needs_review" and not judgment.uncertainty:
                raise ValueError("Needs-review judgments must identify the uncertainty")
        if not (judgment.evidence or judgment.checked_message_ids):
            raise ValueError("Judgment needs source evidence or a checked omission span")
        for evidence in judgment.evidence + judgment.counterevidence:
            message = messages.get(evidence.message_id)
            if message is None or not evidence.quote.strip() or evidence.quote not in message.text:
                raise ValueError("Evidence quote must occur verbatim in the referenced original message")
        if any(mid not in messages for mid in judgment.checked_message_ids):
            raise ValueError("Checked span references a nonexistent message")
    for request in result.request_coverage:
        if not request.request.strip() or not request.explanation.strip():
            raise ValueError("Request coverage needs a substantive request and explanation")
        if not request.request_message_ids or any(
            mid not in messages or messages[mid].speaker != "client" for mid in request.request_message_ids
        ):
            raise ValueError("Request coverage must reference actual customer messages")
        if any(mid not in messages or messages[mid].speaker != "operator" for mid in request.answer_message_ids):
            raise ValueError("Request answers must reference operator messages")
        if request.status in {"answered", "next_step"} and not request.answer_message_ids:
            raise ValueError("An answered request or next step needs operator evidence")
        if any(mid not in messages or messages[mid].speaker != "client" for mid in request.withdrawal_message_ids):
            raise ValueError("Withdrawals must reference actual customer messages")
        if request.status == "withdrawn":
            if not request.withdrawal_message_ids:
                raise ValueError("A withdrawn request needs customer withdrawal evidence")
            order = {m.id: i for i, m in enumerate(conversation.messages)}
            if min(order[mid] for mid in request.withdrawal_message_ids) < min(
                order[mid] for mid in request.request_message_ids
            ):
                raise ValueError("Withdrawal cannot precede the request")
        elif request.withdrawal_message_ids:
            raise ValueError("Only withdrawn requests may have withdrawal evidence")
    validate_audit(result, conversation, checklist, require_audit=require_audit)
    validate_semantic_coverage(result, conversation, checklist)
    validate_source_citations(result, conversation, checklist)
    validate_atomic_dependencies(result, conversation, checklist)


def validate_audit(result, conversation, checklist, *, require_audit):
    criteria = {c.id: c for c in checklist.criteria}
    judgments = {j.criterion_id: j for j in result.judgments}
    messages = {m.id: m for m in conversation.messages}
    references = {r.id: r for r in conversation.references}

    def check_quotes(items, allowed_roles=None):
        for item in items:
            message = messages.get(item.message_id)
            if message is None or not item.quote.strip() or item.quote not in message.text:
                raise ValueError("Audit quote must occur verbatim in its source message")
            if allowed_roles is not None and message.speaker not in allowed_roles:
                raise ValueError("Audit source has the wrong speaker role")

    deducted = set()
    for item in result.deductions:
        if item.criterion_id in deducted:
            raise ValueError("Duplicate deduction audits for one criterion are not allowed")
        criterion = criteria.get(item.criterion_id)
        if criterion is None or not item.defect.strip() or not item.overlap_note.strip():
            raise ValueError("Deduction needs a configured criterion, defect and overlap explanation")
        rules = [criterion.instruction, *[x.description for x in criterion.levels],
                 *criterion.channel_guidance.values()]
        if not item.rule_quote.strip() or not any(item.rule_quote in text for text in rules):
            raise ValueError("Deduction must quote the configured criterion rule verbatim")
        judgment = judgments[item.criterion_id]
        if judgment.status != "scored" or criterion.kind == "flag":
            raise ValueError("Deduction audit only describes scored numeric deductions")
        level = next(x for x in criterion.levels if x.value == judgment.answer)
        if level.fraction == max(x.fraction for x in criterion.levels):
            raise ValueError("Maximum-level judgments cannot have a deduction")
        if not (item.evidence or item.checked_message_ids):
            raise ValueError("Deduction requires evidence or a checked omission span")
        check_quotes(item.evidence)
        if any(mid not in messages for mid in item.checked_message_ids):
            raise ValueError("Deduction checked span references a nonexistent message")
        deducted.add(item.criterion_id)
    if require_audit:
        for cid, judgment in judgments.items():
            criterion = criteria[cid]
            if criterion.kind == "flag" or judgment.status != "scored":
                continue
            level = next(x for x in criterion.levels if x.value == judgment.answer)
            if level.fraction < max(x.fraction for x in criterion.levels) and cid not in deducted:
                raise ValueError(f"Every numeric deduction requires a source-linked rule audit: {cid}")

    for claim in result.factual_claims:
        if not claim.claim.strip() or not claim.explanation.strip() or not claim.operator_evidence:
            raise ValueError("Factual claim needs a statement, explanation and operator source")
        if not claim.criterion_ids or any(cid not in criteria for cid in claim.criterion_ids):
            raise ValueError("Factual claim must identify its configured criterion impact")
        check_quotes(claim.operator_evidence, {"operator"})
        check_quotes(claim.dialogue_evidence, {"client", "system"})
        for citation in claim.reference_evidence:
            ref = references.get(citation.reference_id)
            if ref is None or not citation.quote.strip() or citation.quote not in ref.text:
                raise ValueError("Reference quote must occur verbatim in the supplied reference")
            if claim.status != "unverified" and not reference_applicable(
                ref, conversation, derive_dates=result.semantic_audit is not None
            ):
                raise ValueError("Out-of-scope or out-of-date source cannot verify a claim")
        for citation in claim.rule_evidence:
            criterion = criteria.get(citation.criterion_id)
            if criterion is None or citation.criterion_id not in claim.criterion_ids:
                raise ValueError("Rule evidence must identify a related configured criterion")
            rules = [criterion.instruction, *[x.description for x in criterion.levels],
                     *criterion.channel_guidance.values()]
            if not citation.quote.strip() or not any(citation.quote in text for text in rules):
                raise ValueError("Rule evidence must quote the supplied checklist verbatim")
        if claim.rule_evidence and claim.evidence_kind != "grading_rule":
            raise ValueError("Checklist rules cannot verify product or account facts")
        if claim.evidence_kind == "grading_rule" and not claim.rule_evidence:
            raise ValueError("A grading-rule claim needs its supplied rule source")
        commitment = (result.semantic_audit is not None and claim.evidence_kind == "workflow_commitment"
                      and claim.verification_scope == "commitment" and claim.status == "supported")
        if claim.status != "unverified" and not (
            claim.reference_evidence or claim.dialogue_evidence or claim.rule_evidence or commitment
        ):
            raise ValueError("Verified claims require reference or customer/system evidence")
        if claim.assessment is not None:
            validate_claim_assessment(claim, conversation, criteria, judgments, check_quotes,
                                      derive_dates=result.semantic_audit is not None)
            continue
        # Preserve validation semantics for frozen historical evaluations.
        if claim.material and claim.status == "unverified" and any(
            judgments[cid].status != "needs_review" for cid in claim.criterion_ids
        ):
            raise ValueError("Material unverified claims require review of the dependent criteria")
        if claim.material and claim.status == "contradicted":
            for cid in claim.criterion_ids:
                criterion, judgment = criteria[cid], judgments[cid]
                if criterion.kind != "flag" and judgment.status == "scored":
                    level = next(x for x in criterion.levels if x.value == judgment.answer)
                    if level.fraction == max(x.fraction for x in criterion.levels):
                        raise ValueError("Material contradicted claims cannot receive full credit in dependent criteria")


def calculate_score(result: Evaluation, checklist: Checklist):
    judgments = {j.criterion_id: j for j in result.judgments}
    earned, applicable = Decimal(0), Decimal(0)
    unresolved, recommended, flags, contributions = [], [], {}, []
    for criterion in checklist.criteria:
        judgment = judgments[criterion.id]
        if judgment.status != "needs_review" and judgment.uncertainty:
            recommended.append(criterion.id)
        if criterion.kind == "flag":
            flags[criterion.id] = judgment.answer if judgment.status == "scored" else judgment.status
            continue
        if judgment.status == "not_applicable":
            contributions.append({"criterion_id": criterion.id, "status": judgment.status, "points": None})
            continue
        weight = Decimal(str(criterion.weight))
        applicable += weight
        if judgment.status == "needs_review":
            unresolved.append(criterion.id)
            points = None
        else:
            level = next(x for x in criterion.levels if x.value == judgment.answer)
            points = weight * Decimal(str(level.fraction))
            earned += points
        contributions.append({"criterion_id": criterion.id, "status": judgment.status,
                              "points": float(points) if points is not None else None})
    total = None
    if applicable and not unresolved:
        total = float((100 * earned / applicable).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return {"total": total, "provisional": bool(unresolved or recommended), "unresolved_criteria": unresolved,
            **({"review_recommended_criteria": recommended} if recommended else {}),
            "applicable_weight": float(applicable), "earned_points": float(earned),
            "flags": flags, "contributions": contributions,
            "score_bounds": score_bounds(result, checklist)}


def score_bounds(result: Evaluation, checklist: Checklist):
    """Allowed-outcome envelope, not a probability interval or a finalized score.

    For an unresolved N/A-eligible criterion, include both exclusion and every
    allowed level. A weighted-average optimum includes optional items in order of
    their fractions, so testing sorted prefixes avoids exponential enumeration.
    """
    judgments = {j.criterion_id: j for j in result.judgments}
    fixed_points, fixed_weight = Decimal(0), Decimal(0)
    mandatory, optional = [], []
    for criterion in checklist.criteria:
        judgment = judgments[criterion.id]
        if criterion.kind == "flag" or (judgment.status == "not_applicable" and not judgment.uncertainty):
            continue
        weight = Decimal(str(criterion.weight))
        if judgment.status == "scored" and not judgment.uncertainty:
            level = next(x for x in criterion.levels if x.value == judgment.answer)
            fixed_points += weight * Decimal(str(level.fraction))
            fixed_weight += weight
        elif weight:
            fractions = [Decimal(str(x.fraction)) for x in criterion.levels]
            (optional if criterion.na_condition else mandatory).append((weight, min(fractions), max(fractions)))

    def extremum(upper):
        index = 2 if upper else 1
        points = fixed_points + sum((item[0] * item[index] for item in mandatory), Decimal(0))
        weight = fixed_weight + sum((item[0] for item in mandatory), Decimal(0))
        candidates = [points / weight] if weight else []
        for item in sorted(optional, key=lambda x: x[index], reverse=upper):
            weight += item[0]
            points += item[0] * item[index]
            candidates.append(points / weight)
        if not candidates:
            return None
        value = max(candidates) if upper else min(candidates)
        return float((100 * value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return {"lower": extremum(False), "upper": extremum(True),
            "no_numeric_score_possible": fixed_weight == 0 and not mandatory,
            "meaning": "Envelope of allowed uncertain outcomes, including N/A where permitted; not confidence."}

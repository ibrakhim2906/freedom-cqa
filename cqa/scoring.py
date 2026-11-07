from decimal import ROUND_HALF_UP, Decimal

from .models import Checklist, Conversation, Evaluation


def validate_evaluation(result: Evaluation, conversation: Conversation, checklist: Checklist):
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


def calculate_score(result: Evaluation, checklist: Checklist):
    judgments = {j.criterion_id: j for j in result.judgments}
    earned, applicable = Decimal(0), Decimal(0)
    unresolved, flags, contributions = [], {}, []
    for criterion in checklist.criteria:
        judgment = judgments[criterion.id]
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
    return {"total": total, "provisional": bool(unresolved), "unresolved_criteria": unresolved,
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
        if criterion.kind == "flag" or judgment.status == "not_applicable":
            continue
        weight = Decimal(str(criterion.weight))
        if judgment.status == "scored":
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
            "meaning": "Envelope of allowed unresolved outcomes, including N/A where permitted; not confidence."}

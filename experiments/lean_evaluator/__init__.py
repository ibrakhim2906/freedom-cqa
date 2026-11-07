"""Pure experimental evaluator. No API client and no production strategy hook.

Validation establishes structural/source consistency, not semantic entailment or
complete material-claim/request discovery. Native records never masquerade as v5.
"""

import json

from jsonschema import Draft202012Validator, ValidationError

from cqa.grounding import reference_applicable
from cqa.models import Checklist, Conversation, Evaluation, Evidence, Judgment
from cqa.prompt import payload_for
from cqa.scoring import calculate_score
from cqa.source_spans import build_catalog
from cqa.source_view import project_sources

from .contract import CONTRACT, CONTRACT_HASH, LeanAssessment
from .prompt import PROMPT_HASH, PROMPT_VERSION, SYSTEM

__all__ = ["CONTRACT", "CONTRACT_HASH", "PROMPT_HASH", "PROMPT_VERSION", "LeanAssessment", "common_view", "decode",
           "prepare", "schema_for", "score", "validate"]


def _inputs(conversation, checklist):
    # model_copy/model_construct can bypass validators; do not trust caller provenance.
    return (Conversation.model_validate(conversation.model_dump()),
            Checklist.model_validate(checklist.model_dump()))


def schema_for(conversation, checklist):
    """Strict whole-document schema; criterion IDs remain values, never object keys."""
    schema = LeanAssessment.model_json_schema()
    ids = [criterion.id for criterion in checklist.criteria]
    schema["$defs"]["Judgment"]["properties"]["criterion_id"]["enum"] = ids
    for field in ("criterion_ids", "uncertain_criterion_ids"):
        schema["$defs"]["Fact"]["properties"][field]["items"]["enum"] = ids
    return schema


def prepare(conversation, checklist):
    """Return instructions, unchanged full-source JSON view, strict schema, output cap."""
    conversation, checklist = _inputs(conversation, checklist)
    catalog = build_catalog(conversation, checklist)
    payload = json.loads(payload_for(conversation, checklist, grounded=True))
    payload = project_sources(payload, conversation, checklist, catalog)
    payload["output_contract"] = CONTRACT
    return SYSTEM, json.dumps(payload, ensure_ascii=False, sort_keys=True), schema_for(conversation, checklist), 6000


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("Non-finite JSON number: " + value)


def _shape(value, conversation, checklist):
    try:
        Draft202012Validator(schema_for(conversation, checklist)).validate(value)
    except ValidationError as error:
        path = "/" + "/".join(str(part) for part in error.absolute_path)
        raise ValueError(f"Lean schema rejection at {path}: {error.message}") from error


def decode(text, conversation, checklist):
    """Reject the entire malformed document before resolving a single citation."""
    value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    _shape(value, conversation, checklist)
    result = LeanAssessment.model_validate(value, strict=True)
    validate(result, conversation, checklist)
    return result


def _unique(values, label):
    if len(values) != len(set(values)):
        raise ValueError("Duplicate links in " + label)


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " needs substantive text")


def _grades(result, checklist):
    criteria = {c.id: c for c in checklist.criteria}
    ids = [j.criterion_id for j in result.judgments]
    _unique(ids, "judgments")
    if set(ids) != set(criteria):
        raise ValueError("Judgments must cover every configured criterion exactly once")
    judgments = {j.criterion_id: j for j in result.judgments}
    for judgment in result.judgments:
        criterion = criteria[judgment.criterion_id]
        _text(judgment.explanation, "Judgment explanation")
        if judgment.status == "scored":
            levels = {level.value: level for level in criterion.levels}
            if judgment.answer not in levels:
                raise ValueError("Answer is not an allowed configured level")
            below = (criterion.kind != "flag" and levels[judgment.answer].fraction <
                     max(level.fraction for level in criterion.levels))
        else:
            below = False
            if judgment.answer is not None:
                raise ValueError("Non-scored answer must be null")
            if judgment.status == "not_applicable" and not criterion.na_condition:
                raise ValueError("N/A is forbidden for this criterion")
            if judgment.status == "needs_review":
                _text(judgment.uncertainty, "Needs-review uncertainty")
        if judgment.uncertainty is not None:
            _text(judgment.uncertainty, "Uncertainty")
        if below != (judgment.deduction is not None):
            raise ValueError("Exactly below-max numeric grades require a rule-linked deduction")
        if judgment.deduction is not None:
            _text(judgment.deduction.defect, "Deduction defect")
            _text(judgment.deduction.overlap_note, "Deduction overlap note")
    for fact in result.facts:
        _unique(fact.criterion_ids, "fact criteria")
        _unique(fact.uncertain_criterion_ids, "uncertain criteria")
        if not fact.criterion_ids or not set(fact.criterion_ids) <= set(criteria):
            raise ValueError("Fact requires related configured criteria")
        if not set(fact.uncertain_criterion_ids) <= set(fact.criterion_ids):
            raise ValueError("Uncertain criteria must be a subset of related criteria")
        if fact.status != "unverified" and fact.uncertain_criterion_ids:
            raise ValueError("Known facts cannot have unresolved grade dependencies")
        if any(judgments[cid].status != "needs_review" for cid in fact.uncertain_criterion_ids):
            raise ValueError("Grade-changing unknown requires needs_review")
        recovered = (fact.correction is not None and
                     fact.correction.remaining_consequences == "none_established")
        if fact.status == "contradicted" and not recovered:
            for cid in fact.criterion_ids:
                criterion, judgment = criteria[cid], judgments[cid]
                if criterion.kind != "flag" and judgment.status == "scored":
                    level = next(x for x in criterion.levels if x.value == judgment.answer)
                    if level.fraction == max(x.fraction for x in criterion.levels):
                        raise ValueError("Material wrong advice cannot receive full credit without recovery")
    return criteria, judgments


def validate(result, conversation, checklist):
    """Validate native structure, source roles, applicability and explicit grade links.

    Actor/route/time entailment and exhaustiveness of semantic inventory still need
    review. This intentionally makes no stronger automated-proof claim.
    """
    # Revalidate whole shape even for direct callers supplying a constructed model.
    value = result.model_dump(mode="json")
    _shape(value, conversation, checklist)
    result = LeanAssessment.model_validate(value, strict=True)
    conversation, checklist = _inputs(conversation, checklist)
    _grades(result, checklist)
    catalog = build_catalog(conversation, checklist)
    catalog.assert_sources(conversation, checklist)
    if result.catalog_fingerprint != catalog.fingerprint:
        raise ValueError("Catalog fingerprint does not match unchanged sources")
    messages = conversation.messages
    order = {m.id: i for i, m in enumerate(messages)}
    human_ids = [m.id for m in messages if m.speaker in {"client", "operator"}]
    if result.reviewed_message_ids != human_ids:
        raise ValueError("Reviewed human-message list must be complete and source-ordered")
    references = {r.id: r for r in conversation.references}

    def resolve(span_id, kind, roles=None, criterion_id=None):
        catalog.resolve(span_id, kind=kind, roles=roles, criterion_id=criterion_id)
        return catalog.entries[span_id]

    def links(ids, kind, roles=None, criterion_id=None):
        _unique(ids, "source spans")
        return [resolve(sid, kind, roles, criterion_id) for sid in ids]

    def interval(item, *, start=None):
        if item is None:
            raise ValueError("Omission requires an exhaustive source-ordered interval")
        if item.start_message_id not in order or item.end_message_id not in order:
            raise ValueError("Omission interval references nonexistent messages")
        left, right = order[item.start_message_id], order[item.end_message_id]
        if left > right or right != len(messages) - 1:
            raise ValueError("Omission interval is reversed or omits later opportunity")
        if start is not None and left != start:
            raise ValueError("Omission interval must start at the linked opportunity")
        if item.message_ids != [m.id for m in messages[left:right + 1]]:
            raise ValueError("Omission interval must list every source-ordered message")
        return left, right

    for judgment in result.judgments:
        evidence = links(judgment.evidence_span_ids, "dialogue")
        links(judgment.counterevidence_span_ids, "dialogue")
        resolve(judgment.rule_span_id, "rule", criterion_id=judgment.criterion_id)
        if not evidence and judgment.omission is None:
            raise ValueError("Judgment needs dialogue evidence or checked omission opportunity")
        if judgment.omission is not None:
            interval(judgment.omission)

    request_keys = set()
    for request in result.request_coverage:
        _text(request.request, "Request")
        _text(request.explanation, "Request explanation")
        asks = links(request.request_span_ids, "dialogue", {"client"})
        answers = links(request.answer_span_ids, "dialogue", {"operator"})
        withdrawals = links(request.withdrawal_span_ids, "dialogue", {"client"})
        if not asks:
            raise ValueError("Request requires actual client evidence")
        key = (request.request, tuple(request.request_span_ids))
        if key in request_keys:
            raise ValueError("Duplicate request coverage")
        request_keys.add(key)
        first_ask = min(order[s.source_id] for s in asks)
        if any(order[s.source_id] <= first_ask for s in answers + withdrawals):
            raise ValueError("Answer/withdrawal must follow the linked request")
        if request.status in {"answered", "next_step", "partial"} and not answers:
            raise ValueError("Positive/partial request coverage needs human answer evidence")
        if request.status in {"unanswered", "withdrawn"} and answers:
            raise ValueError("Unanswered/withdrawn coverage cannot supply answer evidence")
        if (request.status == "withdrawn") != bool(withdrawals):
            raise ValueError("Only withdrawn requests require withdrawal evidence")
        if request.status in {"partial", "unanswered"}:
            interval(request.omission, start=first_ask)
        elif request.omission is not None:
            raise ValueError("Positive/withdrawn requests cannot carry omission support")

    for fact in result.facts:
        _text(fact.claim, "Atomic fact")
        _text(fact.explanation, "Fact explanation")
        operators = links(fact.operator_source_span_ids, "dialogue", {"operator"})
        if not operators:
            raise ValueError("Fact requires operator assertion source")
        _unique(fact.proof_source_span_ids, "truth proof")
        _unique(fact.context_source_span_ids, "fact context")
        for sid in fact.context_source_span_ids:
            entry = catalog.entries.get(sid)
            if entry is None:
                raise ValueError("Unknown context source")
            resolve(sid, entry.kind)
        if fact.status == "unverified":
            if fact.proof_source_span_ids or fact.negative_interval is not None or fact.correction is not None:
                raise ValueError("Unverified facts have no truth proof or established correction")
            continue
        if not fact.proof_source_span_ids:
            raise ValueError("Known facts require independent truth proof")
        proof = []
        for sid in fact.proof_source_span_ids:
            if fact.kind == "policy":
                span = resolve(sid, "reference")
                if not reference_applicable(references[span.source_id], conversation, derive_dates=True):
                    raise ValueError("Policy truth source is out of date or scope")
            elif fact.kind in {"interaction", "private_state"}:
                span = resolve(sid, "dialogue", {"system"} if fact.kind == "private_state" else {"client", "system"})
            elif fact.kind == "commitment":
                if fact.status != "supported":
                    raise ValueError("Commitment records only the supported observable promise")
                span = resolve(sid, "dialogue", {"operator"})
                if sid not in fact.operator_source_span_ids:
                    raise ValueError("Commitment proof must be the linked operator promise")
            else:
                span = resolve(sid, "rule")
                if span.source_id not in fact.criterion_ids:
                    raise ValueError("Grading-rule truth needs a related configured rule")
            proof.append(span)
        if fact.negative_interval is not None:
            if fact.kind not in {"interaction", "private_state"}:
                raise ValueError("Broader negative intervals apply only to observed state/interaction")
            initial = min(order[s.source_id] for s in proof)
            interval(fact.negative_interval, start=initial)
        if fact.correction is not None:
            if fact.status != "contradicted":
                raise ValueError("Correction must retain the original contradicted advice")
            correction = fact.correction
            _text(correction.explanation, "Correction explanation")
            revised = links(correction.correction_span_ids, "dialogue", {"operator"})
            recovery = links(correction.recovery_span_ids, "dialogue", {"client", "system"})
            if not revised or not recovery:
                raise ValueError("Correction requires explicit correction and independent later recovery")
            last_assertion = max(order[s.source_id] for s in operators)
            first_correction = min(order[s.source_id] for s in revised)
            last_correction = max(order[s.source_id] for s in revised)
            if first_correction <= last_assertion or any(order[s.source_id] <= last_correction for s in recovery):
                raise ValueError("Correction/recovery chronology is invalid")
    for note in result.scope_notes:
        _text(note, "Scope note")
    return result


def _common(result, checklist, evidence_for):
    _grades(result, checklist)
    return Evaluation(judgments=[Judgment(
        criterion_id=j.criterion_id, status=j.status, answer=j.answer,
        explanation=j.explanation, evidence=evidence_for(j.evidence_span_ids),
        counterevidence=evidence_for(j.counterevidence_span_ids),
        checked_message_ids=j.omission.message_ids if j.omission else [], uncertainty=j.uncertainty,
    ) for j in result.judgments], request_coverage=[], scope_notes=[
        "Lean candidate score-only projection; not a span-v5 audit. See native assessment for facts and requests."
    ])


def common_view(result, conversation, checklist):
    """Read-only score/judgment projection; deliberately no fabricated v5 audit."""
    validate(result, conversation, checklist)
    catalog = build_catalog(conversation, checklist)

    def evidence(ids):
        return [Evidence(**catalog.resolve(sid, kind="dialogue")) for sid in ids]

    return _common(result, checklist, evidence)


def score(result, checklist):
    """Common deterministic score after native decode/validation; no hidden rewriting."""
    return calculate_score(_common(result, checklist, lambda ids: []), checklist)

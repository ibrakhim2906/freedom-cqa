import json

import pytest

from cqa.datasets import load_cases
from cqa.evaluator import schema_for
from cqa.grounding import attach_reference_pack, reference_applicable
from cqa.models import Deduction, Evaluation, Evidence, FactualClaim, Judgment, Reference, ReferenceEvidence
from cqa.prompt import PROMPT_VERSION, payload_for
from cqa.rubric import load_checklist
from cqa.scoring import validate_evaluation
from cqa.settings import ROOT


def fixtures():
    case = next(c for c in load_cases(ROOT / "evals/targeted-v5.jsonl") if c.id == "facts-profile-supported")
    rubric = load_checklist(ROOT / "checklists/freedom-reviewed-013.json")
    result = Evaluation(judgments=[Judgment(criterion_id=c.id, status="scored", answer=c.levels[0].value,
        explanation="Observed", evidence=[], counterevidence=[], checked_message_ids=["m1", "m2"],
        uncertainty=None) for c in rubric.criteria], request_coverage=[], scope_notes=[])
    # The serious flag is independent and is not a numeric deduction.
    next(j for j in result.judgments if j.criterion_id == "serious").answer = "no"
    result.factual_claims = [FactualClaim(claim="The route opens the data change request.",
        criterion_ids=["consultation"], operator_evidence=[Evidence(message_id="m2", quote="Open Menu")],
        status="supported", material=True, reference_evidence=[ReferenceEvidence(
            reference_id=case.conversation.references[0].id, quote="Изменение сведений")],
        dialogue_evidence=[], explanation="Applicable official platform reference")]
    return case.conversation.model_copy(deep=True), rubric, result


@pytest.mark.parametrize("scope,on,usable", [
    ("fbroker-kz-platform", "2026-11-07", True), ("other-company", "2026-11-07", False),
    (None, "2026-11-07", False), ("fbroker-kz-platform", None, False),
    ("fbroker-kz-platform", "2025-01-01", False), ("fbroker-kz-platform", "2027-01-01", False)])
def test_source_selection_is_bound_to_explicit_scope_and_date(scope, on, usable):
    conversation, rubric, result = fixtures()
    conversation.knowledge_scope, conversation.occurred_on = scope, on
    ref = conversation.references[0]
    assert reference_applicable(ref, conversation) == usable
    assert (ref.id in json.loads(payload_for(conversation, rubric, grounded=True))["usable_reference_ids"]) == usable
    if usable:
        validate_evaluation(result, conversation, rubric, require_audit=True)
    else:
        with pytest.raises(ValueError, match="Out-of-scope or out-of-date"):
            validate_evaluation(result, conversation, rubric, require_audit=True)


@pytest.mark.parametrize("defect", ["quote", "invented_reference", "operator_self_proof", "missing_proof"])
def test_unsubstantiated_factual_support_is_rejected(defect):
    conversation, rubric, result = fixtures()
    claim = result.factual_claims[0]
    if defect == "quote":
        claim.reference_evidence[0].quote = "Withdrawal is guaranteed in ten minutes."
    elif defect == "invented_reference":
        claim.reference_evidence[0].reference_id = "not-supplied"
    elif defect == "operator_self_proof":
        claim.reference_evidence = []
        claim.dialogue_evidence = claim.operator_evidence
    else:
        claim.reference_evidence = []
    with pytest.raises(ValueError):
        validate_evaluation(result, conversation, rubric, require_audit=True)


def test_unverified_is_not_automatically_wrong_and_only_dependent_criterion_requires_review():
    conversation, rubric, result = fixtures()
    claim = result.factual_claims[0]
    claim.status, claim.reference_evidence = "unverified", []
    with pytest.raises(ValueError, match="Material unverified"):
        validate_evaluation(result, conversation, rubric, require_audit=True)
    judgment = next(j for j in result.judgments if j.criterion_id == "consultation")
    judgment.status, judgment.answer, judgment.uncertainty = "needs_review", None, "No usable source"
    validate_evaluation(result, conversation, rubric, require_audit=True)
    assert next(j for j in result.judgments if j.criterion_id == "management").answer == "10"


def test_deductions_need_real_criterion_rules_but_independent_overlaps_are_allowed():
    conversation, rubric, result = fixtures()
    result.factual_claims = []
    for cid, answer in [("consultation", "10"), ("management", "4")]:
        judgment = next(j for j in result.judgments if j.criterion_id == cid)
        judgment.answer = answer
        with pytest.raises(ValueError, match="Every numeric deduction"):
            validate_evaluation(result, conversation, rubric, require_audit=True)
        criterion = next(c for c in rubric.criteria if c.id == cid)
        result.deductions.append(Deduction(criterion_id=cid, rule_quote=criterion.levels[-1].description,
            defect="Different independently applicable defect", evidence=[], checked_message_ids=["m1", "m2"],
            overlap_note="Same span, but missing content and unclear wording are different defects."))
    validate_evaluation(result, conversation, rubric, require_audit=True)
    result.deductions[-1].rule_quote = "Invented rule: deduct twice for every unanswered question"
    with pytest.raises(ValueError, match="quote the configured"):
        validate_evaluation(result, conversation, rubric, require_audit=True)


def test_reference_pack_cannot_silently_assign_another_context_or_duplicate_sources():
    conversation, _, _ = fixtures()
    path = ROOT / "references/fbroker-platform-20261107.json"
    with pytest.raises(ValueError, match="overwrite"):
        attach_reference_pack(conversation, path, "fbroker-kz-platform", "2026-11-08")
    with pytest.raises(ValueError, match="match"):
        attach_reference_pack(conversation, path, "another-company", "2026-11-07")
    with pytest.raises(ValueError, match="unique"):
        attach_reference_pack(conversation, path, "fbroker-kz-platform", "2026-11-07")


@pytest.mark.parametrize("value", ["20261107", "2026-W45-6", "2026-02-30", ""])
def test_ambiguous_dates_cannot_bypass_lexical_scope_checks(value):
    with pytest.raises(ValueError):
        Reference(id="r", text="Source", provenance="Test", valid_from=value)


def test_legacy_contract_remains_available_and_grounded_schema_is_strict():
    conversation, rubric, _ = fixtures()
    original = schema_for(conversation, rubric)
    candidate = schema_for(conversation, rubric, grounded=True)
    assert PROMPT_VERSION == "evaluator-v2-452e92fc403a"
    assert set(original["properties"]) == {"judgments", "request_coverage", "scope_notes"}
    assert "factual_claims" in candidate["required"]
    assert "deductions" not in candidate["properties"]  # Audits now belong to their exact judgment.
    assert candidate["properties"]["judgments"]["required"] == [c.id for c in rubric.criteria]
    assert "usable_reference_ids" not in json.loads(payload_for(conversation, rubric))
    for definition in [candidate, *candidate["$defs"].values()]:
        if definition.get("type") == "object":
            assert set(definition["required"]) == set(definition["properties"])
            assert definition["additionalProperties"] is False

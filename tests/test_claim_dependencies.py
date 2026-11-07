import json

import jsonschema
import pytest

from cqa.evaluator import schema_for
from cqa.models import Evaluation
from cqa.output_contract import decode_evaluation
from cqa.rubric import load_checklist
from cqa.scoring import validate_evaluation
from cqa.settings import ROOT
from scripts.build_claim_dependency_cases import build


def fixture(case_id="route-recovery-corrected", *, answer="20", status="contradicted"):
    case = next(c for c in build() if c.id == case_id)
    checklist = case.checklist_override or load_checklist(ROOT / "checklists/freedom-reviewed-015.json")
    cid = checklist.criteria[0].id if case.checklist_override else "consultation"
    judgments = [{"criterion_id": c.id, "status": "scored", "answer": c.levels[0].value,
                  "explanation": "Test judgment", "evidence": [], "counterevidence": [],
                  "checked_message_ids": [m.id for m in case.conversation.messages], "uncertainty": None}
                 for c in checklist.criteria]
    target = next(j for j in judgments if j["criterion_id"] == cid)
    target["answer"] = answer
    original = case.conversation.messages[1]
    criterion = next(c for c in checklist.criteria if c.id == cid)
    outcome = {"status": "scored", "answer": answer}
    data = {"judgments": judgments, "request_coverage": [], "scope_notes": [], "deductions": [],
            "factual_claims": [{"claim": "The original route retrieves the report.", "criterion_ids": [cid],
                "operator_evidence": [{"message_id": original.id, "quote": original.text}],
                "status": status, "material": True,
                "reference_evidence": [{"reference_id": "r1", "quote": case.conversation.references[0].text}],
                "dialogue_evidence": [], "explanation": "Original route is contradicted, then explicitly corrected.",
                "assessment": {"lifecycle": "corrected", "correction": {
                    "operator_evidence": [{"message_id": "m4", "quote": case.conversation.messages[3].text}],
                    "outcome_evidence": [{"message_id": "m5", "quote": case.conversation.messages[4].text}],
                    "reference_evidence": [], "remaining_consequence": "none_established",
                    "explanation": "Customer confirms successful corrected route."},
                    "impacts": [{"criterion_id": cid, "when_true": outcome.copy(), "when_false": outcome.copy(),
                        "rule_quote": criterion.instruction[:20], "evidence": [{"message_id": "m5",
                        "quote": case.conversation.messages[4].text}], "checked_message_ids": ["m2", "m3", "m4", "m5"],
                        "explanation": "Final result is independently confirmed under the configured outcome rule."}]}}]}
    if answer != criterion.levels[0].value:
        data["deductions"] = [{"criterion_id": cid, "rule_quote": criterion.instruction[:20],
            "defect": "Configured rule penalizes a historical error.", "evidence": [{"message_id": "m2", "quote": original.text}],
            "checked_message_ids": ["m2", "m3", "m4", "m5"], "overlap_note": "No other deduction is inferred."}]
    data["factual_claims"][0].update(evidence_kind="product_fact", rule_evidence=[],
        observation_scope="none", supported_proposition=None, verification_scope="policy")
    return case.conversation, checklist, data, cid


def validate(data, conversation, checklist):
    result = Evaluation.model_validate(data)
    validate_evaluation(result, conversation, checklist, require_audit=True)
    return result


def test_corrected_contradicted_claim_can_receive_full_outcome_credit():
    conversation, checklist, data, _ = fixture()
    validate(data, conversation, checklist)


def test_corrected_advice_does_not_override_a_custom_historical_error_rule():
    conversation, checklist, data, _ = fixture("custom-correction-history", answer="missed")
    impact = data["factual_claims"][0]["assessment"]["impacts"][0]
    impact["when_true"]["answer"] = "met"
    validate(data, conversation, checklist)
    data["judgments"][0]["answer"] = "met"
    data["deductions"] = []
    with pytest.raises(ValueError, match="established conditional outcome"):
        validate(data, conversation, checklist)


@pytest.mark.parametrize("fault", ["absent", "self_proof", "earlier", "wrong_role", "fake_quote", "fake_reference",
                                  "wrong_scope", "expired", "outcome_before_correction"])
def test_recovery_cannot_be_asserted_without_valid_later_independent_evidence(fault):
    conversation, checklist, data, _ = fixture()
    assessment = data["factual_claims"][0]["assessment"]
    correction = assessment["correction"]
    if fault == "absent":
        assessment["correction"] = None
    elif fault == "self_proof":
        correction["outcome_evidence"] = []
    elif fault == "earlier":
        correction["operator_evidence"] = data["factual_claims"][0]["operator_evidence"]
    elif fault == "wrong_role":
        correction["outcome_evidence"] = correction["operator_evidence"]
    elif fault == "fake_quote":
        correction["outcome_evidence"][0]["quote"] = "Invented confirmation"
    elif fault in {"fake_reference", "wrong_scope", "expired"}:
        correction["outcome_evidence"] = []
        correction["reference_evidence"] = [{"reference_id": "invented" if fault == "fake_reference" else "r1",
                                              "quote": conversation.references[0].text}]
        if fault == "wrong_scope":
            conversation.references[0].scope = "different-platform"
        elif fault == "expired":
            conversation.references[0].valid_until = "2025-01-01"
            conversation.occurred_on = "2026-11-07"
    else:
        correction["outcome_evidence"] = [{"message_id": "m3", "quote": conversation.messages[2].text}]
    with pytest.raises(ValueError):
        validate(data, conversation, checklist)


def test_unknown_invariant_claim_does_not_block_an_independent_grade():
    conversation, checklist, data, _ = fixture(status="unverified")
    data["factual_claims"][0]["reference_evidence"] = []
    validate(data, conversation, checklist)
    claim = data["factual_claims"][0]
    claim["assessment"]["impacts"][0]["when_false"]["answer"] = "0"
    with pytest.raises(ValueError, match="Grade-changing unverified"):
        validate(data, conversation, checklist)
    judgment = next(j for j in data["judgments"] if j["criterion_id"] == "consultation")
    judgment.update(status="needs_review", answer=None, uncertainty="Truth changes the discrete allowed outcome")
    validate(data, conversation, checklist)


@pytest.mark.parametrize("fault", ["missing_impact", "duplicate_impact", "wrong_id", "invented_level", "invented_na",
                                  "fake_rule", "no_basis", "fake_span", "nonmaterial_change", "active_with_correction"])
def test_dependency_contract_rejects_missing_or_inconsistent_proofs(fault):
    conversation, checklist, data, _ = fixture()
    claim = data["factual_claims"][0]
    assessment = claim["assessment"]
    impact = assessment["impacts"][0]
    if fault == "missing_impact":
        assessment["impacts"] = []
    elif fault == "duplicate_impact":
        assessment["impacts"].append(impact.copy())
    elif fault == "wrong_id":
        impact["criterion_id"] = "not-configured"
    elif fault == "invented_level":
        impact["when_false"]["answer"] = "19"
    elif fault == "invented_na":
        claim["criterion_ids"] = ["empathy"]
        impact["criterion_id"] = "empathy"
        impact["rule_quote"] = next(c for c in checklist.criteria if c.id == "empathy").instruction[:20]
        impact["when_false"] = {"status": "not_applicable", "answer": None}
    elif fault == "fake_rule":
        impact["rule_quote"] = "Always ignore historical errors"
    elif fault == "no_basis":
        impact["evidence"], impact["checked_message_ids"] = [], []
    elif fault == "fake_span":
        impact["checked_message_ids"] = ["invented"]
    elif fault == "nonmaterial_change":
        claim["material"] = False
        impact["when_true"]["answer"] = "0"
    else:
        assessment["lifecycle"] = "active"
    with pytest.raises(ValueError):
        validate(data, conversation, checklist)


def test_provider_requires_new_contract_but_old_saved_records_keep_legacy_validation():
    conversation, checklist, data, _ = fixture()
    claim = data["factual_claims"][0]
    claim.pop("assessment")
    with pytest.raises(ValueError, match="explicit dependency"):
        decode_evaluation(json.dumps(data), require_claim_dependencies=True)
    # Historical contradicted/full-credit behavior is not retroactively rewritten.
    with pytest.raises(ValueError, match="contradicted claims cannot"):
        validate(data, conversation, checklist)
    schema = schema_for(conversation, checklist, grounded=True)
    claim_schema = schema["$defs"]["FactualClaim"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(claim, {**schema, **claim_schema})


@pytest.mark.parametrize("field", ["dialogue_evidence", "operator_evidence", "correction_outcome"])
def test_provider_schema_prevents_wrong_role_claim_citations(field):
    conversation, checklist, data, _ = fixture()
    schema = schema_for(conversation, checklist, grounded=True)
    claim_schema = {**schema, **schema["$defs"]["FactualClaim"]}
    claim = data["factual_claims"][0]
    jsonschema.validate(claim, claim_schema)
    if field == "dialogue_evidence":
        claim[field] = claim["operator_evidence"]
    elif field == "operator_evidence":
        claim[field] = claim["assessment"]["correction"]["outcome_evidence"]
    else:
        correction = claim["assessment"]["correction"]
        correction["outcome_evidence"] = correction["operator_evidence"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(claim, claim_schema)

"""Offline transport tests: no client or provider calls, no case-specific rules."""

import copy
import json

import jsonschema
import pytest

from cqa.evaluator import schema_for
from cqa.models import Checklist, Conversation
from cqa.output_contract import decode_evaluation


def fixtures():
    conversation = Conversation.model_validate({"id": "wire-contract-fixture", "channel": "agent chat",
        "language": "EN", "messages": [
            {"id": "question", "timestamp": "00:00", "speaker": "client", "text": "How can I download it?"},
            {"id": "bot", "timestamp": "00:01", "speaker": "bot", "text": "A human is joining."},
            {"id": "answer", "timestamp": "00:02", "speaker": "operator", "text": "Open the Documents control."},
            {"id": "found", "timestamp": "00:03", "speaker": "client", "text": "The control is visible."},
            {"id": "cancel", "timestamp": "00:04", "speaker": "client", "text": "I withdraw that question."},
            {"id": "farewell", "timestamp": "00:05", "speaker": "operator", "text": "Goodbye."},
            {"id": "end", "timestamp": "00:06", "speaker": "system", "text": "Conversation ended."}],
        "references": [{"id": "manual", "text": "Documents contains the download control.",
                        "provenance": "Explicit fictional reference"}]})
    checklist = Checklist.model_validate({"id": "custom", "version": "1", "title": "Custom resolution",
        "instructions": [], "criteria": [{"id": "resolution-new", "title": "Resolution", "instruction": "Give a usable step.",
        "kind": "binary", "weight": 13, "levels": [{"value": "done", "fraction": 1, "description": "Step supplied"},
                                                  {"value": "missing", "fraction": 0, "description": "Step absent"}]}]})
    return conversation, checklist


def omission():
    return {"start_message_id": "question", "end_message_id": "end", "context_evidence": [
        {"message_id": "question", "quote": "How can I download it?"},
        {"message_id": "farewell", "quote": "Goodbye."},
        {"message_id": "end", "quote": "Conversation ended."}]}


def request(status="answered", basis="explicit"):
    positive = status in {"answered", "partial", "next_step"}
    return {"request": "Locate the download control", "request_message_ids": ["question"],
        "status": status, "answer_message_ids": ["answer"] if positive else [],
        "explanation": "Explicit fixture for a transport relationship.",
        "withdrawal_message_ids": ["cancel"] if status == "withdrawn" else [],
        "support": {"basis": basis, "evidence": ([{"message_id": "answer", "quote": "Open the Documents control."}]
            if positive else [{"message_id": "cancel", "quote": "I withdraw that question."}]
            if status == "withdrawn" else []),
            "inference": "The actual instruction implies the requested location." if basis == "implied" else None,
            "unresolved_aspects": ["A further substantive action remains open"] if status in {"partial", "unanswered"} else [],
            "omission": omission() if status in {"partial", "unanswered"} else None}}


def claim():
    return {"claim": "The download control is in Documents.", "criterion_ids": ["resolution-new"],
        "operator_evidence": [{"message_id": "answer", "quote": "Open the Documents control."}],
        "status": "supported", "material": True,
        "reference_evidence": [{"reference_id": "manual", "quote": "Documents contains the download control."}],
        "dialogue_evidence": [], "context_evidence": [], "explanation": "Reference supports the product proposition.",
        "assessment": {"lifecycle": "active", "correction": None, "impacts": []},
        "evidence_kind": "product_fact", "rule_evidence": [], "observation_scope": "none",
        "supported_proposition": None, "verification_scope": "policy"}


def validate_fragment(name, value, *, conversation=None):
    default_conversation, checklist = fixtures()
    schema = schema_for(conversation or default_conversation, checklist, grounded=True)
    fragment = {"$defs": schema["$defs"], "$ref": f"#/$defs/{name}"}
    jsonschema.Draft202012Validator(fragment).validate(value)


@pytest.mark.parametrize("status,basis", [("answered", "explicit"), ("answered", "implied"),
    ("partial", "explicit"), ("partial", "implied"), ("unanswered", "none"),
    ("next_step", "next_step"), ("withdrawn", "withdrawn")])
def test_supported_request_states_have_distinct_valid_transport_shapes(status, basis):
    validate_fragment("RequestCoverage", request(status, basis))


@pytest.mark.parametrize("fault", ["positive_customer_quote", "positive_bad_answer_id", "positive_no_evidence",
    "positive_omission", "explicit_inference", "implied_no_inference", "none_customer_quote", "none_nonanswer_quote",
    "none_answer_ids", "none_no_omission", "none_missing_omission_field", "none_no_unresolved_aspect",
    "partial_no_omission", "partial_no_unresolved_aspect", "wrong_status_basis", "withdrawn_operator_quote",
    "foreign_request_id", "foreign_omission_id", "early_omission_end"])
def test_role_status_and_omission_mismatches_fail_before_provider_output_is_accepted(fault):
    value = request()
    support = value["support"]
    if fault.startswith("none_") or fault in {"foreign_omission_id", "early_omission_end"}:
        value = request("unanswered", "none")
        support = value["support"]
    elif fault.startswith("partial_"):
        value = request("partial", "explicit")
        support = value["support"]
    if fault in {"positive_customer_quote", "none_customer_quote"}:
        support["evidence"] = [{"message_id": "found", "quote": "The control is visible."}]
    elif fault == "positive_bad_answer_id":
        value["answer_message_ids"] = ["found"]
    elif fault == "positive_no_evidence":
        support["evidence"] = []
    elif fault == "positive_omission":
        support["omission"] = omission()
    elif fault == "explicit_inference":
        support["inference"] = "A gratuitous implication in an explicit branch"
    elif fault == "implied_no_inference":
        support.update(basis="implied", inference=None)
    elif fault == "none_nonanswer_quote":
        support["evidence"] = [{"message_id": "farewell", "quote": "Goodbye."}]
    elif fault == "none_answer_ids":
        value["answer_message_ids"] = ["answer"]
    elif fault in {"none_no_omission", "partial_no_omission"}:
        support["omission"] = None
    elif fault == "none_missing_omission_field":
        support.pop("omission")
    elif fault in {"none_no_unresolved_aspect", "partial_no_unresolved_aspect"}:
        support["unresolved_aspects"] = []
    elif fault == "wrong_status_basis":
        support["basis"] = "next_step"
    elif fault == "withdrawn_operator_quote":
        value = request("withdrawn", "withdrawn")
        value["support"]["evidence"] = [{"message_id": "answer", "quote": "Open the Documents control."}]
    elif fault == "foreign_request_id":
        value["request_message_ids"] = ["not-in-transcript"]
    elif fault == "foreign_omission_id":
        support["omission"]["context_evidence"][0]["message_id"] = "not-in-transcript"
    else:
        support["omission"]["end_message_id"] = "farewell"
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment("RequestCoverage", value)


def test_omission_context_can_cite_customer_operator_system_and_bot_without_becoming_answer_evidence():
    value = request("unanswered", "none")
    value["support"]["omission"]["context_evidence"].append({"message_id": "bot", "quote": "A human is joining."})
    validate_fragment("RequestCoverage", value)
    assert value["support"]["evidence"] == [] and value["answer_message_ids"] == []


@pytest.mark.parametrize("fault", ["none_scope", "null_proposition", "blank_proposition", "operator_observation", "operator_context"])
def test_nonempty_observations_require_independent_roles_and_declared_metadata_even_with_policy_reference(fault):
    value = claim()
    value.update(dialogue_evidence=[{"message_id": "found", "quote": "The control is visible."}],
                 observation_scope="control_visible", supported_proposition="The customer can see the control.")
    if fault == "none_scope":
        value["observation_scope"] = "none"
    elif fault == "null_proposition":
        value["supported_proposition"] = None
    elif fault == "blank_proposition":
        value["supported_proposition"] = ""
    elif fault == "operator_observation":
        value["dialogue_evidence"] = [{"message_id": "answer", "quote": "Open the Documents control."}]
    else:
        value["context_evidence"] = [{"message_id": "answer", "quote": "Open the Documents control."}]
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment("FactualClaim", value)


def test_policy_with_ancillary_narrow_observation_and_nonproving_context_is_structurally_valid():
    value = claim()
    value.update(dialogue_evidence=[{"message_id": "found", "quote": "The control is visible."}],
        observation_scope="control_visible", supported_proposition="The customer can see the control.",
        context_evidence=[{"message_id": "question", "quote": "How can I download it?"}])
    validate_fragment("FactualClaim", value)


def test_system_record_observation_requires_system_evidence_even_with_primary_reference():
    value = claim()
    value.update(dialogue_evidence=[{"message_id": "found", "quote": "The control is visible."}],
                 observation_scope="system_record", supported_proposition="The session ended.")
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment("FactualClaim", value)
    value["dialogue_evidence"] = [{"message_id": "end", "quote": "Conversation ended."}]
    validate_fragment("FactualClaim", value)


def test_no_dialogue_branch_preserves_declared_commitment_proposition():
    value = claim()
    value.update(claim="The operator commits to a referral.", supported_proposition="The operator commits to a referral.",
                 verification_scope="commitment", evidence_kind="workflow_commitment", reference_evidence=[])
    validate_fragment("FactualClaim", value)


def test_absent_operator_or_independent_roles_create_empty_arrays_not_empty_enums():
    conversation, checklist = fixtures()
    operator_only = conversation.model_copy(update={"messages": [conversation.messages[2]]})
    schema = schema_for(operator_only, checklist, grounded=True)
    assert schema["properties"]["request_coverage"]["maxItems"] == 0
    assert not any(n.get("enum") == [] for n in walk(schema))
    value = claim()
    value["dialogue_evidence"] = [{"message_id": "answer", "quote": "Open the Documents control."}]
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment("FactualClaim", value, conversation=operator_only)
    client_only = conversation.model_copy(update={"messages": [conversation.messages[0]]})
    schema = schema_for(client_only, checklist, grounded=True)
    assert schema["properties"]["factual_claims"]["maxItems"] == 0
    assert not any(n.get("enum") == [] for n in walk(schema))
    value = request("unanswered", "none")
    value["support"]["omission"] = {"start_message_id": "question", "end_message_id": "question", "context_evidence": []}
    validate_fragment("RequestCoverage", value, conversation=client_only)


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def test_grounded_schema_keeps_strict_supported_keywords_and_custom_criterion_ids():
    conversation, checklist = fixtures()
    schema = schema_for(conversation, checklist, grounded=True)
    assert schema["properties"]["judgments"]["required"] == ["resolution-new"]
    assert schema["$defs"]["SemanticAudit"]["properties"]["version"]["enum"] == ["coverage-v2"]
    for node in walk(schema):
        assert not {"allOf", "if", "then", "else", "not", "default"} & node.keys()
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])


def wire():
    return {"judgments": {}, "request_coverage": [request()], "scope_notes": [], "factual_claims": [],
            "semantic_audit": {"version": "coverage-v2", "reviewed_message_ids": [], "exclusions": []}}


@pytest.mark.parametrize("fault", ["old_version", "array_judgments", "missing_claim_list", "missing_omission",
                                  "missing_context", "missing_scope", "missing_supported_proposition"])
def test_current_decoder_does_not_fill_new_contract_fields_from_historical_defaults(fault):
    value = wire()
    if fault == "old_version":
        value["semantic_audit"]["version"] = "coverage-v1"
    elif fault == "array_judgments":
        value["judgments"] = []
    elif fault == "missing_claim_list":
        value.pop("factual_claims")
    elif fault == "missing_omission":
        value["request_coverage"][0]["support"].pop("omission")
    else:
        value["factual_claims"] = [claim()]
        value["factual_claims"][0].pop({"missing_context": "context_evidence", "missing_scope": "observation_scope",
                                       "missing_supported_proposition": "supported_proposition"}[fault])
    with pytest.raises(ValueError):
        decode_evaluation(json.dumps(value), require_evidence_contract=True)


def test_decoder_preserves_explicit_omission_and_context_without_inventing_evidence_or_grades():
    value = wire()
    value["request_coverage"] = [request("unanswered", "none")]
    value["factual_claims"] = [claim()]
    original = copy.deepcopy(value)
    result = decode_evaluation(json.dumps(value), require_evidence_contract=True)
    assert result.request_coverage[0].support.omission.model_dump() == original["request_coverage"][0]["support"]["omission"]
    assert result.request_coverage[0].support.evidence == []
    assert result.judgments == []
    assert result.factual_claims[0].context_evidence == []
    assert value == original


def test_legacy_decoder_can_read_historical_v1_without_assigning_new_omission_evidence():
    value = wire()
    value["semantic_audit"]["version"] = "coverage-v1"
    value["request_coverage"][0]["support"].pop("omission")
    result = decode_evaluation(json.dumps(value), require_semantic_coverage=True)
    assert result.request_coverage[0].support.omission is None


@pytest.mark.parametrize("fault", ["request_withdrawal_ids", "claim_rule_evidence", "root_factual_claims"])
def test_current_decoder_recursively_rejects_fields_hidden_by_historical_defaults(fault):
    value = wire()
    if fault == "request_withdrawal_ids":
        value["request_coverage"][0].pop("withdrawal_message_ids")
    elif fault == "claim_rule_evidence":
        value["factual_claims"] = [claim()]
        value["factual_claims"][0].pop("rule_evidence")
    else:
        value.pop("factual_claims")
    with pytest.raises(ValueError, match="explicit"):
        decode_evaluation(json.dumps(value), require_evidence_contract=True)


def test_historical_defaulted_fields_remain_readable_only_under_historical_decoder_mode():
    value = wire()
    value["semantic_audit"]["version"] = "coverage-v1"
    value["request_coverage"][0].pop("withdrawal_message_ids")
    value["request_coverage"][0]["support"].pop("omission")
    value.pop("factual_claims")
    result = decode_evaluation(json.dumps(value), require_semantic_coverage=True)
    assert result.request_coverage[0].withdrawal_message_ids == []
    assert result.request_coverage[0].support.omission is None
    assert result.factual_claims == []

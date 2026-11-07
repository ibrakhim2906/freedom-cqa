"""Source-selection transport tests: no client, inference or score overrides."""

from collections import Counter

import jsonschema
import pytest

from cqa.evaluator import schema_for
from cqa.models import Checklist, Conversation
from cqa.source_spans import build_catalog
from cqa.span_schema import SPAN_CONTRACT, bind_span_contract


def fixture():
    conversation = Conversation.model_validate({"id": "span-transport", "channel": "agent chat", "language": "KZ",
        "messages": [
            {"id": "q", "timestamp": "00:00", "speaker": "client", "text": "PDF файлын қалай ашамын?"},
            {"id": "bot", "timestamp": "00:01", "speaker": "bot", "text": "A human is joining."},
            {"id": "a", "timestamp": "00:02", "speaker": "operator", "text": "Сәлеметсіз бе. Open Documents."},
            {"id": "result", "timestamp": "00:03", "speaker": "client", "text": "The sample PDF opened."},
            {"id": "bye", "timestamp": "00:04", "speaker": "operator", "text": "The sample PDF opened. Goodbye."},
            {"id": "s", "timestamp": "00:05", "speaker": "system", "text": "The sample PDF open event is recorded."}],
        "references": [{"id": "guide", "text": "Documents provides sample PDFs.", "provenance": "Fictional test guide"}]})
    checklist = Checklist.model_validate({"id": "custom", "version": "1", "title": "Resolution", "instructions": [],
        "criteria": [{"id": "resolve", "title": "Resolution", "instruction": "Give a useful next step.", "kind": "binary",
                      "weight": 17, "levels": [{"value": "done", "fraction": 1, "description": "Correct step"},
                                               {"value": "missing", "fraction": 0, "description": "Step missing"}]},
                     {"id": "other", "title": "Other", "instruction": "Apply this separate configured rule.", "kind": "flag",
                      "weight": 0, "levels": [{"value": "yes", "fraction": 1, "description": "Flag present"},
                                               {"value": "no", "fraction": 0, "description": "Flag absent"}]}]})
    catalog = build_catalog(conversation, checklist)
    base = schema_for(conversation, checklist, grounded=True)
    wire = bind_span_contract(base, conversation, checklist, catalog)
    return conversation, checklist, catalog, base, wire


def span(catalog, source_id, *, kind="dialogue"):
    return next(s.span_id for s in catalog.entries.values() if s.kind == kind and s.source_id == source_id and s.is_full)


def evidence(catalog, source_id, *, kind="dialogue"):
    return {"span_id": span(catalog, source_id, kind=kind)}


def premise(catalog):
    return {"premise_id": "p", "proposition": None, "evidence": [],
            "reference_evidence": [evidence(catalog, "guide", kind="reference")], "rule_evidence": [],
            "depends_on_claim_id": None, "required_status": None}


def proof(catalog):
    return {"relation": "direct", "premises": [premise(catalog)], "required_premise_ids": ["p"],
            "explanation": "The selected source supports this one declared proposition."}


def claim(catalog):
    return {"claim": "Documents provides sample PDFs.", "criterion_ids": ["resolve"],
            "operator_evidence": [evidence(catalog, "a")], "status": "supported", "material": True,
            "explanation": "The explicit source supports the policy fact.",
            "assessment": {"lifecycle": "active", "correction": None, "impacts": []},
            "evidence_kind": "product_fact", "verification_scope": "policy",
            "context_evidence": [], "claim_id": "c", "assertion_group_id": "g", "proof": proof(catalog),
            "observation": None}


def request(catalog, status="answered", basis="explicit"):
    return {"request": "Locate the PDF", "request_message_ids": ["q"], "status": status,
            "answer_message_ids": ["a"], "explanation": "The operator supplied the step.",
            "withdrawal_message_ids": None, "support": {"basis": basis, "evidence": [evidence(catalog, "a")],
            "inference": None, "unresolved_aspects": None, "omission": None}}


def validate_fragment(wire, name, value):
    jsonschema.Draft202012Validator({"$defs": wire["$defs"], "$ref": f"#/$defs/{name}"}).validate(value)


def test_binding_is_pure_and_requires_explicit_v3_root_identity():
    _, _, catalog, base, wire = fixture()
    assert "contract_version" not in base["properties"]
    assert wire["properties"]["contract_version"]["enum"] == [SPAN_CONTRACT]
    assert wire["properties"]["catalog_fingerprint"]["enum"] == [catalog.fingerprint]
    assert "source_citations" not in wire["properties"]
    assert "assertion_groups" in wire["required"]
    assert wire["$defs"]["SemanticAudit"]["properties"]["version"]["enum"] == ["coverage-v3"]
    jsonschema.Draft202012Validator.check_schema(wire)


@pytest.mark.parametrize("criterion_id", ["title", "required", "type"])
def test_schema_metadata_cleanup_preserves_configured_property_names(criterion_id):
    conversation, checklist, _, _, _ = fixture()
    checklist = checklist.model_copy(update={"criteria": [
        checklist.criteria[0].model_copy(update={"id": criterion_id}), checklist.criteria[1]]})
    catalog = build_catalog(conversation, checklist)
    wire = bind_span_contract(schema_for(conversation, checklist, grounded=True), conversation, checklist, catalog)
    judgments = wire["properties"]["judgments"]
    assert criterion_id in judgments["properties"] and criterion_id in judgments["required"]
    jsonschema.Draft202012Validator.check_schema(wire)


@pytest.mark.parametrize("criterion_id", ["$defs", "$ref", "properties", "anyOf", "a/b~c", "rule_quote"])
@pytest.mark.parametrize("deduct", [False, True])
def test_single_keyword_named_criterion_keeps_referenced_schemas_and_rule_ownership(criterion_id, deduct):
    conversation, checklist, _, _, _ = fixture()
    checklist = checklist.model_copy(update={"criteria": [checklist.criteria[0].model_copy(update={"id": criterion_id})]})
    catalog = build_catalog(conversation, checklist)
    wire = bind_span_contract(schema_for(conversation, checklist, grounded=True), conversation, checklist, catalog)
    assert list(wire["properties"]["judgments"]["properties"]) == [criterion_id]
    judgment = {"criterion_id": criterion_id, "status": "scored", "answer": "missing" if deduct else "done",
        "explanation": "Structural fixture for citation and rule binding.", "evidence": [evidence(catalog, "a")],
        "counterevidence": [], "checked_message_ids": ["a"], "uncertainty": None,
        "deduction": {"criterion_id": criterion_id, "rule_span_id": span(catalog, criterion_id, kind="rule"),
            "defect": "Structural fixture", "evidence": [evidence(catalog, "a")], "checked_message_ids": ["a"],
            "overlap_note": "Independent fixture"} if deduct else None}
    value = {"judgments": {criterion_id: judgment}, "request_coverage": [], "scope_notes": [], "factual_claims": [],
        "semantic_audit": {"version": "coverage-v3", "reviewed_message_ids": ["q", "a", "result", "bye"],
                           "exclusions": []}, "assertion_groups": [], "contract_version": SPAN_CONTRACT,
        "catalog_fingerprint": catalog.fingerprint}
    jsonschema.Draft202012Validator.check_schema(wire)
    jsonschema.Draft202012Validator(wire).validate(value)


@pytest.mark.parametrize("criterion_ids", [["message_id", "quote"], ["reference_id", "quote"],
                                         ["criterion_id", "quote"], ["criterion_id", "rule_quote"]])
def test_criterion_names_matching_citation_fields_do_not_retype_the_judgment_object(criterion_ids):
    conversation, checklist, _, _, _ = fixture()
    checklist = checklist.model_copy(update={"criteria": [
        criterion.model_copy(update={"id": name})
        for criterion, name in zip(checklist.criteria, criterion_ids, strict=True)]})
    catalog = build_catalog(conversation, checklist)
    wire = bind_span_contract(schema_for(conversation, checklist, grounded=True), conversation, checklist, catalog)
    judgments = wire["properties"]["judgments"]
    assert set(judgments["properties"]) == set(criterion_ids)
    assert set(judgments["required"]) == set(criterion_ids)
    jsonschema.Draft202012Validator.check_schema(wire)


@pytest.mark.parametrize("slot,owner,bad_kind,bad_owner", [
    ("operator_evidence", "a", "dialogue", "result"),
    ("context_evidence", "result", "dialogue", "a"),
    ("reference_evidence", "guide", "dialogue", "a"),
    ("rule_evidence", "resolve", "reference", "guide"),
])
def test_all_citation_classes_reject_wrong_kind_or_role(slot, owner, bad_kind, bad_owner):
    _, _, catalog, _, wire = fixture()
    value = claim(catalog)
    good_kind = "reference" if slot == "reference_evidence" else "rule" if slot == "rule_evidence" else "dialogue"
    location = value["proof"]["premises"][0] if slot in {"reference_evidence", "rule_evidence"} else value
    location[slot] = [evidence(catalog, owner, kind=good_kind)]
    validate_fragment(wire, "FactualClaim", value)
    location[slot] = [evidence(catalog, bad_owner, kind=bad_kind)]
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "FactualClaim", value)


@pytest.mark.parametrize("fault", ["typed_quote", "foreign_id", "missing_proof", "bad_kind_scope", "duplicated_proposition",
                                  "flat_reference_evidence", "flat_rule_evidence", "flat_dialogue_evidence"])
def test_current_claim_transport_rejects_free_text_defaults_and_wrong_topology(fault):
    _, _, catalog, _, wire = fixture()
    value = claim(catalog)
    validate_fragment(wire, "FactualClaim", value)
    if fault == "typed_quote":
        value["operator_evidence"][0]["quote"] = "Сәлемсіз бе"
    elif fault == "foreign_id":
        value["operator_evidence"][0]["span_id"] = "d_o_invented"
    elif fault == "missing_proof":
        value["proof"] = None
    elif fault == "bad_kind_scope":
        value.update(evidence_kind="account_state", verification_scope="interaction")
    elif fault == "duplicated_proposition":
        value["supported_proposition"] = value["claim"]
    else:
        value[fault.removeprefix("flat_")] = []
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "FactualClaim", value)


def test_canonical_observation_uses_claim_once_and_rejects_duplicated_evidence():
    _, _, catalog, _, wire = fixture()
    value = claim(catalog)
    value.update(claim="The sample PDF opened.", verification_scope="interaction",
                 evidence_kind="general_fact", observation={"target": "claim", "scope": "task_completed"})
    value["proof"]["premises"][0].update(evidence=[evidence(catalog, "result")], reference_evidence=[])
    validate_fragment(wire, "FactualClaim", value)
    assert "supported_proposition" not in str(wire)
    value["observation"]["evidence"] = [evidence(catalog, "result")]
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "FactualClaim", value)


def test_counterfactual_fixed_claim_ids_are_explicit_and_not_historical_defaults():
    _, _, catalog, _, wire = fixture()
    value = {"criterion_id": "resolve", "when_true": {"status": "scored", "answer": "done"},
             "when_false": {"status": "scored", "answer": "missing"},
             "rule_span_id": span(catalog, "resolve", kind="rule"), "evidence": [],
             "checked_message_ids": ["q", "a"], "explanation": "Hold other known facts fixed.", "fixed_claim_ids": []}
    validate_fragment(wire, "ClaimImpact", value)
    value.pop("fixed_claim_ids")
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "ClaimImpact", value)
    value["fixed_claim_ids"] = None
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "ClaimImpact", value)


def test_commitment_proof_operator_source_is_not_available_to_product_fact_proof():
    _, _, catalog, _, wire = fixture()
    value = claim(catalog)
    value["proof"]["premises"][0].update(evidence=[evidence(catalog, "a")], reference_evidence=[])
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "FactualClaim", value)
    value.update(evidence_kind="workflow_commitment", verification_scope="commitment")
    validate_fragment(wire, "FactualClaim", value)


@pytest.mark.parametrize("kind,scope", [("product_fact", "policy"), ("general_fact", "policy"),
    ("grading_rule", "grading_rule"), ("workflow_commitment", "commitment")])
def test_canonical_observation_does_not_launder_ui_context_into_policy_or_normative_truth(kind, scope):
    _, _, catalog, _, wire = fixture()
    value = claim(catalog)
    value.update(evidence_kind=kind, verification_scope=scope)
    validate_fragment(wire, "FactualClaim", value)
    value["observation"] = {"target": "claim", "scope": "control_visible"}
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "FactualClaim", value)


def test_private_record_observation_is_null_or_system_record_only():
    _, _, catalog, _, wire = fixture()
    value = claim(catalog)
    value.update(evidence_kind="account_state", verification_scope="private_record")
    validate_fragment(wire, "FactualClaim", value)
    value["observation"] = {"target": "claim", "scope": "task_completed"}
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "FactualClaim", value)
    value["observation"] = {"target": "claim", "scope": "system_record"}
    validate_fragment(wire, "FactualClaim", value)
    value["proof"]["premises"][0].update(evidence=[evidence(catalog, "result")], reference_evidence=[])
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "FactualClaim", value)


def test_dependency_and_source_premises_are_distinct_and_conjunctions_have_own_propositions():
    _, _, catalog, _, wire = fixture()
    value = proof(catalog)
    value["premises"] = [{"premise_id": "p", "proposition": None, "evidence": None,
        "reference_evidence": None, "rule_evidence": None, "depends_on_claim_id": "other-claim", "required_status": "supported"}]
    validate_fragment(wire, "SpanClaimProof", value)
    value["premises"][0]["evidence"] = [evidence(catalog, "result")]
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "SpanClaimProof", value)
    value = proof(catalog)
    value["relation"] = "all_of"
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "SpanClaimProof", value)
    value["premises"] = [premise(catalog), {**premise(catalog), "premise_id": "p2"}]
    value["required_premise_ids"] = ["p", "p2"]
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "SpanClaimProof", value)
    for index, item in enumerate(value["premises"]):
        item["proposition"] = f"Independent required proposition {index}"
    validate_fragment(wire, "SpanClaimProof", value)


def test_request_non_applicable_lists_are_literal_null_not_empty_array_branches():
    _, _, catalog, _, wire = fixture()
    value = request(catalog, "next_step", "next_step")
    validate_fragment(wire, "RequestCoverage", value)
    value["support"]["unresolved_aspects"] = []
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "RequestCoverage", value)
    value["support"]["unresolved_aspects"] = ["Factual uncertainty belongs to the claim audit."]
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "RequestCoverage", value)


def test_rule_span_binding_preserves_owning_criterion_for_inline_deduction():
    _, _, catalog, _, wire = fixture()
    branch = wire["properties"]["judgments"]["properties"]["resolve"]
    fragment = {"$defs": wire["$defs"], **branch}
    value = {"criterion_id": "resolve", "status": "scored", "answer": "missing", "explanation": "Step missing.",
             "evidence": [], "counterevidence": [], "checked_message_ids": ["q", "a"], "uncertainty": None,
             "deduction": {"criterion_id": "resolve", "rule_span_id": span(catalog, "resolve", kind="rule"),
                           "defect": "Missing step", "evidence": [], "checked_message_ids": ["q", "a"],
                           "overlap_note": "Independent defect"}}
    jsonschema.validate(value, fragment)
    value["deduction"]["rule_span_id"] = span(catalog, "other", kind="rule")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, fragment)


def test_exclusions_do_not_accept_system_or_bot_spans():
    _, _, catalog, _, wire = fixture()
    value = {"evidence": evidence(catalog, "a"), "reason": "social", "criterion_ids": [], "explanation": "Greeting."}
    validate_fragment(wire, "SemanticExclusion", value)
    for mid in ["s", "bot"]:
        value["evidence"] = evidence(catalog, mid)
        with pytest.raises(jsonschema.ValidationError):
            validate_fragment(wire, "SemanticExclusion", value)


def test_exact_old_message_subset_is_not_broadened_to_all_operator_spans():
    conversation, checklist, catalog, base, _ = fixture()
    for branch in base["$defs"]["FactualClaim"]["anyOf"]:
        branch["properties"]["operator_evidence"]["items"]["properties"]["message_id"] = {"type": "string", "enum": ["a"]}
    wire = bind_span_contract(base, conversation, checklist, catalog)
    value = claim(catalog)
    validate_fragment(wire, "FactualClaim", value)
    value["operator_evidence"] = [evidence(catalog, "bye")]
    with pytest.raises(jsonschema.ValidationError):
        validate_fragment(wire, "FactualClaim", value)


def test_catalog_ids_are_enumerated_once_and_empty_arrays_are_never_max_zero():
    _, _, catalog, _, wire = fixture()
    counts = Counter()

    def visit(node):
        if isinstance(node, dict):
            assert not (node.get("type") == "array" and node.get("maxItems") == 0)
            assert "default" not in node
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node["required"]) == set(node["properties"])
            counts.update(x for x in node.get("enum", []) if x in catalog.entries)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(wire)
    assert set(counts) == set(catalog.ids())
    assert set(counts.values()) == {1}


@pytest.mark.parametrize("role", ["operator", "client", "system", "bot"])
def test_absent_source_roles_have_null_collections_and_no_empty_enum(role):
    conversation, checklist, _, _, _ = fixture()
    conversation = conversation.model_copy(update={"messages": [m for m in conversation.messages if m.speaker == role],
                                                    "references": []})
    catalog = build_catalog(conversation, checklist)
    wire = bind_span_contract(schema_for(conversation, checklist, grounded=True), conversation, checklist, catalog)
    jsonschema.Draft202012Validator.check_schema(wire)
    if role != "operator":
        assert wire["properties"]["factual_claims"] == {"type": "null"}
        assert wire["properties"]["assertion_groups"] == {"type": "null"}
    if role != "client":
        assert wire["properties"]["request_coverage"] == {"type": "null"}

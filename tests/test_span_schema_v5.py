"""Offline review-link schema checks and exact historical wire regressions."""

import hashlib
import json
from copy import deepcopy

import jsonschema
import pytest
from test_span_schema import evidence, span
from test_span_schema import fixture as historical_fixture
from test_span_schema_v4 import claim, observed_claim, proof, source_premise

from cqa.evaluator import schema_for
from cqa.source_spans import build_catalog
from cqa.span_schema import SPAN_CONTRACT, bind_span_contract


@pytest.fixture
def source():
    conversation, checklist, catalog, base, _ = historical_fixture()
    wire = bind_span_contract(base, conversation, checklist, catalog)
    return conversation, checklist, catalog, base, wire


def expand(wire, node):
    if isinstance(node, list):
        return [expand(wire, item) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return expand(wire, wire["$defs"][node["$ref"].split("/")[-1]])
    return {key: expand(wire, value) for key, value in node.items()}


def judgment_schema(wire, criterion_id="resolve"):
    return {"$defs": wire["$defs"], **wire["properties"]["judgments"]["properties"][criterion_id]}


def judgment(catalog, criterion_id="resolve"):
    return {"criterion_id": criterion_id, "status": "scored", "answer": "done",
            "explanation": "The selected canonical sources establish the configured result.",
            "evidence": [evidence(catalog, "a")], "counterevidence": [],
            "additional_checked_message_ids": [], "uncertainty": None, "deduction": None}


def test_default_is_explicit_v5_and_does_not_mutate_base(source):
    conversation, checklist, catalog, base, wire = source
    assert SPAN_CONTRACT == "span-v5"
    assert wire == bind_span_contract(base, conversation, checklist, catalog, contract="span-v5")
    assert wire["properties"]["contract_version"]["enum"] == ["span-v5"]
    assert wire["$defs"]["SemanticAudit"]["properties"]["version"]["enum"] == ["coverage-v5"]
    assert wire["properties"]["catalog_fingerprint"]["enum"] == [catalog.fingerprint]
    assert "contract_version" not in base["properties"]
    assert "additional_checked_message_ids" not in base["$defs"]["Judgment"]["properties"]
    assert schema_for(conversation, checklist, grounded=True, source_contract=True) == wire
    assert schema_for(conversation, checklist, grounded=True, source_contract=True,
                      source_contract_version="span-v5") == wire
    with pytest.raises(ValueError, match="Unsupported source-span contract"):
        bind_span_contract(base, conversation, checklist, catalog, contract="span-v6")


def test_every_judgment_branch_keeps_exact_review_constraints_and_field_position(source):
    conversation, checklist, catalog, base, wire = source
    previous = bind_span_contract(base, conversation, checklist, catalog, contract="span-v4")
    for criterion in checklist.criteria:
        before = expand(previous, previous["properties"]["judgments"]["properties"][criterion.id])["anyOf"]
        after = expand(wire, wire["properties"]["judgments"]["properties"][criterion.id])["anyOf"]
        assert len(after) == len(before)
        for old_branch, new_branch in zip(before, after, strict=True):
            fields = new_branch["properties"]
            assert "checked_message_ids" not in fields
            assert list(fields) == ["additional_checked_message_ids" if key == "checked_message_ids" else key
                                    for key in old_branch["properties"]]
            assert new_branch["required"] == list(fields)
            assert new_branch["additionalProperties"] is False
            assert fields["additional_checked_message_ids"] == old_branch["properties"]["checked_message_ids"]
            assert fields["additional_checked_message_ids"]["type"] == "array"
            assert "minItems" not in fields["additional_checked_message_ids"]


@pytest.mark.parametrize("extra", [[], ["q"], ["q", "a", "bot", "result", "bye", "s"]])
def test_judgment_extra_checks_accept_only_the_existing_message_domain(source, extra):
    _, _, catalog, _, wire = source
    value = judgment(catalog)
    value["additional_checked_message_ids"] = extra
    jsonschema.validate(value, judgment_schema(wire))


@pytest.mark.parametrize("extra", [None, "a", ["invented"], [1], {}])
def test_judgment_extra_checks_reject_invalid_types_and_invented_ids(source, extra):
    _, _, catalog, _, wire = source
    value = judgment(catalog)
    value["additional_checked_message_ids"] = extra
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, judgment_schema(wire))


@pytest.mark.parametrize("form", ["missing", "old_only", "both"])
def test_provider_cannot_submit_a_complete_judgment_review_list(source, form):
    _, _, catalog, _, wire = source
    value = judgment(catalog)
    if form != "both":
        value.pop("additional_checked_message_ids")
    if form != "missing":
        value["checked_message_ids"] = ["q", "a"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, judgment_schema(wire))


def test_deduction_and_impact_checked_lists_keep_their_existing_meaning(source):
    conversation, checklist, catalog, base, wire = source
    previous = bind_span_contract(base, conversation, checklist, catalog, contract="span-v4")
    value = judgment(catalog)
    value.update(answer="missing", deduction={"criterion_id": "resolve",
        "rule_span_id": span(catalog, "resolve", kind="rule"), "defect": "Missing the configured step.",
        "evidence": [], "checked_message_ids": ["q", "a"], "overlap_note": "An independent configured defect."})
    jsonschema.validate(value, judgment_schema(wire))
    value["deduction"]["additional_checked_message_ids"] = value["deduction"].pop("checked_message_ids")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, judgment_schema(wire))
    impact = expand(wire, wire["$defs"]["ClaimImpact"])
    assert impact == expand(previous, previous["$defs"]["ClaimImpact"])
    assert "checked_message_ids" in impact["required"]
    assert "additional_checked_message_ids" not in impact["properties"]


@pytest.mark.parametrize("criterion_id", ["checked_message_ids", "additional_checked_message_ids", "$defs", "$ref",
                                         "properties", "anyOf", "required", "items", "additionalProperties", "S1"])
def test_review_and_metadata_named_criteria_remain_required_configured_keys(source, criterion_id):
    conversation, checklist, _, _, _ = source
    checklist = checklist.model_copy(update={
        "criteria": [checklist.criteria[0].model_copy(update={"id": criterion_id})]})
    catalog = build_catalog(conversation, checklist)
    wire = schema_for(conversation, checklist, grounded=True, source_contract=True,
                      source_contract_version="span-v5")
    configured = wire["properties"]["judgments"]
    assert list(configured["properties"]) == configured["required"] == [criterion_id]
    jsonschema.Draft202012Validator.check_schema(wire)
    value = judgment(catalog, criterion_id)
    jsonschema.validate(value, judgment_schema(wire, criterion_id))
    value["checked_message_ids"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, judgment_schema(wire, criterion_id))


def test_many_judgment_field_named_criteria_do_not_turn_the_key_map_into_a_judgment(source):
    conversation, checklist, _, _, _ = source
    ids = ["criterion_id", "status", "answer", "counterevidence", "checked_message_ids",
           "additional_checked_message_ids", "$defs", "properties", "required"]
    checklist = checklist.model_copy(update={"criteria": [
        checklist.criteria[0].model_copy(update={"id": criterion_id}) for criterion_id in ids]})
    wire = schema_for(conversation, checklist, grounded=True, source_contract=True,
                      source_contract_version="span-v5")
    configured = wire["properties"]["judgments"]
    assert list(configured["properties"]) == configured["required"] == ids
    jsonschema.Draft202012Validator.check_schema(wire)


@pytest.mark.parametrize("only_role", [None, "operator", "client", "system", "bot"])
def test_v5_retains_every_other_v4_wire_guard_and_compaction(source, only_role):
    conversation, checklist, _, _, _ = source
    if only_role:
        conversation = conversation.model_copy(update={
            "messages": [m for m in conversation.messages if m.speaker == only_role], "references": []})
    catalog = build_catalog(conversation, checklist)
    base = schema_for(conversation, checklist, grounded=True)
    previous = bind_span_contract(base, conversation, checklist, catalog, contract="span-v4")
    wire = bind_span_contract(base, conversation, checklist, catalog)
    normalized = deepcopy(wire)
    normalized["properties"]["contract_version"]["enum"] = ["span-v4"]
    normalized["$defs"]["SemanticAudit"]["properties"]["version"]["enum"] = ["coverage-v4"]
    for criterion in normalized["properties"]["judgments"]["properties"].values():
        for branch in criterion["anyOf"]:
            branch["properties"] = {"checked_message_ids" if key == "additional_checked_message_ids" else key: field
                                    for key, field in branch["properties"].items()}
            branch["required"] = list(branch["properties"])
    assert normalized == previous
    jsonschema.Draft202012Validator.check_schema(wire)


def test_v5_keeps_group_sources_absent_and_observation_proof_coupled(source):
    _, _, catalog, _, wire = source
    group_schema = {"$defs": wire["$defs"], "$ref": "#/$defs/AssertionGroup"}
    group = {"group_id": "g", "composition": "atomic", "claim_ids": ["c"]}
    jsonschema.validate(group, group_schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**group, "operator_evidence": [evidence(catalog, "a")]}, group_schema)
    claim_schema = {"$defs": wire["$defs"], "$ref": "#/$defs/FactualClaim"}
    value = claim(catalog)
    value.update(status="unverified", proof=None)
    jsonschema.validate(value, claim_schema)
    value["observation"] = {"target": "claim", "scope": "task_completed"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, claim_schema)
    value = observed_claim(catalog)
    jsonschema.validate(value, claim_schema)
    value["proof"] = proof(source_premise(catalog, message="a"))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, claim_schema)


@pytest.mark.parametrize("contract,role,expected", [
    ("span-v3", None, "2d53ed7902a557e20b1a2026c148039de46cd5bdac8ad9e396a0575c4d3f5dd6"),
    ("span-v4", None, "cceb5407edd71343e3720f2d7ab10a215453015082863bffd0dfb81d66e84a52"),
    ("span-v3", "operator", "5a1af86f8fc5b2136bec9e2dd95320f9027109fd712129af665c1888824b38f5"),
    ("span-v4", "operator", "1941b8c2baa922ed2a20a9cc7833f848967284811c8b249c8ec58e9773d0015b"),
    ("span-v3", "client", "f1f4662fb4aaefe6170073005e3548819f2d92a775a8154d13afa8f59e7059ea"),
    ("span-v4", "client", "fe38cb7cb0f488900d3cab27d3752bdddca31cf081dff29c0cf90b2d71a75aef"),
    ("span-v3", "system", "4ad482d1bed22ce53091e0f65cfca2a929f75ceb1391ebe5cb066d1718ee5898"),
    ("span-v4", "system", "12561f0e7c0faad3d24b2095118c27c307fb3ab019d79eadccb28780060f1873"),
    ("span-v3", "bot", "3fed9b9ead204cedb8baa4a492c39a6abde251ffec61d4c3f4416d02cccb9aef"),
    ("span-v4", "bot", "caf15551a96a274b9608fed6da55907ee4ce97fe7cda70e29417ebb1142bdfff"),
])
def test_explicit_historical_contracts_keep_exact_pre_v5_bytes(source, contract, role, expected):
    conversation, checklist, _, _, _ = source
    if role:
        conversation = conversation.model_copy(update={
            "messages": [m for m in conversation.messages if m.speaker == role], "references": []})
    catalog = build_catalog(conversation, checklist)
    wire = bind_span_contract(schema_for(conversation, checklist, grounded=True), conversation, checklist,
                              catalog, contract=contract)
    serialized = json.dumps(wire, ensure_ascii=False, separators=(",", ":")).encode()
    assert hashlib.sha256(serialized).hexdigest() == expected

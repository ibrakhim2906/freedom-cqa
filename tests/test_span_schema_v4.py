"""Offline v4 schema regressions; no provider calls or rewritten historical data."""

import hashlib
import json
from collections import Counter

import jsonschema
import pytest
from test_span_schema import evidence
from test_span_schema import fixture as historical_fixture

from cqa.evaluator import schema_for
from cqa.source_spans import build_catalog
from cqa.span_schema import SPAN_CONTRACT, bind_span_contract


@pytest.fixture
def source():
    conversation, checklist, catalog, base, _ = historical_fixture()
    wire = bind_span_contract(base, conversation, checklist, catalog)
    return conversation, checklist, catalog, base, wire


def validate(wire, name, value):
    jsonschema.Draft202012Validator({"$defs": wire["$defs"], "$ref": f"#/$defs/{name}"}).validate(value)


def source_premise(catalog, *, message=None, pid="p", proposition=None):
    return {"premise_id": pid, "proposition": proposition,
            "evidence": [evidence(catalog, message)] if message else None,
            "reference_evidence": [] if message else [evidence(catalog, "guide", kind="reference")],
            "rule_evidence": [], "depends_on_claim_id": None, "required_status": None}


def dependency(pid="p", claim_id="other"):
    return {"premise_id": pid, "proposition": None, "evidence": None, "reference_evidence": None,
            "rule_evidence": None, "depends_on_claim_id": claim_id, "required_status": "supported"}


def proof(*premises):
    return {"relation": "direct" if len(premises) == 1 else "all_of", "premises": list(premises),
            "required_premise_ids": [item["premise_id"] for item in premises],
            "explanation": "The explicit essential premises establish this canonical proposition."}


def claim(catalog):
    return {"claim": "Documents provides sample PDFs.", "criterion_ids": ["resolve"],
            "operator_evidence": [evidence(catalog, "a")], "status": "supported", "material": True,
            "explanation": "The selected source establishes the proposition.",
            "assessment": {"lifecycle": "active", "correction": None, "impacts": []},
            "evidence_kind": "product_fact", "verification_scope": "policy", "context_evidence": [],
            "claim_id": "c", "assertion_group_id": "g", "proof": proof(source_premise(catalog)),
            "observation": None}


def observed_claim(catalog, *, scope="task_completed", message="result"):
    value = claim(catalog)
    value.update(evidence_kind="general_fact", verification_scope="interaction",
                 observation={"target": "claim", "scope": scope}, proof=proof(source_premise(catalog, message=message)))
    return value


def test_default_is_explicit_v4_and_does_not_mutate_base(source):
    conversation, checklist, catalog, base, wire = source
    assert SPAN_CONTRACT == "span-v4"
    assert wire == bind_span_contract(base, conversation, checklist, catalog, contract="span-v4")
    assert wire["properties"]["contract_version"]["enum"] == ["span-v4"]
    assert wire["$defs"]["SemanticAudit"]["properties"]["version"]["enum"] == ["coverage-v4"]
    assert wire["properties"]["catalog_fingerprint"]["enum"] == [catalog.fingerprint]
    assert "contract_version" not in base["properties"]
    with pytest.raises(ValueError, match="Unsupported source-span contract"):
        bind_span_contract(base, conversation, checklist, catalog, contract="span-v5")


@pytest.mark.parametrize("role,expected", [
    (None, "e666781c47bacb06e977bcefafdfe50a775f8cc54a72e86f98f67b3dd8a29f08"),
    ("operator", "a6dad8b49a3a4fd1aaec8c6cc4fc6edb4f83a7800bde8be155c0cea9c43e5f53"),
    ("client", "a642d2598ad7026e2e82ca806d196913a70edc39fa5028f42c2e06e246edf4e1"),
    ("system", "58b71e17c169e34652bdaa249777d234c5ce4c8a1f97a6ed7cb6ee8457922bd6"),
    ("bot", "0ce497319d6b6490c43aab6296cc2004698b6ee1bfa4369f3439ab198697435f"),
])
def test_explicit_v3_schema_matches_pre_v4_canonical_hash(source, role, expected):
    conversation, checklist, _, _, _ = source
    if role is not None:
        conversation = conversation.model_copy(update={
            "messages": [m for m in conversation.messages if m.speaker == role], "references": []})
    catalog = build_catalog(conversation, checklist)
    wire = bind_span_contract(schema_for(conversation, checklist, grounded=True), conversation, checklist,
                              catalog, contract="span-v3")
    serialized = json.dumps(wire, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(serialized).hexdigest() == expected


def test_group_has_only_required_canonical_membership_fields(source):
    _, _, catalog, _, wire = source
    group = {"group_id": "g", "composition": "atomic", "claim_ids": ["c"]}
    validate(wire, "AssertionGroup", group)
    for field in group:
        invalid = {key: value for key, value in group.items() if key != field}
        with pytest.raises(jsonschema.ValidationError):
            validate(wire, "AssertionGroup", invalid)
    for citation in [None, [], [evidence(catalog, "a")]]:
        with pytest.raises(jsonschema.ValidationError):
            validate(wire, "AssertionGroup", {**group, "operator_evidence": citation})


@pytest.mark.parametrize("composition,claim_ids,valid", [
    ("atomic", [], False), ("atomic", ["c"], True), ("atomic", ["c", "d"], False),
    ("all_of", [], False), ("all_of", ["c"], False), ("all_of", ["c", "d"], True),
    ("all_of", ["c", ""], False),
])
def test_group_cardinalities_remain_explicit(source, composition, claim_ids, valid):
    wire = source[-1]
    group = {"group_id": "g", "composition": composition, "claim_ids": claim_ids}
    if valid:
        validate(wire, "AssertionGroup", group)
    else:
        with pytest.raises(jsonschema.ValidationError):
            validate(wire, "AssertionGroup", group)


@pytest.mark.parametrize("kind,scope,observation", [
    ("general_fact", "interaction", "reported_state"),
    ("general_fact", "interaction", "system_record"),
    ("account_state", "private_record", "system_record"),
])
def test_nonnull_observation_always_requires_nonnull_proof(source, kind, scope, observation):
    _, _, catalog, _, wire = source
    value = claim(catalog)
    value.update(evidence_kind=kind, verification_scope=scope, status="unverified", proof=None)
    validate(wire, "FactualClaim", value)
    value["observation"] = {"target": "claim", "scope": observation}
    with pytest.raises(jsonschema.ValidationError):
        validate(wire, "FactualClaim", value)


@pytest.mark.parametrize("status", ["supported", "contradicted", "unverified"])
def test_proofless_status_is_only_unverified(source, status):
    _, _, catalog, _, wire = source
    value = claim(catalog)
    value.update(status=status, proof=None)
    if status == "unverified":
        validate(wire, "FactualClaim", value)
    else:
        with pytest.raises(jsonschema.ValidationError):
            validate(wire, "FactualClaim", value)


@pytest.mark.parametrize("kind,scope", [
    ("product_fact", "policy"), ("general_fact", "interaction"),
    ("grading_rule", "grading_rule"), ("account_state", "private_record"),
])
def test_absent_observation_forbids_local_independent_dialogue_sources(source, kind, scope):
    _, _, catalog, _, wire = source
    value = claim(catalog)
    value.update(evidence_kind=kind, verification_scope=scope)
    validate(wire, "FactualClaim", value)
    for message in ["result", "s"]:
        value["proof"] = proof(source_premise(catalog, message=message))
        with pytest.raises(jsonschema.ValidationError):
            validate(wire, "FactualClaim", value)


def test_commitment_source_role_is_operator_and_observation_stays_null(source):
    _, _, catalog, _, wire = source
    value = claim(catalog)
    value.update(evidence_kind="workflow_commitment", verification_scope="commitment",
                 proof=proof(source_premise(catalog, message="a")))
    validate(wire, "FactualClaim", value)
    for message in ["result", "s", "bot"]:
        value["proof"] = proof(source_premise(catalog, message=message))
        with pytest.raises(jsonschema.ValidationError):
            validate(wire, "FactualClaim", value)
    value["proof"] = proof(source_premise(catalog, message="a"))
    value["observation"] = {"target": "claim", "scope": "action_completed"}
    with pytest.raises(jsonschema.ValidationError):
        validate(wire, "FactualClaim", value)


@pytest.mark.parametrize("scope", ["reported_state", "control_visible", "action_completed", "task_completed"])
def test_observed_direct_source_accepts_independent_roles_only(source, scope):
    _, _, catalog, _, wire = source
    for message in ["result", "s"]:
        validate(wire, "FactualClaim", observed_claim(catalog, scope=scope, message=message))
    for message in ["a", "bot"]:
        with pytest.raises(jsonschema.ValidationError):
            validate(wire, "FactualClaim", observed_claim(catalog, scope=scope, message=message))


@pytest.mark.parametrize("kind,scope", [("general_fact", "interaction"), ("account_state", "private_record")])
def test_system_observation_source_must_be_system(source, kind, scope):
    _, _, catalog, _, wire = source
    value = observed_claim(catalog, scope="system_record", message="s")
    value.update(evidence_kind=kind, verification_scope=scope)
    validate(wire, "FactualClaim", value)
    value["proof"] = proof(source_premise(catalog, message="result"))
    with pytest.raises(jsonschema.ValidationError):
        validate(wire, "FactualClaim", value)


def test_observed_direct_source_cannot_be_reference_only_or_empty(source):
    _, _, catalog, _, wire = source
    value = observed_claim(catalog)
    value["proof"] = proof(source_premise(catalog))
    for absent in [None, []]:
        value["proof"]["premises"][0]["evidence"] = absent
        with pytest.raises(jsonschema.ValidationError):
            validate(wire, "FactualClaim", value)


@pytest.mark.parametrize("observation", [None, "task_completed", "system_record"])
def test_dependency_only_proofs_remain_available_for_runtime_leaf_validation(source, observation):
    _, _, catalog, _, wire = source
    value = observed_claim(catalog)
    value["observation"] = {"target": "claim", "scope": observation} if observation else None
    value["proof"] = proof(dependency())
    validate(wire, "FactualClaim", value)
    value["proof"] = proof(dependency("p"), dependency("q", "another"))
    validate(wire, "FactualClaim", value)
    value["proof"]["premises"][0]["evidence"] = [evidence(catalog, "result")]
    with pytest.raises(jsonschema.ValidationError):
        validate(wire, "FactualClaim", value)


def test_observed_conjunction_can_mix_dialogue_reference_and_dependency_premises(source):
    _, _, catalog, _, wire = source
    value = observed_claim(catalog)
    reference = source_premise(catalog, pid="r", proposition="The guide establishes the first prerequisite.")
    reference["evidence"] = []
    value["proof"] = proof(source_premise(catalog, message="result", proposition="The action was observed."),
                           reference, dependency("d"))
    validate(wire, "FactualClaim", value)
    value["proof"]["premises"][0]["proposition"] = None
    with pytest.raises(jsonschema.ValidationError):
        validate(wire, "FactualClaim", value)


def test_v3_and_v4_groups_are_distinct_provider_shapes(source):
    conversation, checklist, catalog, base, wire = source
    old = bind_span_contract(base, conversation, checklist, catalog, contract="span-v3")
    group = {"group_id": "g", "composition": "atomic", "claim_ids": ["c"]}
    validate(wire, "AssertionGroup", group)
    with pytest.raises(jsonschema.ValidationError):
        validate(old, "AssertionGroup", group)
    group["operator_evidence"] = [evidence(catalog, "a")]
    validate(old, "AssertionGroup", group)
    with pytest.raises(jsonschema.ValidationError):
        validate(wire, "AssertionGroup", group)


@pytest.mark.parametrize("criterion_id", ["$defs", "$ref", "properties", "anyOf", "required", "S1"])
def test_compact_definition_references_preserve_configured_judgment_keys(source, criterion_id):
    conversation, checklist, _, _, _ = source
    checklist = checklist.model_copy(update={"criteria": [checklist.criteria[0].model_copy(update={"id": criterion_id})]})
    catalog = build_catalog(conversation, checklist)
    wire = bind_span_contract(schema_for(conversation, checklist, grounded=True), conversation, checklist, catalog)
    assert list(wire["properties"]["judgments"]["properties"]) == [criterion_id]
    jsonschema.Draft202012Validator.check_schema(wire)


@pytest.mark.parametrize("only_role", [None, "operator", "client", "system", "bot"])
def test_v4_schema_keeps_strict_objects_and_one_copy_of_each_reachable_source_enum(source, only_role):
    conversation, checklist, _, _, _ = source
    if only_role:
        conversation = conversation.model_copy(update={
            "messages": [m for m in conversation.messages if m.speaker == only_role], "references": []})
    catalog = build_catalog(conversation, checklist)
    wire = bind_span_contract(schema_for(conversation, checklist, grounded=True), conversation, checklist, catalog)
    counts = Counter()

    def visit(node):
        if isinstance(node, dict):
            assert "default" not in node
            assert not (node.get("type") == "array" and node.get("maxItems") == 0)
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            if "enum" in node:
                assert node["enum"]
                counts.update(value for value in node["enum"] if value in catalog.entries)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(wire)
    assert set(counts) <= set(catalog.ids())
    if only_role in {None, "operator"}:
        assert set(counts) == set(catalog.ids())
    assert set(counts.values()) == {1}
    jsonschema.Draft202012Validator.check_schema(wire)

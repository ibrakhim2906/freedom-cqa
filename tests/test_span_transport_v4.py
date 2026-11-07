"""Offline v4 group projection and exact source-identity regressions."""

import json
from copy import deepcopy

import pytest
from span_fixtures import novel_fixture
from span_fixtures import wire_for as _wire_for

from cqa.atomic_dependencies import validate_atomic_dependencies
from cqa.models import Evidence, SelectedSourceSpan
from cqa.scoring import calculate_score, validate_evaluation
from cqa.source_spans import SourceCatalog, build_catalog
from cqa.span_transport import (
    decode_span_evaluation_v3,
    validate_source_citations,
)
from cqa.span_transport import (
    decode_span_evaluation_v4 as decode_span_evaluation,
)


def wire_for(*args, contract="span-v4"):
    return _wire_for(*args, contract=contract)


def decode(wire, conversation, checklist, *, historical=False):
    reader = decode_span_evaluation_v3 if historical else decode_span_evaluation
    result = reader(json.dumps(wire, ensure_ascii=False), conversation, checklist)
    validate_evaluation(result, conversation, checklist, require_audit=True)
    return result


def test_no_operator_literal_null_collections_are_normalized_after_schema_validation():
    from cqa.models import Conversation

    _, checklist, _ = novel_fixture()
    conversation = Conversation.model_validate({"id": "no-agent", "channel": "agent chat", "language": "EN",
        "messages": [{"id": "hello", "speaker": "client", "timestamp": "00:00", "text": "Hello."},
                     {"id": "end", "speaker": "system", "timestamp": "00:01", "text": "No human agent joined."}]})
    catalog = build_catalog(conversation, checklist)
    sid = catalog.ids("dialogue", roles={"client"})[0]
    wire = {"contract_version": "span-v4", "catalog_fingerprint": catalog.fingerprint,
        "judgments": {criterion.id: {"criterion_id": criterion.id, "status": "needs_review", "answer": None,
            "explanation": "No human operator joined the conversation.", "evidence": [{"span_id": sid}],
            "counterevidence": [], "checked_message_ids": ["hello", "end"],
            "uncertainty": "There is no human conduct to assess.", "deduction": None}
            for criterion in checklist.criteria},
        "request_coverage": [], "scope_notes": [], "factual_claims": None, "assertion_groups": None,
        "semantic_audit": {"version": "coverage-v4", "reviewed_message_ids": ["hello"], "exclusions": [
            {"evidence": {"span_id": sid}, "reason": "social", "criterion_ids": [c.id for c in checklist.criteria],
             "explanation": "Only a customer greeting occurred; no service request or operator assertion."}]}}
    result = decode(wire, conversation, checklist)
    assert result.factual_claims == [] and result.assertion_groups == []
    assert result.source_citations.projection == "derived-groups-v4"
    assert calculate_score(result, checklist)["provisional"] is True


def narrow_fixture(*, contract="span-v4", repeated=False):
    conversation, checklist, authored = novel_fixture()
    if repeated:
        original = conversation.messages[1].text
        replacement = original + "\n Holds must be announced before they begin."
        conversation.messages[1].text = replacement

        def update_full_citations(value):
            if isinstance(value, dict):
                if value.get("message_id") == "first" and value.get("quote") == original:
                    value["quote"] = replacement
                for item in value.values():
                    update_full_citations(item)
            elif isinstance(value, list):
                for item in value:
                    update_full_citations(item)

        update_full_citations(authored)
    wire = wire_for(authored, conversation, checklist, contract=contract)
    catalog = build_catalog(conversation, checklist)
    original_span = next(
        span for span in catalog.entries.values()
        if span.source_id == "first" and span.quote == " Edits apply immediately without review."
    )
    rule_spans = [
        span for span in catalog.entries.values()
        if span.source_id == "first" and span.quote == " Holds must be announced before they begin."
    ]
    assert len(rule_spans) == (2 if repeated else 1)
    wire["factual_claims"][0]["operator_evidence"] = [{"span_id": original_span.span_id}]
    wire["factual_claims"][1]["operator_evidence"] = [{"span_id": rule_spans[0].span_id}]
    return conversation, checklist, authored, wire, catalog, rule_spans


def group_selections(result, index=0):
    prefix = f"/assertion_groups/{index}/operator_evidence/"
    return [result.source_citations.selections[prefix + str(i)]
            for i in range(len(result.assertion_groups[index].operator_evidence))]


def replace_group_sources(result, catalog, selected, index=0):
    """Author real alternative selections, keeping every navigation slot valid."""
    result.assertion_groups[index].operator_evidence = [
        Evidence.model_validate(catalog.resolve(sid, kind="dialogue", roles={"operator"}))
        for sid in selected
    ]
    prefix = f"/assertion_groups/{index}/operator_evidence/"
    audit = result.source_citations
    audit.selections = {key: sid for key, sid in audit.selections.items() if not key.startswith(prefix)}
    audit.selections.update({prefix + str(i): sid for i, sid in enumerate(selected)})
    audit.spans = {
        sid: SelectedSourceSpan(**{
            field: getattr(catalog.entries[sid], field)
            for field in ["kind", "source_id", "field", "role", "start", "end"]
        })
        for sid in set(audit.selections.values())
    }


def test_v4_wire_omits_group_sources_and_projects_exact_declared_member_union():
    conversation, checklist, authored, wire, _, _ = narrow_fixture()
    before = deepcopy(wire)
    assert wire["contract_version"] == "span-v4"
    assert wire["semantic_audit"]["version"] == "coverage-v4"
    assert all(set(group) == {"group_id", "composition", "claim_ids"} for group in wire["assertion_groups"])
    result = decode(wire, conversation, checklist)
    assert wire == before
    assert result.semantic_audit.version == "coverage-v4"
    assert result.source_citations.projection == "derived-groups-v4"
    assert group_selections(result) == [
        wire["factual_claims"][index]["operator_evidence"][0]["span_id"] for index in [0, 1]
    ]
    # Distinct atoms may explicitly select the same original source occurrence.
    assert len(result.assertion_groups[1].operator_evidence) == 1
    assert [judgment.model_dump() for judgment in result.judgments] == authored["judgments"]
    assert [deduction.model_dump() for deduction in result.deductions] == authored["deductions"]
    assert calculate_score(result, checklist)["total"] == 30


def test_projection_uses_declared_member_order_without_searching_for_assertion_text():
    conversation, checklist, _, wire, _, _ = narrow_fixture()
    wire["assertion_groups"][0]["claim_ids"].reverse()
    result = decode(wire, conversation, checklist)
    assert group_selections(result) == [
        wire["factual_claims"][index]["operator_evidence"][0]["span_id"] for index in [1, 0]
    ]


def test_v4_rejects_provider_group_evidence_before_resolving_any_source(monkeypatch):
    conversation, checklist, _, wire, _, _ = narrow_fixture()
    wire["assertion_groups"][0]["operator_evidence"] = deepcopy(wire["factual_claims"][0]["operator_evidence"])

    def forbidden_resolution(*args, **kwargs):
        pytest.fail("Invalid provider schema must fail before any source resolution/projection")

    monkeypatch.setattr(SourceCatalog, "resolve", forbidden_resolution)
    with pytest.raises(ValueError, match="schema mismatch"):
        decode_span_evaluation(json.dumps(wire), conversation, checklist)


@pytest.mark.parametrize("fault", [
    "duplicate_claim", "duplicate_group", "duplicate_link", "unknown_link", "missing_link",
    "missing_group", "mismatched_group", "cross_group_link", "atomic_many", "all_of_one", "empty_group",
])
def test_v4_rejects_invalid_declared_membership_before_source_resolution(fault, monkeypatch):
    conversation, checklist, _, wire, _, _ = narrow_fixture()
    groups, claims = wire["assertion_groups"], wire["factual_claims"]
    if fault == "duplicate_claim":
        claims[1]["claim_id"] = claims[0]["claim_id"]
    elif fault == "duplicate_group":
        groups[1]["group_id"] = groups[0]["group_id"]
    elif fault == "duplicate_link":
        groups[0]["claim_ids"].append(groups[0]["claim_ids"][0])
    elif fault == "unknown_link":
        groups[0]["claim_ids"][0] = "invented-claim"
    elif fault == "missing_link":
        groups[0]["claim_ids"].pop()
        groups[0]["composition"] = "atomic"
    elif fault == "missing_group":
        groups.pop()
    elif fault == "mismatched_group":
        claims[0]["assertion_group_id"] = groups[1]["group_id"]
    elif fault == "cross_group_link":
        groups[1]["claim_ids"].append(groups[0]["claim_ids"][0])
    elif fault == "atomic_many":
        groups[0]["composition"] = "atomic"
    elif fault == "all_of_one":
        groups[0]["claim_ids"].pop()
    else:
        groups[0]["claim_ids"] = []

    def forbidden_resolution(*args, **kwargs):
        pytest.fail("Invalid declared links must fail before group sources can be projected/resolved")

    monkeypatch.setattr(SourceCatalog, "resolve", forbidden_resolution)
    with pytest.raises(ValueError):
        decode_span_evaluation(json.dumps(wire), conversation, checklist)


@pytest.mark.parametrize("validate", [validate_source_citations, validate_atomic_dependencies])
@pytest.mark.parametrize("fault", ["broader", "extra", "dropped", "duplicate"])
def test_saved_v4_groups_require_exact_span_union_even_with_valid_quotes_and_metadata(validate, fault):
    conversation, checklist, _, wire, catalog, _ = narrow_fixture()
    result = decode(wire, conversation, checklist)
    selected = group_selections(result)
    full = next(s.span_id for s in catalog.entries.values() if s.source_id == "first" and s.is_full)
    if fault == "broader":
        selected = [full]
    elif fault == "extra":
        selected.append(full)
    elif fault == "dropped":
        selected.pop()
    else:
        selected.append(selected[0])
    replace_group_sources(result, catalog, selected)
    with pytest.raises(ValueError, match="exact selected span union"):
        validate(result, conversation, checklist)


@pytest.mark.parametrize("validate", [validate_source_citations, validate_atomic_dependencies])
def test_equal_text_at_another_operator_offset_cannot_replace_group_member_source(validate):
    conversation, checklist, _, wire, catalog, repeated = narrow_fixture(repeated=True)
    result = decode(wire, conversation, checklist)
    assert repeated[0].quote == repeated[1].quote and repeated[0].start != repeated[1].start
    previous_evidence = deepcopy(result.assertion_groups[0].operator_evidence)
    selected = group_selections(result)
    selected[1] = repeated[1].span_id
    replace_group_sources(result, catalog, selected)
    assert result.assertion_groups[0].operator_evidence == previous_evidence
    with pytest.raises(ValueError, match="exact selected span union"):
        validate(result, conversation, checklist)


def test_v3_reader_is_explicit_and_preserves_historical_broader_group_selections():
    conversation, checklist, _, historical, _, _ = narrow_fixture(contract="span-v3")
    before = deepcopy(historical)
    with pytest.raises(ValueError, match="explicit span-v4"):
        decode_span_evaluation(json.dumps(historical), conversation, checklist)
    result = decode(historical, conversation, checklist, historical=True)
    assert historical == before
    assert result.semantic_audit.version == "coverage-v3"
    assert result.source_citations.projection is None
    assert group_selections(result) == [historical["assertion_groups"][0]["operator_evidence"][0]["span_id"]]
    assert len(result.assertion_groups[0].operator_evidence) == 1
    assert calculate_score(result, checklist)["total"] == 30
    _, _, _, current, _, _ = narrow_fixture()
    with pytest.raises(ValueError, match="explicit span-v3"):
        decode_span_evaluation_v3(json.dumps(current), conversation, checklist)


@pytest.mark.parametrize("fault", ["drop_projection", "downgrade_audit"])
def test_persisted_projection_version_cannot_silently_use_historical_group_rules(fault):
    conversation, checklist, _, wire, _, _ = narrow_fixture()
    result = decode(wire, conversation, checklist)
    if fault == "drop_projection":
        result.source_citations.projection = None
    else:
        result.semantic_audit.version = "coverage-v3"
    with pytest.raises(ValueError, match="requires explicit derived-groups-v4|no contract downgrade"):
        validate_source_citations(result, conversation, checklist)


def test_v4_retains_explicit_observation_guard_and_cannot_promote_context_to_proof():
    conversation, checklist, _, wire, _, _ = narrow_fixture()
    missing_observation = deepcopy(wire)
    missing_observation["factual_claims"][3]["observation"] = None
    with pytest.raises(ValueError, match="schema mismatch|explicitly declared observation metadata"):
        decode(missing_observation, conversation, checklist)
    context_only = deepcopy(wire)
    claim = context_only["factual_claims"][3]
    claim["context_evidence"] = deepcopy(claim["proof"]["premises"][0]["evidence"])
    claim["proof"] = None
    claim["observation"] = None
    with pytest.raises(ValueError, match="schema mismatch|proof=null"):
        decode(context_only, conversation, checklist)

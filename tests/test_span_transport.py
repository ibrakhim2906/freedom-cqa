"""Unseen offline v3 transport/provenance regressions; no paid requests."""

import json
from copy import deepcopy

import pytest
from span_fixtures import dependent_fixture, novel_fixture, wire_for

from cqa.atomic_dependencies import assertion_group_status
from cqa.models import Evaluation
from cqa.scoring import calculate_score, validate_evaluation
from cqa.source_spans import build_catalog
from cqa.span_transport import decode_span_evaluation


def decode(wire, conversation, checklist):
    result = decode_span_evaluation(json.dumps(wire, ensure_ascii=False), conversation, checklist)
    validate_evaluation(result, conversation, checklist, require_audit=True)
    return result


@pytest.mark.parametrize("fault", ["duplicate_version", "duplicate_span", "NaN", "Infinity", "-Infinity"])
def test_raw_transport_rejects_duplicate_fields_and_nonstandard_json_without_discarding_values(fault):
    conversation, checklist, data = novel_fixture()
    wire = wire_for(data, conversation, checklist)
    text = json.dumps(wire, ensure_ascii=False)
    if fault == "duplicate_version":
        text = text.replace('"contract_version": "span-v3"',
                            '"contract_version": "legacy-v0", "contract_version": "span-v3"', 1)
    elif fault == "duplicate_span":
        text = text.replace('"span_id": ', '"span_id": "invented-span", "span_id": ', 1)
    else:
        text = text.replace('"material": true', '"material": ' + fault, 1)
    assert text != json.dumps(wire, ensure_ascii=False)
    with pytest.raises(ValueError, match="duplicate object fields|standard JSON"):
        decode_span_evaluation(text, conversation, checklist)


@pytest.mark.parametrize("criterion_id", ["span_id", "rule_span_id", "observation", "exclusions", "$defs", "a/b~c"])
def test_dynamic_criterion_names_cannot_be_mistaken_for_transport_objects(criterion_id):
    conversation, checklist, data = novel_fixture()
    checklist.criteria[0].id = criterion_id

    def rename(value):
        if isinstance(value, dict):
            return {key: rename(item) for key, item in value.items()}
        if isinstance(value, list):
            return [rename(item) for item in value]
        return criterion_id if value == "resolution" else value

    data = rename(data)
    result = decode(wire_for(data, conversation, checklist), conversation, checklist)
    assert result.judgments[0].criterion_id == criterion_id
    assert calculate_score(result, checklist)["total"] == 30


@pytest.mark.parametrize("fault", ["offset", "role", "source", "missing_span", "extra_span"])
def test_saved_navigation_metadata_cannot_change_selected_source_identity(fault):
    conversation, checklist, data = novel_fixture()
    result = decode(wire_for(data, conversation, checklist), conversation, checklist)
    sid = next(iter(result.source_citations.spans))
    span = result.source_citations.spans[sid]
    if fault == "offset":
        span.end += 1
    elif fault == "role":
        span.role = "bot" if span.role != "bot" else "client"
    elif fault == "source":
        span.source_id = "invented-source"
    elif fault == "missing_span":
        result.source_citations.spans.pop(sid)
    else:
        result.source_citations.spans["invented-span"] = span.model_copy()
    with pytest.raises(ValueError, match="Source navigation|offsets/identity"):
        validate_evaluation(result, conversation, checklist, require_audit=True)


def repeated_observation_fixture():
    conversation, checklist, data = novel_fixture()
    sentence = "I clicked Download and opened sample.pdf 👩🏽‍💻."
    message = next(m for m in conversation.messages if m.id == "done")
    message.text = sentence + "\n" + sentence + "\nDoes the guide give a deadline?"

    def narrow(value):
        if isinstance(value, dict):
            if value.get("message_id") == "done" and "quote" in value:
                value["quote"] = sentence
            for item in value.values():
                narrow(item)
        elif isinstance(value, list):
            for item in value:
                narrow(item)

    narrow(data)
    catalog = build_catalog(conversation, checklist)
    duplicates = [s for s in catalog.entries.values() if s.kind == "dialogue" and
                  s.source_id == "done" and s.quote == sentence]
    assert len(duplicates) == 2 and duplicates[0].start != duplicates[1].start
    return conversation, checklist, wire_for(data, conversation, checklist), duplicates


def test_distinct_identical_source_occurrences_can_both_be_selected_in_one_proof():
    conversation, checklist, wire, duplicates = repeated_observation_fixture()
    wire["factual_claims"][3]["proof"]["premises"][0]["evidence"] = [
        {"span_id": source.span_id} for source in duplicates]
    result = decode(wire, conversation, checklist)
    assert calculate_score(result, checklist)["total"] == 30
    assert len(result.factual_claims[3].dialogue_evidence) == 2
    assert result.factual_claims[3].dialogue_evidence[0] == result.factual_claims[3].dialogue_evidence[1]
    selected = result.source_citations.selections
    first = selected["/factual_claims/3/dialogue_evidence/0"]
    second = selected["/factual_claims/3/dialogue_evidence/1"]
    assert first != second and result.source_citations.spans[first].start != result.source_citations.spans[second].start


def test_identical_quote_text_at_another_offset_cannot_replace_the_selected_proof_leaf():
    conversation, checklist, wire, duplicates = repeated_observation_fixture()
    result = decode(wire, conversation, checklist)
    assert calculate_score(result, checklist)["total"] == 30
    pointer = "/factual_claims/3/dialogue_evidence/0"
    previous = result.source_citations.selections[pointer]
    other = next(s for s in duplicates if s.span_id != previous)
    result.source_citations.selections[pointer] = other.span_id
    result.source_citations.spans[other.span_id] = type(next(iter(result.source_citations.spans.values())))(
        **{field: getattr(other, field) for field in ["kind", "source_id", "field", "role", "start", "end"]})
    # Both selected strings are still exact and identical; only source identity
    # exposes the false claim that the flat view preserves its declared premise.
    with pytest.raises(ValueError, match="exact selected spans"):
        validate_evaluation(result, conversation, checklist, require_audit=True)


def test_unseen_custom_rubric_resolves_all_citation_kinds_and_preserves_independent_deductions():
    conversation, checklist, data = novel_fixture()
    before = deepcopy(data)
    result = decode(wire_for(data, conversation, checklist), conversation, checklist)
    assert data == before, "Test serialization cannot mutate the authored judgments/evidence"
    assert result.judgments == Evaluation.model_validate(data).judgments
    assert result.deductions == Evaluation.model_validate(data).deductions
    assert calculate_score(result, checklist)["total"] == 30
    assert {d.criterion_id for d in result.deductions} == {"resolution", "process", "closing"}
    index = {claim.claim_id: claim for claim in result.factual_claims}
    assert assertion_group_status(result.assertion_groups[0], index) == "contradicted"
    assert index["original"].assessment.lifecycle == "corrected"
    assert index["hold-rule"].status == "supported"
    assert index["download"].status == "supported"
    assert index["download"].supported_proposition == index["download"].claim
    pointers = result.source_citations.selections
    for pointer in [
        "/judgments/0/evidence/0", "/deductions/0/rule_quote",
        "/factual_claims/0/assessment/correction/operator_evidence/0",
        "/factual_claims/0/assessment/correction/outcome_evidence/0",
        "/factual_claims/0/assessment/correction/reference_evidence/0",
        "/factual_claims/0/proof/premises/0/reference_evidence/0",
        "/factual_claims/1/proof/premises/0/rule_evidence/0",
        "/factual_claims/0/reference_evidence/0", "/factual_claims/1/rule_evidence/0",
        "/factual_claims/3/dialogue_evidence/0",
        "/request_coverage/1/support/omission/context_evidence/1",
        "/semantic_audit/exclusions/0/evidence", "/assertion_groups/0/operator_evidence/0",
    ]:
        assert pointer in pointers


def test_canonical_observation_has_one_generated_proposition_and_explicit_alias():
    conversation, checklist, data = novel_fixture()
    wire = wire_for(data, conversation, checklist)
    observation = wire["factual_claims"][3]
    assert observation["observation"] == {"target": "claim", "scope": "task_completed"}
    assert not {"supported_proposition", "dialogue_evidence", "observation_scope", "reference_evidence", "rule_evidence"} & observation.keys()
    result = decode(wire, conversation, checklist)
    claim = result.factual_claims[3]
    assert claim.claim == claim.supported_proposition == "The sample PDF was downloaded and opened."
    assert claim.dialogue_evidence[0].quote == conversation.messages[2].text
    assert "👩🏽‍💻" in claim.dialogue_evidence[0].quote


@pytest.mark.parametrize("fault", ["unknown_span", "extra_quote", "wrong_kind", "answer_role", "proof_role", "rule_criterion"])
def test_model_cannot_invent_or_retype_citations_or_choose_wrong_source_class(fault):
    conversation, checklist, data = novel_fixture()
    wire = wire_for(data, conversation, checklist)
    catalog = build_catalog(conversation, checklist)
    if fault == "unknown_span":
        wire["judgments"]["resolution"]["evidence"][0]["span_id"] = "d_o_9999"
    elif fault == "extra_quote":
        wire["judgments"]["resolution"]["evidence"][0]["quote"] = "Invented quotation"
    elif fault == "wrong_kind":
        wire["judgments"]["resolution"]["evidence"][0]["span_id"] = catalog.ids("reference")[0]
    elif fault == "answer_role":
        wire["request_coverage"][0]["support"]["evidence"][0]["span_id"] = catalog.ids("dialogue", roles={"client"})[0]
    elif fault == "proof_role":
        wire["factual_claims"][3]["proof"]["premises"][0]["evidence"][0]["span_id"] = catalog.ids("dialogue", roles={"operator"})[0]
    else:
        wire["judgments"]["resolution"]["deduction"]["rule_span_id"] = catalog.ids("rule", criterion_id="process")[0]
    with pytest.raises(ValueError):
        decode(wire, conversation, checklist)


@pytest.mark.parametrize("fault", ["source_text", "source_role", "source_scope", "rule_version", "fingerprint"])
def test_catalog_binding_rejects_other_source_revisions_without_quote_search(fault):
    conversation, checklist, data = novel_fixture()
    wire = wire_for(data, conversation, checklist)
    if fault == "source_text":
        conversation.messages[2].text += " Changed actual outcome."
    elif fault == "source_role":
        conversation.messages[2].speaker = "operator"
    elif fault == "source_scope":
        conversation.knowledge_scope = "other-lab"
    elif fault == "rule_version":
        checklist.version = "different"
    else:
        wire["catalog_fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="catalog/source revision"):
        decode(wire, conversation, checklist)


def test_literal_null_for_forbidden_collections_is_explicit_and_not_a_missing_default():
    conversation, checklist, data = novel_fixture()
    wire = wire_for(data, conversation, checklist)
    assert wire["request_coverage"][0]["withdrawal_message_ids"] is None
    assert wire["request_coverage"][0]["support"]["unresolved_aspects"] is None
    assert wire["request_coverage"][1]["answer_message_ids"] is None
    assert wire["request_coverage"][1]["support"]["evidence"] is None
    result = decode(wire, conversation, checklist)
    assert result.request_coverage[0].withdrawal_message_ids == []
    assert result.request_coverage[0].support.unresolved_aspects == []
    assert result.request_coverage[1].answer_message_ids == []
    assert result.request_coverage[1].support.evidence == []
    for path in ["missing", "nonempty", "array_instead_of_null"]:
        bad = deepcopy(wire)
        if path == "missing":
            bad["request_coverage"][0].pop("withdrawal_message_ids")
        else:
            bad["request_coverage"][0]["withdrawal_message_ids"] = ["done"] if path == "nonempty" else []
        with pytest.raises(ValueError):
            decode(bad, conversation, checklist)


@pytest.mark.parametrize("fault", ["missing_contract", "old_contract", "missing_audit", "old_audit", "missing_groups",
                                  "missing_claim_id", "missing_proof", "missing_fixed", "missing_observation", "extra_proposition"])
def test_current_wire_has_no_legacy_fallback_or_silent_new_metadata_defaults(fault):
    conversation, checklist, data = novel_fixture()
    wire = wire_for(data, conversation, checklist)
    if fault == "missing_contract":
        wire.pop("contract_version")
    elif fault == "old_contract":
        wire["contract_version"] = "span-v2"
    elif fault == "missing_audit":
        wire.pop("semantic_audit")
    elif fault == "old_audit":
        wire["semantic_audit"]["version"] = "coverage-v2"
    elif fault == "missing_groups":
        wire.pop("assertion_groups")
    elif fault == "missing_claim_id":
        wire["factual_claims"][0].pop("claim_id")
    elif fault == "missing_proof":
        wire["factual_claims"][0].pop("proof")
    elif fault == "missing_fixed":
        wire["factual_claims"][0]["assessment"]["impacts"][0].pop("fixed_claim_ids")
    elif fault == "missing_observation":
        wire["factual_claims"][3].pop("observation")
    else:
        wire["factual_claims"][3]["supported_proposition"] = "A second independently generated paraphrase."
    with pytest.raises(ValueError):
        decode(wire, conversation, checklist)


@pytest.mark.parametrize("fault", ["quote", "wrong_selection", "missing_selection", "extra_selection", "canonical_alias",
                                  "missing_fixed", "uncovered_atom", "context_as_proof"])
def test_persisted_or_declared_proof_tampering_remains_strictly_rejected(fault):
    conversation, checklist, data = novel_fixture()
    result = decode(wire_for(data, conversation, checklist), conversation, checklist)
    if fault == "quote":
        result.judgments[0].evidence[0].quote = "A locally repaired invented string."
    elif fault == "wrong_selection":
        result.source_citations.selections["/judgments/0/evidence/0"] = build_catalog(conversation, checklist).ids("reference")[0]
    elif fault == "missing_selection":
        result.source_citations.selections.pop("/judgments/0/evidence/0")
    elif fault == "extra_selection":
        result.source_citations.selections["/unused"] = next(iter(result.source_citations.selections.values()))
    elif fault == "canonical_alias":
        result.factual_claims[3].supported_proposition = "A broader policy than the model's canonical claim."
    elif fault == "missing_fixed":
        result.factual_claims[0].assessment.impacts[0].fixed_claim_ids.pop()
    elif fault == "uncovered_atom":
        result.assertion_groups[0].claim_ids.remove("hold-rule")
    else:
        # Every original selection remains exact. But removing the proof and
        # relying only on matching context must not preserve known truth.
        result.factual_claims[3].proof = None
        result.factual_claims[3].context_evidence = deepcopy(result.factual_claims[3].dialogue_evidence)
    with pytest.raises(ValueError):
        validate_evaluation(result, conversation, checklist, require_audit=True)


def test_test_serializer_refuses_non_catalog_quotes_and_missing_atomic_metadata():
    conversation, checklist, data = novel_fixture()
    bad = deepcopy(data)
    bad["judgments"][0]["evidence"][0]["quote"] = "Not the selected source text."
    with pytest.raises(AssertionError, match="not a repaired quote"):
        wire_for(bad, conversation, checklist)
    bad = deepcopy(data)
    bad["factual_claims"][0]["claim_id"] = None
    with pytest.raises(AssertionError):
        wire_for(bad, conversation, checklist)


def test_transitive_claim_dependency_resolves_exact_source_union_without_retyping():
    conversation, checklist, data = dependent_fixture()
    wire = wire_for(data, conversation, checklist)
    dependent = wire["factual_claims"][1]
    assert dependent["proof"]["relation"] == "all_of"
    assert dependent["proof"]["premises"][0]["evidence"] is None
    assert dependent["proof"]["premises"][0]["reference_evidence"] is None
    result = decode(wire, conversation, checklist)
    assert calculate_score(result, checklist)["total"] == 100
    eligibility = result.factual_claims[1]
    assert {e.reference_id for e in eligibility.reference_evidence} == {"private-classification", "route-policy"}
    assert eligibility.dialogue_evidence == []
    assert eligibility.proof.required_premise_ids == ["classification", "policy"]
    assert "/factual_claims/1/reference_evidence/0" in result.source_citations.selections
    assert "/factual_claims/1/reference_evidence/1" in result.source_citations.selections


@pytest.mark.parametrize("fault", ["missing_premise", "unrequired_premise", "wrong_dependency_status", "unknown_dependency", "cycle"])
def test_transitive_proof_cannot_drop_needed_policy_or_forge_canonical_dependency(fault):
    conversation, checklist, data = dependent_fixture()
    wire = wire_for(data, conversation, checklist)
    p = wire["factual_claims"][1]["proof"]
    if fault == "missing_premise":
        p["premises"].pop()
    elif fault == "unrequired_premise":
        p["required_premise_ids"].pop()
    elif fault == "wrong_dependency_status":
        p["premises"][0]["required_status"] = "contradicted"
    elif fault == "unknown_dependency":
        p["premises"][0]["depends_on_claim_id"] = "unknown"
    else:
        wire["factual_claims"][0]["proof"]["premises"] = [deepcopy(p["premises"][0])]
        wire["factual_claims"][0]["proof"]["premises"][0]["depends_on_claim_id"] = "eligible"
        wire["factual_claims"][0]["proof"]["premises"][0]["premise_id"] = "record"
    with pytest.raises(ValueError):
        decode(wire, conversation, checklist)

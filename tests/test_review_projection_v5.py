"""Offline review projection regressions; explicit historical readers stay strict."""

import json
from copy import deepcopy

import pytest
from span_fixtures import novel_fixture, wire_for

from cqa.models import Evaluation
from cqa.review_projection import PROJECTION, project_review_links, validate_review_projection
from cqa.scoring import calculate_score, validate_evaluation
from cqa.source_spans import SourceCatalog
from cqa.span_transport import (
    decode_span_evaluation,
    decode_span_evaluation_v3,
    decode_span_evaluation_v4,
    validate_source_citations,
)


def fixture(*, extras=None):
    conversation, checklist, authored = novel_fixture()
    # Keep each authored declaration narrow so the projection cannot pass merely
    # by copying a previously authored all-transcript judgment review list.
    for deduction in authored["deductions"]:
        deduction["checked_message_ids"] = []
    for claim in authored["factual_claims"]:
        for impact in claim["assessment"]["impacts"]:
            impact["checked_message_ids"] = []
    wire = wire_for(authored, conversation, checklist, contract="span-v4")
    wire["contract_version"] = "span-v5"
    wire["semantic_audit"]["version"] = "coverage-v5"
    for cid, judgment in wire["judgments"].items():
        judgment.pop("checked_message_ids")
        judgment["additional_checked_message_ids"] = (extras or {}).get(cid, [])
    return conversation, checklist, authored, wire


def decode(wire, conversation, checklist):
    result = decode_span_evaluation(json.dumps(wire, ensure_ascii=False), conversation, checklist)
    validate_evaluation(result, conversation, checklist, require_audit=True)
    return result


def test_v5_projects_exact_explicit_union_without_changing_scores_or_evidence():
    conversation, checklist, authored, wire = fixture(extras={"resolution": ["back", "q"]})
    before = deepcopy(wire)
    # Counterevidence and an unquoted deduction check both independently declare review.
    wire["judgments"]["resolution"]["counterevidence"] = deepcopy(wire["judgments"]["process"]["evidence"])
    wire["judgments"]["resolution"]["deduction"]["checked_message_ids"] = ["bye"]
    result = decode(wire, conversation, checklist)
    checked = {judgment.criterion_id: judgment.checked_message_ids for judgment in result.judgments}
    assert checked == {
        "resolution": ["q", "first", "done", "held", "back", "fixed", "no-use", "bye"],
        "process": ["first", "held", "fixed"],
        "closing": ["bye"],
    }
    assert result.source_citations.projection == PROJECTION
    assert result.source_citations.additional_checked_message_ids == {
        "resolution": ["back", "q"], "process": [], "closing": []}
    assert result.judgments[0].evidence[0].message_id == "done"
    assert [item.message_id for item in result.judgments[0].counterevidence] == ["held"]
    assert [(item.status, item.answer) for item in result.judgments] == [
        (item["status"], item["answer"]) for item in authored["judgments"]]
    assert calculate_score(result, checklist)["total"] == 30
    assert before["judgments"]["resolution"]["additional_checked_message_ids"] == ["back", "q"]
    # Decoding does not mutate the caller's JSON object or promote review links to evidence.
    assert "checked_message_ids" not in wire["judgments"]["resolution"]
    assert len(result.judgments[0].evidence) == 1


def test_requests_and_wording_have_no_implicit_criterion_binding():
    conversation, checklist, _, wire = fixture()
    result = decode(wire, conversation, checklist)
    assert all("q" not in judgment.checked_message_ids for judgment in result.judgments)
    # The request remains explicitly represented, including its actual source.
    assert result.request_coverage[0].request_message_ids == ["q"]
    assert result.judgments[2].checked_message_ids == ["bye"]


def test_v5_fixes_review_link_fragility_and_explicit_v4_keeps_rejecting_it():
    conversation, checklist, authored, wire = fixture(extras={"closing": ["q"]})
    authored["judgments"][2]["evidence"] = []
    authored["judgments"][2]["checked_message_ids"] = ["q"]
    historical = wire_for(authored, conversation, checklist, contract="span-v4")
    old = decode_span_evaluation_v4(json.dumps(historical), conversation, checklist)
    with pytest.raises(ValueError, match="Semantic exclusion must link to a judgment reviewing that source"):
        validate_evaluation(old, conversation, checklist, require_audit=True)
    wire["judgments"]["closing"]["evidence"] = []
    result = decode(wire, conversation, checklist)
    closing = next(item for item in result.judgments if item.criterion_id == "closing")
    assert closing.checked_message_ids == ["q", "bye"]
    assert closing.evidence == []
    assert closing.answer == "no"


@pytest.mark.parametrize("fault", ["provider_checked", "missing_additional", "unknown_additional", "duplicate_additional"])
def test_v5_rejects_invalid_provider_review_declarations(fault, monkeypatch):
    conversation, checklist, _, wire = fixture()
    judgment = wire["judgments"]["resolution"]
    if fault == "provider_checked":
        judgment["checked_message_ids"] = ["q"]
    elif fault == "missing_additional":
        judgment.pop("additional_checked_message_ids")
    elif fault == "unknown_additional":
        judgment["additional_checked_message_ids"] = ["invented"]
    else:
        judgment["additional_checked_message_ids"] = ["q", "q"]
    if fault in {"provider_checked", "missing_additional", "unknown_additional"}:
        def forbidden_resolution(*args, **kwargs):
            pytest.fail("The complete provider schema must validate before source resolution")
        monkeypatch.setattr(SourceCatalog, "resolve", forbidden_resolution)
    with pytest.raises(ValueError, match="schema mismatch|valid unique"):
        decode_span_evaluation(json.dumps(wire), conversation, checklist)


@pytest.mark.parametrize("fault", [
    "drop_review", "extra_review", "duplicate_review", "reverse_reviews", "drop_map", "drop_criterion",
    "extra_criterion", "unknown_extra", "duplicate_extra", "bad_marker", "downgrade",
])
def test_v5_rejects_saved_review_projection_tampering(fault):
    conversation, checklist, _, wire = fixture()
    result = decode(wire, conversation, checklist)
    audit = result.source_citations
    if fault == "drop_review":
        result.judgments[0].checked_message_ids.pop()
    elif fault == "extra_review":
        result.judgments[0].checked_message_ids.insert(0, "q")
    elif fault == "duplicate_review":
        result.judgments[0].checked_message_ids.append("first")
    elif fault == "reverse_reviews":
        result.judgments[0].checked_message_ids.reverse()
    elif fault == "drop_map":
        audit.additional_checked_message_ids = None
    elif fault == "drop_criterion":
        audit.additional_checked_message_ids.pop("closing")
    elif fault == "extra_criterion":
        audit.additional_checked_message_ids["consultation"] = []
    elif fault == "unknown_extra":
        audit.additional_checked_message_ids["closing"] = ["invented"]
    elif fault == "duplicate_extra":
        audit.additional_checked_message_ids["closing"] = ["bye", "bye"]
    elif fault == "bad_marker":
        audit.projection = "derived-groups-v4"
    else:
        result.semantic_audit.version = "coverage-v4"
    with pytest.raises(ValueError, match="review|Review|coverage-v5|provenance|chronological"):
        validate_source_citations(result, conversation, checklist)


def test_v5_rejects_dropped_explicit_source_provenance():
    conversation, checklist, _, wire = fixture()
    result = decode(wire, conversation, checklist)
    result.source_citations.selections.pop("/factual_claims/0/assessment/correction/operator_evidence/0")
    with pytest.raises(ValueError):
        validate_source_citations(result, conversation, checklist)


def test_v5_roundtrip_persisted_projection_remains_exact():
    conversation, checklist, _, wire = fixture(extras={"closing": ["q"]})
    result = decode(wire, conversation, checklist)
    saved = Evaluation.model_validate_json(result.model_dump_json())
    validate_evaluation(saved, conversation, checklist, require_audit=True)
    assert saved == result


@pytest.mark.parametrize("field", ["deduction", "impact"])
def test_v5_rejects_duplicate_nonjudgment_checked_source_links(field):
    conversation, checklist, _, wire = fixture()
    target = (wire["judgments"]["resolution"]["deduction"] if field == "deduction" else
              wire["factual_claims"][0]["assessment"]["impacts"][0])
    target["checked_message_ids"] = ["q", "q"]
    with pytest.raises(ValueError, match="schema mismatch|valid unique"):
        decode_span_evaluation(json.dumps(wire), conversation, checklist)


def test_v5_chronology_uses_original_message_sequence_and_preserves_correction_guards():
    conversation, checklist, _, wire = fixture()
    result = decode(wire, conversation, checklist)
    assert result.judgments[0].checked_message_ids == ["first", "done", "fixed", "no-use"]
    # Explicit source order governs chronology even when display timestamps collide.
    for message in conversation.messages:
        message.timestamp = "00:00"
    validate_review_projection(result, conversation, checklist)
    correction = result.factual_claims[0].assessment.correction
    correction.operator_evidence = deepcopy(result.factual_claims[0].operator_evidence)
    with pytest.raises(ValueError, match="Correction must follow"):
        project_review_links(result, conversation, checklist)


def test_current_decoder_requires_v5_and_historical_readers_remain_explicit():
    conversation, checklist, authored, wire = fixture()
    for contract, reader in [("span-v4", decode_span_evaluation_v4), ("span-v3", decode_span_evaluation_v3)]:
        historical = wire_for(authored, conversation, checklist, contract=contract)
        result = reader(json.dumps(historical), conversation, checklist)
        validate_evaluation(result, conversation, checklist, require_audit=True)
        assert result.source_citations.additional_checked_message_ids is None
        assert result.judgments[0].checked_message_ids == authored["judgments"][0]["checked_message_ids"]
        with pytest.raises(ValueError, match="explicit span-v5"):
            decode_span_evaluation(json.dumps(historical), conversation, checklist)
        with pytest.raises(ValueError, match=f"explicit {contract}"):
            reader(json.dumps(wire), conversation, checklist)


def test_v5_no_operator_keeps_explicit_null_claims_and_projects_declared_review():
    from cqa.models import Conversation
    from cqa.source_spans import build_catalog

    _, checklist, _ = novel_fixture()
    conversation = Conversation.model_validate({"id": "no-agent", "channel": "agent chat", "language": "EN",
        "messages": [{"id": "hello", "speaker": "client", "timestamp": "00:00", "text": "Hello."},
                     {"id": "end", "speaker": "system", "timestamp": "00:01", "text": "No human agent joined."}]})
    catalog = build_catalog(conversation, checklist)
    sid = catalog.ids("dialogue", roles={"client"})[0]
    wire = {"contract_version": "span-v5", "catalog_fingerprint": catalog.fingerprint,
        "judgments": {criterion.id: {"criterion_id": criterion.id, "status": "needs_review", "answer": None,
            "explanation": "No human operator joined the conversation.", "evidence": [{"span_id": sid}],
            "counterevidence": [], "additional_checked_message_ids": ["end"],
            "uncertainty": "There is no human conduct to assess.", "deduction": None}
            for criterion in checklist.criteria},
        "request_coverage": [], "scope_notes": [], "factual_claims": None, "assertion_groups": None,
        "semantic_audit": {"version": "coverage-v5", "reviewed_message_ids": ["hello"], "exclusions": [
            {"evidence": {"span_id": sid}, "reason": "social", "criterion_ids": [c.id for c in checklist.criteria],
             "explanation": "Only a customer greeting occurred; no service request or operator assertion."}]}}
    result = decode(wire, conversation, checklist)
    assert result.factual_claims == [] and result.assertion_groups == []
    assert result.source_citations.projection == PROJECTION
    assert all(j.checked_message_ids == ["hello", "end"] for j in result.judgments)
    assert all(j.status == "needs_review" and j.answer is None for j in result.judgments)
    assert calculate_score(result, checklist)["provisional"] is True

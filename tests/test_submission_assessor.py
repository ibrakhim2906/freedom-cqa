"""Focused contract/export integration; these fixtures do not measure model quality."""

from copy import deepcopy

import pytest

from cqa.assessor import CONTRACT_VERSION, validate_native
from cqa.models import Conversation
from cqa.rubric import official_checklist
from cqa.source_spans import build_catalog
from cqa.submission import result_for


def export_fixture(*, conditional=False, uses_reference=False, version="rubric-assessor-v2"):
    conversation = Conversation.model_validate({
        "id": "adapter-source", "channel": "agent chat", "language": "EN",
        "knowledge_scope": "fictional-demo", "occurred_on": "2026-11-08",
        "messages": [
            {"id": "m1", "timestamp": "00:01", "speaker": "client", "text": "How do I open Reports?"},
            {"id": "m2", "timestamp": "00:02", "speaker": "operator",
             "text": "Hello, I am Leila. Select Reports in the menu. Can I help with anything else? Goodbye!"},
            {"id": "m3", "timestamp": "00:03", "speaker": "client", "text": "Reports opened."}],
        "references": [{"id": "guide", "text": "Select Reports in the menu to open Reports.",
                        "provenance": "Fictional adapter test policy", "scope": "fictional-demo",
                        "date_basis": "snapshot", "snapshot_on": "2026-11-08"}],
        "reference_context": ({"mode": "snapshot_review", "scope": "fictional-demo",
            "as_of": "2026-11-08", "rationale": "Explicit adapter test snapshot.",
            "pack_id": "demo", "pack_sha256": "a" * 64} if conditional else None)})
    checklist = official_checklist()
    catalog = build_catalog(conversation, checklist)

    def span(kind, source_id):
        return next(x.span_id for x in catalog.entries.values()
                    if x.kind == kind and x.source_id == source_id and x.is_full)

    answers = {"contact": "yes", "needs": None, "identity": None, "consultation": "20",
               "empathy": "yes", "management": "10", "closing": "yes", "serious": "no"}
    judgments = {}
    for criterion in checklist.criteria:
        answer = answers[criterion.id]
        judgments[criterion.id] = {
            "status": "scored" if answer is not None else "not_applicable", "answer": answer,
            "explanation": "Isolated export-contract fixture, not a quality-reference label.",
            "evidence_span_ids": [span("dialogue", "m2")], "counterevidence_span_ids": [],
            "omission": None, "factual_basis": "not_required",
            "factual_support_span_ids": [], "missing_information": None, "review_warnings": []}
    judgments["consultation"].update(
        factual_basis="policy_reference" if uses_reference else "observed_interaction",
        factual_support_span_ids=[span("reference", "guide") if uses_reference else span("dialogue", "m3")])
    native = validate_native({"contract_version": version, "catalog_fingerprint": catalog.fingerprint,
        "judgments": judgments, "request_coverage": [], "scope_notes": []}, conversation, checklist)
    record = {"status": "completed", "strategy": "assessor", "assessment": native.native,
              "evaluation": native.evaluation.model_dump(), "model": "TEST-ONLY"}
    return conversation, checklist, record


def test_conditional_context_only_blocks_criteria_relying_on_conditional_references():
    conversation, checklist, record = export_fixture(conditional=True)
    assert result_for(conversation, conversation, checklist, record)["status"] == "ok"
    conversation, checklist, record = export_fixture(conditional=True, uses_reference=True)
    record["assessment"]["criteria"]["consultation"]["uses_conditional_reference"] = False
    row = result_for(conversation, conversation, checklist, record)
    assert row["status"] == "error" and "Conditional snapshot" in row["error"]


@pytest.mark.parametrize("corruption", ["projection", "missing_native", "unknown_contract"])
def test_compact_export_rejects_tampered_or_missing_native_assessment(corruption):
    conversation, checklist, record = export_fixture()
    record = deepcopy(record)
    if corruption == "projection":
        record["evaluation"]["judgments"][0]["explanation"] = "A replacement not in the native record."
    elif corruption == "missing_native":
        record.pop("assessment")
    else:
        record["assessment"]["contract_version"] = "unknown-contract"
    with pytest.raises(ValueError, match="native assessment"):
        result_for(conversation, conversation, checklist, record)


def test_v3_selected_numeric_grade_survives_uncertainty_and_export():
    from cqa.scoring import calculate_score

    conversation, checklist, record = export_fixture(version=CONTRACT_VERSION)
    wire = record['assessment']['transport']
    wire['judgments']['consultation'].update(answer='15', factual_basis='unverified',
        factual_support_span_ids=[], missing_information='Applicable product policy is not confirmed.',
        explanation='Synthetic adapter fixture: the selected provisional rubric level is15.')
    parsed = validate_native(wire, conversation, checklist)
    record.update(assessment=parsed.native, evaluation=parsed.evaluation.model_dump())
    score = calculate_score(parsed.evaluation, checklist)
    assert score['total'] == 92.31 and score['provisional']
    assert score['review_recommended_criteria'] == ['consultation']
    assert score['unresolved_criteria'] == []
    assert score['score_bounds']['lower'] == 69.23
    row = result_for(conversation, conversation, checklist, record)
    assert row['status'] == 'ok' and row['score']['final_score'] == 92.31
    item = next(c for c in row['criteria'] if c['criterion_id'] == 'consultation')
    assert item['value'] == 15 and 'Missing information' in item['rationale']


def test_v3_snapshot_assumption_is_disclosed_with_numeric_submission():
    conversation, checklist, record = export_fixture(
        conditional=True, uses_reference=True, version=CONTRACT_VERSION)
    row = result_for(conversation, conversation, checklist, record)
    assert row['status'] == 'ok' and row['score']['final_score'] == 100
    item = next(c for c in row['criteria'] if c['criterion_id'] == 'consultation')
    assert 'Policy assumption:' in item['rationale']
    assert 'historical applicability is not independently confirmed' in item['rationale']

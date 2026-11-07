import json

import pytest

from cqa.grounding import attach_reference_pack, reference_applicable, reference_rejection_reasons
from cqa.models import Conversation, Message, Reference
from cqa.prompt import payload_for
from cqa.rubric import load_checklist


def source(*, stamps=None, occurred_on=None, scope="fictional-platform", language="EN"):
    return Conversation(id="arbitrary-source", channel="voice call", language=language,
        occurred_on=occurred_on, knowledge_scope=scope,
        messages=[Message(id=f"turn-{i}", timestamp=stamp, speaker="client" if i == 1 else "operator",
                          text="Source utterance") for i, stamp in enumerate(
                              stamps or ["2026-11-03T13:10:00.1234567+00:00", "2026-11-03T13:10:05Z"], 1)],
        references=[Reference(id="guide", text="Fictional instruction", provenance="Explicit test document",
                              scope="fictional-platform", valid_from="2026-11-03", valid_until="2026-11-03")])


def payload(conversation):
    return json.loads(payload_for(conversation, load_checklist(), grounded=True))


def test_new_payload_can_use_source_derived_date_without_rewriting_frozen_input():
    conversation = source()
    original = conversation.model_dump()
    ref = conversation.references[0]
    assert reference_applicable(ref, conversation) is False
    assert reference_rejection_reasons(ref, conversation) == ["missing_occurrence_date"]
    assert reference_applicable(ref, conversation, derive_dates=True) is True
    data = payload(conversation)
    assert data["usable_reference_ids"] == ["guide"]
    assert data["evidence_context"]["temporal"]["occurred_on"] == "2026-11-03"
    assert data["evidence_context"]["temporal"]["origin"] == "iso_timestamp_consensus"
    assert data["evidence_context"]["references"] == [{"reference_id": "guide", "usable": True,
                                                       "rejection_reasons": []}]
    assert data["conversation"]["occurred_on"] is None
    assert conversation.model_dump() == original
    # Full source timestamps remain in the original messages, not duplicated in context.
    assert data["conversation"]["messages"][0]["timestamp"] == original["messages"][0]["timestamp"]
    assert "source_timestamps" not in data["evidence_context"]["temporal"]


@pytest.mark.parametrize("scope,first,last,reason", [
    ("other-platform", "2026-11-03", "2026-11-03", "scope_mismatch"),
    (None, "2026-11-03", "2026-11-03", "missing_scope"),
    ("fictional-platform", "2026-11-04", "2026-11-10", "before_validity_window"),
    ("fictional-platform", "2026-10-01", "2026-11-02", "after_validity_window"),
])
def test_derived_dates_do_not_relax_scope_or_validity_checks(scope, first, last, reason):
    conversation = source(scope=scope, language="KZ")
    conversation.references[0].valid_from, conversation.references[0].valid_until = first, last
    assert not reference_applicable(conversation.references[0], conversation, derive_dates=True)
    data = payload(conversation)
    assert data["usable_reference_ids"] == []
    assert reason in data["evidence_context"]["references"][0]["rejection_reasons"]


def test_explicit_date_conflict_is_exposed_and_blocks_new_dated_reference_use():
    conversation = source(stamps=["2026-11-04T13:10:00Z"], occurred_on="2026-11-03")
    ref = conversation.references[0]
    # Frozen historical reference validation stays explicit-context only.
    assert reference_applicable(ref, conversation)
    assert not reference_applicable(ref, conversation, derive_dates=True)
    data = payload(conversation)
    assert data["evidence_context"]["temporal"]["occurred_on"] == "2026-11-03"
    assert data["evidence_context"]["temporal"]["has_conflict"]
    assert "source_date_conflict" in data["evidence_context"]["references"][0]["rejection_reasons"]
    assert data["usable_reference_ids"] == []


def test_relative_chat_time_is_not_imputed_from_language_or_today():
    conversation = source(stamps=["00:02", "00:03"], scope=None, language="RU")
    conversation.channel = "agent chat"
    data = payload(conversation)
    assert data["evidence_context"]["temporal"]["occurred_on"] is None
    assert data["evidence_context"]["temporal"]["origin"] == "unavailable"
    assert data["conversation"]["knowledge_scope"] is None
    assert set(data["evidence_context"]["references"][0]["rejection_reasons"]) == {
        "missing_scope", "missing_occurrence_date"}
    assert data["usable_reference_ids"] == []


def test_retrieval_date_is_not_an_invented_policy_window():
    conversation = source(stamps=["00:02", "00:03"])
    ref = conversation.references[0]
    ref.valid_from, ref.valid_until, ref.retrieved_on = None, None, "2026-11-07"
    data = payload(conversation)
    assert data["evidence_context"]["temporal"]["occurred_on"] is None
    assert data["usable_reference_ids"] == ["guide"]
    assert data["conversation"]["references"][0]["valid_from"] is None
    assert data["conversation"]["references"][0]["valid_until"] is None


def test_new_rule_authority_is_explicitly_separate_from_product_truth():
    data = payload(source())
    assert data["checklist"]["criteria"]
    assert data["evidence_context"]["rule_authority"] == (
        "The selected checklist defines grading requirements, not external product/account truth.")
    legacy = json.loads(payload_for(source(), load_checklist(), grounded=False))
    assert "evidence_context" not in legacy and "usable_reference_ids" not in legacy


def test_explicit_pack_attachment_cannot_override_conflicting_source_date(tmp_path):
    conversation = source(scope=None)
    conversation.references = []
    pack = {"scope": "fictional-platform", "references": [
        Reference(id="guide", text="Fictional instruction", provenance="Test", scope="fictional-platform",
                  valid_from="2026-11-07", valid_until="2026-11-07").model_dump()]}
    path = tmp_path / "pack.json"
    path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(ValueError, match="conflicts with original source timestamps"):
        attach_reference_pack(conversation, path, "fictional-platform", "2026-11-07")
    assert conversation.occurred_on is None and conversation.knowledge_scope is None
    assert conversation.references == []

import json

import pytest

from backend.importing import parse_import
from cqa.context import derive_temporal_context, with_source_date
from cqa.datasets import load_cases, organizer_cases
from cqa.models import Conversation, Message
from cqa.settings import ROOT


def conversation(stamps, *, occurred_on=None, origin=None, language="EN"):
    return Conversation(id="arbitrary-source-id", channel="voice call", language=language,
        occurred_on=occurred_on, occurred_on_origin=origin,
        messages=[Message(id=f"turn-{i}", timestamp=stamp,
                          speaker="client" if i == 1 else "operator", text="Source utterance")
                  for i, stamp in enumerate(stamps, 1)])


def test_fresh_iso_consensus_copies_date_and_preserves_offset_provenance():
    stamps = ["2026-11-03T13:10:00.6388245+00:00", "2026-11-03T18:10:05.1111111+05:00"]
    original = conversation(stamps)
    before = original.model_dump()
    context = derive_temporal_context(original)
    assert context["occurred_on"] == "2026-11-03"
    assert context["origin"] == "iso_timestamp_consensus" and not context["has_conflict"]
    assert context["source_message_ids"] == ["turn-1", "turn-2"]
    assert context["source_timestamps"] == stamps
    assert context["source_offsets"] == ["+00:00", "+05:00"]
    copied = with_source_date(original)
    assert copied is not original and original.model_dump() == before
    assert copied.occurred_on == "2026-11-03"
    assert copied.occurred_on_origin == "source_iso_timestamps"
    assert derive_temporal_context(copied)["origin"] == "iso_timestamp_consensus"
    assert copied.messages == original.messages and copied.knowledge_scope is None


@pytest.mark.parametrize("stamps", [
    ["00:02", "00:03"], ["2026-11-03", "2026-11-03"],
    ["2026-11-03T13:10:00", "2026-11-03T13:10:03"],
    ["2026-11-03T13:10:00+00:00", "00:03"],
    ["2026-02-30T13:10:00+00:00"], ["20261103T131000Z"],
    ["2026-W45-2T13:10:00Z"], ["", ""],
])
def test_relative_partial_naive_or_invalid_timestamps_do_not_invent_a_date(stamps):
    original = conversation(stamps, language="KZ")
    context = derive_temporal_context(original)
    assert context["occurred_on"] is None and context["origin"] == "unavailable"
    assert not context["has_conflict"]
    assert with_source_date(original).occurred_on is None


def test_mixed_empty_timestamps_prevent_automatic_whole_conversation_derivation():
    original = conversation(["", "2026-11-03T13:10:00Z"])
    context = derive_temporal_context(original)
    assert context["occurred_on"] is None and context["origin"] == "unavailable"
    assert context["source_message_ids"] == ["turn-2"]
    assert context["unusable_timestamps"] == [{"message_id": "turn-1", "timestamp": ""}]
    assert with_source_date(original) is original


def test_explicit_date_remains_supplied_with_missing_source_timestamps():
    original = conversation(["", "2026-11-03T13:10:00Z"], occurred_on="2026-11-03")
    context = derive_temporal_context(original)
    assert context["occurred_on"] == "2026-11-03" and context["origin"] == "explicit"
    assert not context["has_conflict"]
    assert with_source_date(original) is original


@pytest.mark.parametrize("stamps", [
    ["2026-11-03T23:59:59Z", "2026-11-04T00:00:01Z"],
    ["2026-11-03T00:10:00+05:00", "2026-11-02T19:10:00Z"],
])
def test_midnight_or_offset_date_conflicts_are_not_silently_normalized(stamps):
    original = conversation(stamps)
    context = derive_temporal_context(original)
    assert context["origin"] == "conflict" and context["has_conflict"]
    assert context["occurred_on"] is None
    assert len(context["source_date_candidates"]) == 2
    assert with_source_date(original) is original


def test_explicit_date_is_preserved_but_conflict_is_exposed():
    original = conversation(["2026-11-04T13:10:00Z"], occurred_on="2026-11-03")
    context = derive_temporal_context(original)
    assert context["occurred_on"] == "2026-11-03" and context["origin"] == "explicit"
    assert context["has_conflict"] and context["conflict_reason"]
    assert with_source_date(original) is original


def test_explicit_date_needs_no_guessed_absolute_time_from_relative_chat():
    original = conversation(["00:02", "00:03"], occurred_on="2026-11-03", origin="supplied")
    context = derive_temporal_context(original)
    assert context["origin"] == "explicit" and not context["has_conflict"]
    assert context["occurred_on"] == "2026-11-03"


@pytest.mark.parametrize("stamps,date", [
    (["00:02"], "2026-11-03"),
    (["2026-11-04T13:10:00Z"], "2026-11-03"),
    (["2026-11-03T13:10:00Z", "00:03"], "2026-11-03"),
])
def test_forged_or_unsupported_derived_provenance_is_a_conflict(stamps, date):
    context = derive_temporal_context(conversation(stamps, occurred_on=date, origin="source_iso_timestamps"))
    assert context["has_conflict"] and context["conflict_reason"]
    assert context["origin"] == "conflict"


def test_browser_import_preserves_original_evidence_context_and_recording_metadata():
    raw = conversation(["2026-11-03T13:10:00Z", "2026-11-03T13:10:04Z"]).model_dump()
    raw["recording_url"] = "https://example.org/player"
    raw["expected_score"] = "NEVER_IN_INFERENCE"
    imported, metadata = parse_import(json.dumps(raw))[0]
    assert imported.occurred_on == "2026-11-03"
    assert imported.occurred_on_origin == "source_iso_timestamps"
    assert metadata["recording_url"] == "https://example.org/player"
    assert metadata["temporal_context"]["origin"] == "iso_timestamp_consensus"
    assert metadata["temporal_context"]["source_timestamps"] == [m["timestamp"] for m in raw["messages"]]
    assert "NEVER_IN_INFERENCE" not in imported.model_dump_json()


def test_historical_conversation_parsing_and_case_file_loading_remain_inert(tmp_path):
    raw = conversation(["2026-11-03T13:10:00Z"]).model_dump()
    assert Conversation.model_validate(raw).occurred_on is None
    record = {"id": "unchanged", "family": "source", "source": "authored", "label_provenance": "unlabelled",
              "tags": [], "conversation": raw, "expectations": [], "checklist_override": None}
    path = tmp_path / "frozen.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    assert load_cases(path)[0].conversation.occurred_on is None


@pytest.mark.skipif(not (ROOT / "data/private/dev.json").exists(), reason="Private organizer data is not in checkout")
def test_fresh_organizer_import_derives_all_five_call_dates_and_no_chat_dates():
    data = (ROOT / "data/private/dev.json").read_text(encoding="utf-8")
    imported = [c for c, _ in parse_import(data)]
    dataset = [c.conversation for c in organizer_cases()]
    for conversations in [imported, dataset]:
        calls = [c for c in conversations if c.channel == "voice call"]
        chats = [c for c in conversations if c.channel == "agent chat"]
        assert len(calls) == 5 and len(chats) == 60
        assert all(c.occurred_on == "2026-11-03" and c.occurred_on_origin == "source_iso_timestamps" for c in calls)
        assert all(c.occurred_on is None and c.knowledge_scope is None for c in chats)

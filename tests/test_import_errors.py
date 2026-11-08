"""Import guidance is field-specific without echoing uploaded customer data."""

import copy
import json

import pytest

from backend.importing import parse_import

PRIVATE = "PRIVATE-CUSTOMER-DATA"
CONVERSATION = {"id": PRIVATE, "channel": "agent chat", "language": "EN", "messages": [
    {"id": "m1", "timestamp": "00:01", "speaker": "client", "text": PRIVATE},
    {"id": "m2", "timestamp": "00:02", "speaker": "operator", "text": "Please open your profile."},
]}


def error_for(value):
    with pytest.raises(ValueError) as failure:
        parse_import(json.dumps(value))
    message = str(failure.value)
    assert PRIVATE not in message
    return message


@pytest.mark.parametrize(("field", "value", "guidance"), [
    ("speaker", PRIVATE, 'use "client", "operator", "bot", or "system"'),
    ("timestamp", 123, 'use a text timestamp, for example "00:01" or an ISO date-time'),
    ("text", {PRIVATE: PRIVATE}, "use text for the message or reference"),
    ("text", "  ", "use nonempty text"),
    ("id", "  ", "use nonempty text"),
])
def test_canonical_message_error_identifies_record_and_message(field, value, guidance):
    invalid = copy.deepcopy(CONVERSATION)
    invalid["messages"][1][field] = value
    message = error_for([CONVERSATION, invalid])
    assert message == f"Record 2, messages[2].{field}: {guidance}"


def test_missing_message_field_and_bad_channel_give_allowed_format():
    invalid = copy.deepcopy(CONVERSATION)
    del invalid["messages"][0]["timestamp"]
    assert "Record 1, messages[1].timestamp: required; use a text timestamp" in error_for(invalid)
    invalid = CONVERSATION | {"channel": PRIVATE}
    assert error_for(invalid) == 'Record 1, channel: use "agent chat" or "voice call"'


def test_organizer_errors_use_uploaded_field_names():
    record = {"conversation_id": PRIVATE, "channel": "voice call", "language": "EN",
              "transcript": copy.deepcopy(CONVERSATION["messages"])}
    del record["transcript"][1]["speaker"]
    message = error_for({"data": {"records": [CONVERSATION, record]}})
    assert message == 'Record 2, transcript[2].speaker: required; use "client", "operator", "bot", or "system"'
    del record["conversation_id"]
    assert error_for(record) == "Record 1, conversation_id: required; use a text identifier"


@pytest.mark.parametrize(("payload", "expected"), [
    ([CONVERSATION, PRIVATE], "Record 2, record: expected a conversation object"),
    ({"conversation": PRIVATE}, "Record 1, conversation: expected an object with conversation fields"),
    (CONVERSATION | {"messages": PRIVATE}, "Record 1, messages: use an array of message objects"),
    (CONVERSATION | {"messages": []}, "Record 1, messages: include at least one message"),
    ({"transcript": [PRIVATE]}, "Record 1, transcript[1]: expected a message object"),
])
def test_invalid_structure_is_actionable(payload, expected):
    assert error_for(payload) == expected


def test_duplicate_id_names_second_message_without_echoing_id():
    invalid = copy.deepcopy(CONVERSATION)
    invalid["messages"][0]["id"] = invalid["messages"][1]["id"] = PRIVATE
    assert error_for(invalid) == "Record 1, messages[2].id: use a unique ID within this conversation"


def test_unknown_property_name_and_date_validation_do_not_echo_data():
    invalid = copy.deepcopy(CONVERSATION)
    invalid["messages"][0][PRIVATE] = PRIVATE
    assert "messages[1].unrecognized field: remove this extra property" in error_for(invalid)
    assert error_for(CONVERSATION | {"occurred_on": PRIVATE}) == "Record 1, occurred_on: use a valid calendar date in YYYY-MM-DD format"
    invalid = CONVERSATION | {"references": [{"id": "ref", "text": PRIVATE, "provenance": "Example",
                                              "valid_from": PRIVATE}]}
    assert "Record 1, references[1]: use valid YYYY-MM-DD dates" in error_for(invalid)


def test_invalid_jsonl_reports_physical_line_without_echoing_content():
    content = json.dumps(CONVERSATION) + '\n\n{"text": "' + PRIVATE + '"'
    with pytest.raises(ValueError) as failure:
        parse_import(content)
    message = str(failure.value)
    assert "JSONL line 3, column" in message
    assert "check quotes, commas and brackets" in message
    assert PRIVATE not in message


def test_invalid_json_reports_location_without_echoing_content():
    with pytest.raises(ValueError, match="JSON line 2, column") as failure:
        parse_import('{\n"' + PRIVATE + '": }')
    assert PRIVATE not in str(failure.value)


@pytest.mark.parametrize("shape", ["canonical", "array", "records", "organizer", "diagnostic", "jsonl"])
def test_supported_import_shapes_and_source_metadata_still_work(shape):
    if shape == "organizer":
        record = {"conversation_id": PRIVATE, "channel": "agent chat", "language": "EN",
                  "transcript": [{k: v for k, v in m.items() if k != "id"} for m in CONVERSATION["messages"]],
                  "audio_url": "https://example.org/recording"}
        content = json.dumps({"data": {"records": [record]}})
    elif shape == "jsonl":
        content = json.dumps(CONVERSATION) + "\n\n" + json.dumps(CONVERSATION)
    else:
        payload = {"canonical": CONVERSATION, "array": [CONVERSATION], "records": {"records": [CONVERSATION]},
                   "diagnostic": {"conversation": CONVERSATION, "expectations": {"private_label": PRIVATE}}}[shape]
        content = json.dumps(payload)
    results = parse_import("\ufeff" + content)
    assert len(results) == (2 if shape == "jsonl" else 1)
    for conversation, metadata in results:
        assert conversation.model_dump(exclude_defaults=True) == CONVERSATION
        assert "expectations" not in conversation.model_dump()
        if shape == "organizer":
            assert metadata["recording_url"] == "https://example.org/recording"

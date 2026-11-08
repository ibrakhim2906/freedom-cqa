import json

from pydantic import ValidationError

from cqa.context import derive_temporal_context, with_source_date
from cqa.models import Conversation, Message, Reference, ReferenceContext


class _ImportIssue(ValueError):
    """A field-specific explanation containing only fixed text and row numbers."""


def validate_source_envelope(payload):
    """A failed supported response envelope cannot supply trusted source records."""
    if not isinstance(payload, dict):
        return
    envelope = payload.get("data")
    outer_failed = ("data" in payload or "records" in payload) and payload.get("isSuccess") is False
    inner_failed = isinstance(envelope, dict) and envelope.get("isSuccess") is False
    if outer_failed or inner_failed:
        raise ValueError("Organizer response reports failure; no source records were accepted")


def _validation_issue(error, values, organizer):
    issue = error.errors(include_input=False, include_context=False, include_url=False)[0]
    location = issue["loc"]
    known_fields = set(Conversation.model_fields) | set(Message.model_fields) | set(Reference.model_fields) | set(ReferenceContext.model_fields)
    parts = []
    for part in location:
        if isinstance(part, int):
            parts[-1] += f"[{part + 1}]"
        elif part in known_fields:
            parts.append("transcript" if organizer and part == "messages" else "conversation_id" if organizer and not parts and part == "id" else part)
        else:
            # Unknown property names can themselves contain personal information.
            parts.append("unrecognized field")
    field = ".".join(parts)
    last = location[-1] if location else None
    expected = {
        "channel": 'use "agent chat" or "voice call"',
        "speaker": 'use "client", "operator", "bot", or "system"',
        "timestamp": 'use a text timestamp, for example "00:01" or an ISO date-time',
        "language": 'use text for the language, for example "EN", "RU", or "KZ"',
        "id": "use a text identifier",
        "text": "use text for the message or reference",
        "messages": "use an array of message objects",
        "references": "use an array of reference objects",
        "occurred_on_origin": 'use "supplied" or "source_iso_timestamps"',
        "date_basis": 'use "policy_validity" or "snapshot"',
        "mode": 'use "conversation_date" or "snapshot_review"',
        "pack_sha256": "use a 64-character lowercase hexadecimal hash",
    }
    if issue["type"] == "missing":
        detail = "required; " + expected.get(last, "provide this field")
    elif issue["type"] == "extra_forbidden":
        detail = "remove this extra property; use only the fields in the example dataset"
    elif last in expected:
        detail = expected[last]
    elif issue["type"] == "string_type":
        detail = "expected text"
    elif issue["type"] == "list_type":
        detail = "expected an array"
    elif issue["type"] in {"model_type", "model_attributes_type", "dict_type"}:
        detail = "expected an object with the required fields"
    elif issue["type"] == "value_error":
        # Model validators may include the invalid value in their message.
        # Derive guidance from the model structure, never validation text.
        if not location:
            message_field = "transcript" if organizer else "messages"
            if not values.get("messages"):
                return f"{message_field}: include at least one message"
            for collection, label in (("messages", message_field), ("references", "references")):
                seen = set()
                for index, item in enumerate(values.get(collection, []), 1):
                    if item["id"] in seen:
                        return f"{label}[{index}].id: use a unique ID within this conversation"
                    seen.add(item["id"])
            return "occurred_on: use a valid calendar date in YYYY-MM-DD format"
        if location[0] == "references":
            detail = "use valid YYYY-MM-DD dates; validity must start before it ends; snapshot references need snapshot_on and no validity interval"
        elif location[0] == "reference_context":
            detail = "provide scope, rationale and pack_id; snapshot_review needs a YYYY-MM-DD as_of date, while conversation_date must not set as_of"
        else:
            detail = "check this field against the example dataset"
    else:
        detail = "check this field against the example dataset"
    return f"{field or 'record'}: {detail}"


def parse_import(content):
    try:
        payload = json.loads(content.lstrip("\ufeff"))
    except json.JSONDecodeError as json_error:
        payload = []
        for line_number, line in enumerate(content.lstrip("\ufeff").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload.append(json.loads(line))
            except json.JSONDecodeError as line_error:
                position = f"JSONL line {line_number}, column {line_error.colno}" if payload else f"JSON line {json_error.lineno}, column {json_error.colno}"
                raise ValueError(f"{position}: invalid syntax. Use valid JSON, or one complete JSON object per JSONL line; check quotes, commas and brackets.") from None
    validate_source_envelope(payload)
    if isinstance(payload, dict) and "data" in payload:
        if not isinstance(payload["data"], dict):
            raise ValueError("data: expected an object containing records (an array of conversations)")
        payload = payload["data"].get("records", [])
    elif isinstance(payload, dict) and "records" in payload:
        payload = payload["records"]
    rows = payload if isinstance(payload, list) else [payload]
    if not rows or len(rows) > 1000:
        raise ValueError("Import between 1 and 1000 conversations")
    result = []
    for index, source in enumerate(rows, 1):
        try:
            if not isinstance(source, dict):
                raise _ImportIssue("record: expected a conversation object")
            # Diagnostic labels, expected answers and organizer metadata never enter inference.
            row = source.get("conversation", source)
            if not isinstance(row, dict):
                raise _ImportIssue("conversation: expected an object with conversation fields")
            organizer = "transcript" in row
            if organizer:
                if not isinstance(row["transcript"], list):
                    raise _ImportIssue("transcript: expected an array of message objects")
                messages = []
                for message_index, message in enumerate(row["transcript"], 1):
                    if not isinstance(message, dict):
                        raise _ImportIssue(f"transcript[{message_index}]: expected a message object")
                    messages.append({k: v for k, v in message.items() if k in Message.model_fields} | {"id": message.get("id", f"m{message_index}")})
                values = {k: v for k, v in row.items() if k in Conversation.model_fields and k not in {"id", "messages"}}
                values["messages"] = messages
                if "conversation_id" in row:
                    values["id"] = row["conversation_id"]
            else:
                values = {k: v for k, v in row.items() if k in Conversation.model_fields}
            conversation = Conversation.model_validate(values)
            if len(conversation.messages) > 10_000:
                raise _ImportIssue(f"{'transcript' if organizer else 'messages'}: use at most 10000 messages per conversation")
            if not conversation.id.strip():
                raise _ImportIssue(f"{'conversation_id' if organizer else 'id'}: use a nonempty text identifier")
            for message_index, message in enumerate(conversation.messages, 1):
                for field in ("id", "text"):
                    if not getattr(message, field).strip():
                        raise _ImportIssue(f"{'transcript' if organizer else 'messages'}[{message_index}].{field}: use nonempty text")
            temporal_context = derive_temporal_context(conversation)
            conversation = with_source_date(conversation)
            recording = row.get("audio_url") or row.get("recording_url") or row.get("audio_link")
            if recording and not isinstance(recording, str):
                recording = None
            extra = {"recording_url": recording} if recording and recording.startswith(("https://", "http://")) else {}
            extra["temporal_context"] = temporal_context
            result.append((conversation, extra))
        except _ImportIssue as error:
            raise ValueError(f"Record {index}, {error}") from None
        except ValidationError as error:
            raise ValueError(f"Record {index}, {_validation_issue(error, values, organizer)}") from None
        except (ValueError, KeyError, TypeError):
            raise ValueError(f"Record {index}: check the conversation fields against the example dataset") from None
    return result

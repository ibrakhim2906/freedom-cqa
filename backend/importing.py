import json

from cqa.context import derive_temporal_context, with_source_date
from cqa.models import Conversation, Message


def parse_import(content):
    try:
        payload = json.loads(content.lstrip("\ufeff"))
    except json.JSONDecodeError:
        try:
            payload = [json.loads(line) for line in content.lstrip("\ufeff").splitlines() if line.strip()]
        except json.JSONDecodeError as error:
            raise ValueError("Import valid JSON or one complete JSON object per JSONL line") from error
    if isinstance(payload, dict) and "data" in payload:
        if not isinstance(payload["data"], dict):
            raise ValueError("Organizer data must contain an object with records")
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
                raise TypeError("Record must be an object")
            # Diagnostic labels, expected answers and organizer metadata never enter inference.
            row = source.get("conversation", source)
            if not isinstance(row, dict):
                raise TypeError("Conversation must be an object")
            if "transcript" in row:
                if not isinstance(row["transcript"], list) or any(not isinstance(m, dict) for m in row["transcript"]):
                    raise TypeError("Transcript must contain message objects")
                conversation = Conversation(id=row["conversation_id"], channel=row["channel"], language=row["language"],
                    messages=[Message(id=m.get("id", f"m{i}"), timestamp=m["timestamp"], speaker=m["speaker"], text=m["text"])
                              for i, m in enumerate(row["transcript"], 1)],
                    references=row.get("references", []), knowledge_scope=row.get("knowledge_scope"),
                    occurred_on=row.get("occurred_on"), occurred_on_origin=row.get("occurred_on_origin"))
            else:
                conversation = Conversation.model_validate({k: v for k, v in row.items() if k in Conversation.model_fields})
            if len(conversation.messages) > 10_000 or not conversation.id.strip():
                raise ValueError("Conversation requires an ID and at most 10000 messages")
            for message in conversation.messages:
                if not message.id.strip() or not message.text.strip():
                    raise ValueError("Message IDs and text must be nonempty")
            temporal_context = derive_temporal_context(conversation)
            conversation = with_source_date(conversation)
            recording = row.get("audio_url") or row.get("recording_url") or row.get("audio_link")
            if recording and not isinstance(recording, str):
                recording = None
            extra = {"recording_url": recording} if recording and recording.startswith(("https://", "http://")) else {}
            extra["temporal_context"] = temporal_context
            result.append((conversation, extra))
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"Conversation {index} is invalid: check ID, channel, language, message roles and fields") from error
    return result

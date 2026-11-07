"""Derive temporal context from original source timestamps, without guessing.

Historical Conversation parsing stays inert. Call this module only at fresh
ingress or when preparing explicitly versioned evidence context for evaluation.
"""

import re
from datetime import datetime

from .models import Conversation

_OFFSET_ISO = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def derive_temporal_context(conversation: Conversation) -> dict:
    """Describe supplied/derivable dates while preserving offsets and conflicts.

    Consensus uses the calendar date written at each source offset, never today's
    date, the machine timezone, or a jurisdiction inferred from language. A date
    spanning midnight is conservatively ambiguous unless explicitly supplied.
    """
    valid, unusable = [], []
    for message in conversation.messages:
        stamp = message.timestamp.strip()
        if not stamp:
            unusable.append({"message_id": message.id, "timestamp": message.timestamp})
            continue
        parsed = None
        if _OFFSET_ISO.fullmatch(stamp):
            try:
                parsed = datetime.fromisoformat(stamp)
            except ValueError:
                pass
        if parsed is None or parsed.utcoffset() is None:
            unusable.append({"message_id": message.id, "timestamp": message.timestamp})
        else:
            valid.append({"message_id": message.id, "timestamp": message.timestamp,
                          "date": parsed.date().isoformat(), "offset": stamp[-6:] if not stamp.endswith("Z") else "Z"})
    dates = sorted({item["date"] for item in valid})
    supplied = conversation.occurred_on
    provenance = getattr(conversation, "occurred_on_origin", None)
    invalid_derivation = provenance == "source_iso_timestamps" and not (
        supplied and valid and not unusable and dates == [supplied]
    )
    has_conflict = len(dates) > 1 or bool(supplied and dates and dates != [supplied]) or invalid_derivation
    reason = ("timestamps_span_multiple_source_dates" if len(dates) > 1 else
              "explicit_date_conflicts_with_source_timestamps" if supplied and dates and dates != [supplied] else
              "derived_date_provenance_not_supported_by_source" if invalid_derivation else None)
    unavailable = ("no_nonempty_timestamps" if not any(m.timestamp.strip() for m in conversation.messages) else
                   "timestamps_not_all_offset_aware_iso8601" if unusable else None)
    if supplied:
        effective = supplied
        origin = "conflict" if invalid_derivation else "iso_timestamp_consensus" if provenance == "source_iso_timestamps" else "explicit"
    elif has_conflict:
        effective, origin = None, "conflict"
    elif valid and not unusable and len(dates) == 1:
        effective, origin = dates[0], "iso_timestamp_consensus"
    else:
        effective, origin = None, "unavailable"
    return {"occurred_on": effective, "origin": origin, "has_conflict": has_conflict,
            "conflict_reason": reason, "unavailable_reason": unavailable,
            "source_message_ids": [item["message_id"] for item in valid],
            "source_timestamps": [item["timestamp"] for item in valid],
            "source_date_candidates": dates, "source_offsets": sorted({item["offset"] for item in valid}),
            "unusable_timestamps": unusable,
            "timezone_basis": "calendar_date_at_each_original_source_offset; no timezone conversion"}


def with_source_date(conversation: Conversation) -> Conversation:
    """Copy a fresh input with a source-derived date only when consensus is safe."""
    context = derive_temporal_context(conversation)
    if conversation.occurred_on is not None or context["origin"] != "iso_timestamp_consensus" or context["has_conflict"]:
        return conversation
    updates = {"occurred_on": context["occurred_on"]}
    updates["occurred_on_origin"] = "source_iso_timestamps"
    return conversation.model_copy(update=updates)

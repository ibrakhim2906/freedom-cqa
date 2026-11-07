"""Single-copy model view of unchanged source text and selectable citation spans."""

import json
from copy import deepcopy

from .source_spans import VERSION


def project_sources(payload, conversation, checklist, catalog):
    catalog.assert_sources(conversation, checklist)
    projected = deepcopy(payload)
    full = {(s.kind, s.source_id, s.field): s for s in catalog.entries.values() if s.is_full}

    def alias(kind, source_id, field):
        return {"source_span_id": full[(kind, source_id, field)].span_id}

    for message in projected["conversation"]["messages"]:
        message["text"] = alias("dialogue", message["id"], "text")
    for reference in projected["conversation"]["references"]:
        reference["text"] = alias("reference", reference["id"], "text")
    for criterion in projected["checklist"]["criteria"]:
        cid = criterion["id"]
        criterion["instruction"] = alias("rule", cid, "instruction")
        for index, level in enumerate(criterion["levels"]):
            level["description"] = alias("rule", cid, f"levels[{index}].description")
        for channel in criterion["channel_guidance"]:
            field = "channel_guidance[" + json.dumps(channel, ensure_ascii=False) + "]"
            criterion["channel_guidance"][channel] = alias("rule", cid, field)

    sources = []
    for key, source in full.items():
        fragments = sorted((s for s in catalog.entries.values()
                            if not s.is_full and (s.kind, s.source_id, s.field) == key),
                           key=lambda s: (s.start, s.end))
        parts, position = [], 0
        for fragment in fragments:
            if fragment.start < position or fragment.end > len(source.quote):
                raise ValueError("Source view requires exact nonoverlapping catalog fragments")
            if fragment.start > position:
                parts.append({"span_id": None, "text": source.quote[position:fragment.start]})
            parts.append({"span_id": fragment.span_id, "text": fragment.quote})
            position = fragment.end
        if position < len(source.quote) or not parts:
            parts.append({"span_id": None, "text": source.quote[position:]})
        if "".join(p["text"] for p in parts) != source.quote:
            raise ValueError("Source projection must preserve every original source character")
        # Role, source identity, field and applicability remain at the original
        # source location containing this pointer; don't repeat them per block.
        sources.append({"span_id": source.span_id, "parts": parts})
    projected["source_span_catalog"] = {"version": VERSION, "view": "linked-parts-v1",
                                         "fingerprint": catalog.fingerprint, "sources": sources}
    return projected

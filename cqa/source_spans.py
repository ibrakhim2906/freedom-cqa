"""Immutable citation targets derived from saved sources, never from model prose.

Offsets are Python Unicode code-point offsets into unchanged source fields.
Selection establishes source identity and exact text, not semantic entailment,
reference applicability, factual truth or a score. Full-source targets are never
dropped to meet an optional fragment budget.
"""

import hashlib
import json
import re
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

VERSION = "source-spans-v1"
Kind = Literal["dialogue", "reference", "rule"]
ROLES = frozenset({"operator", "client", "system", "bot"})
KINDS = frozenset({"dialogue", "reference", "rule"})
_BOUNDARY = re.compile(r"[.!?;][\"'»”’\)\]]*(?=\s|$)|\r\n|\r|\n")


def _digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _binding(conversation, checklist):
    # Diagnostic conversation IDs are deliberately absent from inference. All
    # actual source identity, chronology and applicability context remain bound.
    saved = conversation.model_dump()
    saved.pop("id")
    return _digest({"version": VERSION, "conversation": saved, "checklist": checklist.model_dump()})


def _roles(values):
    if values is None:
        return None
    if isinstance(values, str):
        values = {values}
    result = frozenset(values)
    if not result <= ROLES:
        raise ValueError("Citation role filter contains an unknown source role")
    return result


@dataclass(frozen=True, slots=True)
class SourceSpan:
    span_id: str
    kind: Kind
    source_id: str
    field: str
    role: str | None
    start: int
    end: int
    quote: str
    is_full: bool

    @property
    def selectable(self):
        return bool(self.quote.strip())

    def payload(self):
        entry = {"span_id": self.span_id, "kind": self.kind, "source_id": self.source_id,
                 "field": self.field, "role": self.role, "start": self.start, "end": self.end,
                 "is_full": self.is_full}
        # Full text is already present in the original conversation/checklist.
        # Exact fragment text lets the model select a smaller span without doing
        # character-offset arithmetic or retyping that text in its response.
        if not self.is_full:
            entry["text"] = self.quote
        return entry


@dataclass(frozen=True, slots=True)
class SourceCatalog:
    entries: Mapping[str, SourceSpan]
    fingerprint: str
    source_fingerprint: str
    full_source_count: int
    requested_max_spans: int

    def __post_init__(self):
        object.__setattr__(self, "entries", MappingProxyType(dict(self.entries)))

    @property
    def over_budget(self):
        return len(self.entries) > self.requested_max_spans

    def ids(self, kind=None, *, roles=None, criterion_id=None):
        if kind is not None and kind not in KINDS:
            raise ValueError("Unknown citation source kind")
        permitted_roles = _roles(roles)
        if kind not in {None, "dialogue"} and permitted_roles is not None:
            raise ValueError("Role restrictions apply only to dialogue citations")
        if kind not in {None, "rule"} and criterion_id is not None:
            raise ValueError("Criterion restrictions apply only to rule citations")
        return [span.span_id for span in self.entries.values()
                if span.selectable and (kind is None or span.kind == kind)
                and (permitted_roles is None or span.role in permitted_roles)
                and (criterion_id is None or span.kind == "rule" and span.source_id == criterion_id)]

    def payload(self):
        return {"version": VERSION, "fingerprint": self.fingerprint,
                "spans": [span.payload() for span in self.entries.values()]}

    def assert_sources(self, conversation, checklist):
        if _binding(conversation, checklist) != self.source_fingerprint:
            raise ValueError("Source-span catalog does not match the saved source/checklist context")

    def resolve(self, span_id, *, kind, roles=None, criterion_id=None):
        if kind not in KINDS:
            raise ValueError("Unknown citation source kind")
        permitted_roles = _roles(roles)
        if kind != "dialogue" and permitted_roles is not None:
            raise ValueError("Role restrictions apply only to dialogue citations")
        if kind != "rule" and criterion_id is not None:
            raise ValueError("Criterion restrictions apply only to rule citations")
        span = self.entries.get(span_id) if isinstance(span_id, str) else None
        if span is None:
            raise ValueError("Citation selects an unknown source-span ID")
        if not span.selectable:
            raise ValueError("Blank source spans cannot be used as citation evidence")
        if span.kind != kind:
            raise ValueError("Citation selects the wrong source kind")
        if permitted_roles is not None and span.role not in permitted_roles:
            raise ValueError("Citation selects the wrong source role")
        if criterion_id is not None and span.source_id != criterion_id:
            raise ValueError("Rule citation belongs to another criterion")
        key = {"dialogue": "message_id", "reference": "reference_id", "rule": "criterion_id"}[kind]
        return {key: span.source_id, "quote": span.quote}


def _fragments(text):
    """Mechanical ranges only; this deliberately makes no clause/truth decision."""
    start = 0
    for boundary in _BOUNDARY.finditer(text):
        end = boundary.end()
        if text[start:end].strip() and (start, end) != (0, len(text)):
            yield start, end
        start = end
    if start < len(text) and text[start:].strip() and start != 0:
        yield start, len(text)


def build_catalog(conversation, checklist, *, max_spans=500):
    if type(max_spans) is not int or max_spans < 1:
        raise ValueError("Source-span budget must be a positive integer")
    sources = []
    counters = dict.fromkeys(["d_o", "d_c", "d_s", "d_b", "p", "r"], 0)

    def source(kind, source_id, field, role, text):
        prefix = "d_" + role[0] if kind == "dialogue" else "p" if kind == "reference" else "r"
        span_id = f"{prefix}_{counters[prefix]}"
        counters[prefix] += 1
        sources.append((span_id, kind, source_id, field, role, text))

    for message in conversation.messages:
        source("dialogue", message.id, "text", message.speaker, message.text)
    for reference in conversation.references:
        source("reference", reference.id, "text", None, reference.text)
    for criterion in checklist.criteria:
        source("rule", criterion.id, "instruction", None, criterion.instruction)
        for index, level in enumerate(criterion.levels):
            source("rule", criterion.id, f"levels[{index}].description", None, level.description)
        for channel in sorted(criterion.channel_guidance):
            field = "channel_guidance[" + json.dumps(channel, ensure_ascii=False) + "]"
            source("rule", criterion.id, field, None, criterion.channel_guidance[channel])

    entries = {}
    pending = deque()
    for span_id, kind, source_id, field, role, text in sources:
        entries[span_id] = SourceSpan(span_id, kind, source_id, field, role, 0, len(text), text, True)
        pending.append((span_id, kind, source_id, field, role, text, iter(enumerate(_fragments(text), 1))))
    full_count = len(entries)
    # Round-robin fragments avoid giving the whole optional budget to the first
    # message or long instruction. IDs do not depend on the selected budget.
    while pending and len(entries) < max_spans:
        span_id, kind, source_id, field, role, text, ranges = pending.popleft()
        try:
            index, (start, end) = next(ranges)
        except StopIteration:
            continue
        fragment_id = f"{span_id}_s{index}"
        entries[fragment_id] = SourceSpan(fragment_id, kind, source_id, field, role,
                                          start, end, text[start:end], False)
        pending.append((span_id, kind, source_id, field, role, text, ranges))
    binding = _binding(conversation, checklist)
    fingerprint = _digest({"version": VERSION, "sources": binding, "max_spans": max_spans,
        "entries": [{**span.payload(), "quote": span.quote} for span in entries.values()]})
    return SourceCatalog(entries, fingerprint, binding, full_count, max_spans)

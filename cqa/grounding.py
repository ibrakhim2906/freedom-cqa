"""Mechanical source/scope checks; semantic entailment remains the grader's task."""

import json
from pathlib import Path

from .context import derive_temporal_context
from .models import Conversation, Reference, validate_iso_date


def reference_rejection_reasons(reference: Reference, conversation: Conversation, *, derive_dates=False):
    reasons = []
    if reference.scope is not None and reference.scope != conversation.knowledge_scope:
        reasons.append("missing_scope" if conversation.knowledge_scope is None else "scope_mismatch")
    if reference.valid_from or reference.valid_until:
        context = derive_temporal_context(conversation) if derive_dates else None
        on = context["occurred_on"] if context else conversation.occurred_on
        if context and context["has_conflict"]:
            reasons.append("source_date_conflict")
        if on is None:
            reasons.append("missing_occurrence_date")
        else:
            if reference.valid_from and on < reference.valid_from:
                reasons.append("before_validity_window")
            if reference.valid_until and on > reference.valid_until:
                reasons.append("after_validity_window")
    return reasons


def reference_applicable(reference: Reference, conversation: Conversation, *, derive_dates=False):
    # Historical validation retains explicit-context behavior.
    return not reference_rejection_reasons(reference, conversation, derive_dates=derive_dates)


def attach_reference_pack(conversation: Conversation, path: Path, scope: str, occurred_on: str):
    """Explicit caller-selected scope/date; never infer entity or date from language."""
    validate_iso_date(occurred_on)
    pack = json.loads(path.read_text(encoding="utf-8"))
    if not scope or pack["scope"] != scope:
        raise ValueError("Selected reference scope must match the reference pack")
    if conversation.knowledge_scope not in {None, scope} or conversation.occurred_on not in {None, occurred_on}:
        raise ValueError("Reference selection cannot overwrite an existing conversation scope/date")
    refs = [Reference.model_validate(r) for r in pack["references"]]
    if any(r.scope != scope for r in refs):
        raise ValueError("Reference pack contains a differently scoped source")
    attached = Conversation.model_validate(conversation.model_dump() | {
        "knowledge_scope": scope, "occurred_on": occurred_on,
        "references": [r.model_dump() for r in conversation.references + refs]})
    if derive_temporal_context(attached)["has_conflict"]:
        raise ValueError("Reference date conflicts with original source timestamps")
    return attached

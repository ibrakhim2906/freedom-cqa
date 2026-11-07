"""Mechanical source/scope checks; semantic entailment remains the grader's task."""

import json
from pathlib import Path

from .models import Conversation, Reference, validate_iso_date


def reference_applicable(reference: Reference, conversation: Conversation):
    if reference.scope is not None and reference.scope != conversation.knowledge_scope:
        return False
    if reference.valid_from or reference.valid_until:
        if conversation.occurred_on is None:
            return False
        if reference.valid_from and conversation.occurred_on < reference.valid_from:
            return False
        if reference.valid_until and conversation.occurred_on > reference.valid_until:
            return False
    return True


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
    return Conversation.model_validate(conversation.model_dump() | {
        "knowledge_scope": scope, "occurred_on": occurred_on,
        "references": [r.model_dump() for r in conversation.references + refs]})

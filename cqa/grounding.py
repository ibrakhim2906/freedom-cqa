"""Mechanical source/scope checks; semantic entailment remains the grader's task."""

import hashlib
import json
from pathlib import Path

from .context import derive_temporal_context
from .models import Conversation, Reference, ReferenceContext, validate_iso_date


def reference_rejection_reasons(reference: Reference, conversation: Conversation, *, derive_dates=False):
    reasons = []
    selection = conversation.reference_context
    temporal = derive_temporal_context(conversation) if derive_dates or selection is not None else None
    on = temporal["occurred_on"] if temporal else conversation.occurred_on
    scope = (selection.scope if selection and selection.mode == "snapshot_review"
             else conversation.knowledge_scope)
    if selection and conversation.knowledge_scope not in {None, selection.scope}:
        reasons.append("reference_context_scope_mismatch")
    if selection and selection.mode == "conversation_date" and conversation.knowledge_scope != selection.scope:
        reasons.append("reference_context_scope_unconfirmed")
    if reference.scope is not None and reference.scope != scope:
        reasons.append("missing_scope" if scope is None else "scope_mismatch")
    dated = reference.valid_from or reference.valid_until or reference.date_basis == "snapshot"
    if temporal and temporal["has_conflict"] and (dated or selection is not None):
        reasons.append("source_date_conflict")
    if reference.date_basis == "snapshot":
        # An explicit snapshot review is a conditional assessment at that date,
        # not evidence that the historical conversation occurred then.
        review = selection is not None and selection.mode == "snapshot_review"
        assessment_date = selection.as_of if review else on
        if assessment_date is None:
            reasons.append("missing_assessment_date" if review else "missing_occurrence_date")
        elif assessment_date != reference.snapshot_on:
            reasons.append("snapshot_date_mismatch")
    elif reference.valid_from or reference.valid_until:
        # A snapshot-review date never extends a real policy validity window.
        if on is None:
            reasons.append("missing_occurrence_date")
        else:
            if reference.valid_from and on < reference.valid_from:
                reasons.append("before_validity_window")
            if reference.valid_until and on > reference.valid_until:
                reasons.append("after_validity_window")
    return reasons


def evidence_context_for(conversation: Conversation, *, derive_dates=True):
    """Shared preflight/payload/review description without changing source inputs."""
    temporal = derive_temporal_context(conversation)
    selection = conversation.reference_context
    conditional = selection is not None and selection.mode == "snapshot_review"
    assessment = {
        "mode": selection.mode if selection else "conversation_date",
        "conditional": conditional,
        "scope": selection.scope if conditional else conversation.knowledge_scope,
        "as_of": selection.as_of if conditional else temporal["occurred_on"],
        "rationale": selection.rationale if selection else None,
        "pack_id": selection.pack_id if selection else None,
        "pack_sha256": selection.pack_sha256 if selection else None,
    }
    return {
        "temporal": temporal,
        "assessment": assessment,
        "rule_authority": "The selected checklist defines grading requirements, not external product/account truth.",
        "references": [{"reference_id": r.id,
                        "usable": reference_applicable(r, conversation, derive_dates=derive_dates),
                        "rejection_reasons": reference_rejection_reasons(r, conversation, derive_dates=derive_dates)}
                       for r in conversation.references],
    }


def reference_applicable(reference: Reference, conversation: Conversation, *, derive_dates=False):
    # Historical validation retains explicit-context behavior when no new context
    # was selected. New selections consistently check original source conflicts.
    return not reference_rejection_reasons(reference, conversation, derive_dates=derive_dates)


def select_reference_context(conversation: Conversation, path: Path, scope: str, *,
                             mode="conversation_date", occurred_on=None, as_of=None,
                             rationale, pack_id=None, require_usable=True):
    """Freeze an explicit source selection in a new immutable input revision.

    Preview callers can request a candidate with unavailable references, but no
    scope/date is inferred from wording, language, hostname or the machine clock.
    """
    raw = path.read_bytes()
    pack = json.loads(raw)
    if not scope or pack["scope"] != scope:
        raise ValueError("Selected reference scope must match the reference pack")
    if conversation.knowledge_scope not in {None, scope}:
        raise ValueError("Reference selection cannot overwrite an existing conversation scope")
    temporal = derive_temporal_context(conversation)
    if temporal["has_conflict"]:
        raise ValueError("Reference context conflicts with original source timestamps")
    selection = ReferenceContext(mode=mode, scope=scope, as_of=as_of, rationale=rationale,
                                 pack_id=pack_id or path.stem,
                                 pack_sha256=hashlib.sha256(raw).hexdigest())
    updates = {"reference_context": selection.model_dump()}
    if mode == "snapshot_review":
        if occurred_on is not None:
            raise ValueError("Snapshot review cannot assign or replace the actual conversation date")
    else:
        if occurred_on is not None:
            validate_iso_date(occurred_on)
            if temporal["occurred_on"] not in {None, occurred_on}:
                raise ValueError("Reference selection cannot overwrite an existing conversation date")
            # Partial absolute timestamps still provide a contradiction check,
            # even when they do not support deriving a whole-conversation date.
            if any(day != occurred_on for day in temporal["source_date_candidates"]):
                raise ValueError("Reference date conflicts with original source timestamps")
            updates["occurred_on"] = occurred_on
            source_derived = (conversation.occurred_on is None and
                              temporal["origin"] == "iso_timestamp_consensus")
            updates["occurred_on_origin"] = (conversation.occurred_on_origin or
                                             ("source_iso_timestamps" if source_derived else "supplied"))
        elif conversation.occurred_on is None and temporal["origin"] == "iso_timestamp_consensus":
            updates["occurred_on"] = temporal["occurred_on"]
            updates["occurred_on_origin"] = "source_iso_timestamps"
        updates["knowledge_scope"] = scope

    refs = [Reference.model_validate(r) for r in pack["references"]]
    if not refs or any(r.scope != scope for r in refs):
        raise ValueError("Reference pack must contain sources in its declared scope")
    indexed = {r.id: r for r in conversation.references}
    for ref in refs:
        if ref.id in indexed and ref != indexed[ref.id]:
            raise ValueError("Reference ID already exists with different source content")
        indexed[ref.id] = ref
    updates["references"] = [r.model_dump() for r in indexed.values()]
    revised = Conversation.model_validate(conversation.model_dump() | updates)
    if derive_temporal_context(revised)["has_conflict"]:
        raise ValueError("Reference context conflicts with original source timestamps")
    if require_usable and not any(reference_applicable(r, revised, derive_dates=True) for r in refs):
        raise ValueError("No selected pack references are usable for this scope/date; preview explains the exclusions")
    return revised


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

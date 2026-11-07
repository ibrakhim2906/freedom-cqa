"""Generic snapshot integration contracts; no provider/client is instantiated."""

import hashlib
import json

import pytest

from cqa.grounding import (
    evidence_context_for,
    reference_applicable,
    reference_rejection_reasons,
    select_reference_context,
)
from cqa.models import Conversation, Message, Reference, ReferenceContext
from cqa.prompt import GROUNDED_VERSION, PROMPT_VERSION, fingerprint, payload_for
from cqa.rubric import load_checklist

SCOPE = "fictional-broker-platform"
SNAPSHOT = "2026-11-07"


def conversation(*, occurred_on=None, scope=None, timestamps=None):
    return Conversation(id="arbitrary-customer-conversation", channel="agent chat", language="EN",
                        occurred_on=occurred_on, knowledge_scope=scope,
                        messages=[Message(id=f"t{i}", timestamp=stamp,
                                          speaker="client" if i == 1 else "operator", text="Source text")
                                  for i, stamp in enumerate(timestamps or ["00:01", "00:02"], 1)])


def snapshot_reference(**updates):
    return Reference.model_validate({"id": "official-product-guide", "scope": SCOPE,
                                     "text": "Funds require an account transfer before use.",
                                     "provenance": "Fictional reviewed product source, not a score key.",
                                     "date_basis": "snapshot", "snapshot_on": SNAPSHOT, **updates})


def pack_file(tmp_path, refs=None):
    path = tmp_path / "fictional-product-pack.json"
    path.write_text(json.dumps({"scope": SCOPE, "references": [r.model_dump() for r in
                                                               (refs or [snapshot_reference()])]}),
                    encoding="utf-8")
    return path


def select(source, path, **kwargs):
    return select_reference_context(source, path, SCOPE,
                                    rationale="Reviewer confirmed the product and selected the disclosed basis.",
                                    **kwargs)


@pytest.mark.parametrize("updates", [
    {"snapshot_on": None}, {"snapshot_on": "20261107"},
    {"valid_from": SNAPSHOT}, {"valid_until": SNAPSHOT},
    {"date_basis": "policy_validity", "snapshot_on": SNAPSHOT},
])
def test_snapshot_dates_cannot_be_presented_as_legal_policy_intervals(updates):
    with pytest.raises(ValueError):
        snapshot_reference(**updates)


@pytest.mark.parametrize("scope,on,reason", [
    (None, SNAPSHOT, "missing_scope"), (SCOPE, None, "missing_occurrence_date"),
    ("different-broker", SNAPSHOT, "scope_mismatch"), (SCOPE, "2026-11-03", "snapshot_date_mismatch"),
])
def test_snapshot_source_requires_matching_actual_context_without_an_assumption(scope, on, reason):
    source = conversation(scope=scope, occurred_on=on)
    assert reason in reference_rejection_reasons(snapshot_reference(), source)
    assert not reference_applicable(snapshot_reference(), source)


def test_actual_context_freezes_pack_and_uses_a_known_date_without_mutating_original(tmp_path):
    path, source = pack_file(tmp_path), conversation(occurred_on=SNAPSHOT)
    before = source.model_dump()
    selected = select(source, path)
    assert source.model_dump() == before
    assert selected.knowledge_scope == SCOPE and selected.occurred_on == SNAPSHOT
    assert selected.reference_context.mode == "conversation_date" and selected.reference_context.as_of is None
    assert selected.reference_context.pack_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert reference_applicable(selected.references[0], selected)
    context = evidence_context_for(selected)
    assert not context["assessment"]["conditional"]
    assert context["assessment"]["as_of"] == SNAPSHOT
    assert context["references"] == [{"reference_id": "official-product-guide", "usable": True,
                                      "rejection_reasons": []}]


def test_actual_context_can_derive_only_a_consensus_absolute_source_date(tmp_path):
    original = conversation(timestamps=["2026-11-07T10:00:00Z", "2026-11-07T10:00:01Z"])
    selected = select(original, pack_file(tmp_path))
    assert selected.occurred_on == SNAPSHOT and selected.occurred_on_origin == "source_iso_timestamps"
    assert original.occurred_on is None


def test_confirming_a_safely_source_derived_date_preserves_its_origin(tmp_path):
    original = conversation(timestamps=["2026-11-07T10:00:00Z", "2026-11-07T10:00:01Z"])
    selected = select(original, pack_file(tmp_path), occurred_on=SNAPSHOT)
    assert selected.occurred_on == SNAPSHOT and selected.occurred_on_origin == "source_iso_timestamps"
    assert original.occurred_on is None


def test_undated_actual_context_preview_explains_unusable_sources_and_apply_refuses(tmp_path):
    source, path = conversation(), pack_file(tmp_path)
    selected = select(source, path, require_usable=False)
    assert selected.occurred_on is None
    assert evidence_context_for(selected)["references"][0]["rejection_reasons"] == ["missing_occurrence_date"]
    with pytest.raises(ValueError, match="No selected pack references"):
        select(source, path)
    assert source.reference_context is None and source.references == []


@pytest.mark.parametrize("on", [None, "2026-11-03"])
def test_snapshot_review_preserves_unknown_or_historical_actual_date_and_scope(tmp_path, on):
    source = conversation(occurred_on=on)
    original = source.model_dump()
    selected = select(source, pack_file(tmp_path), mode="snapshot_review", as_of=SNAPSHOT)
    assert selected.occurred_on == on and selected.knowledge_scope is None
    assert selected.messages == source.messages and source.model_dump() == original
    assert reference_applicable(selected.references[0], selected)
    context = evidence_context_for(selected)
    assert context["temporal"]["occurred_on"] == on
    assert context["assessment"] == {
        "mode": "snapshot_review", "conditional": True, "scope": SCOPE, "as_of": SNAPSHOT,
        "rationale": selected.reference_context.rationale,
        "pack_id": selected.reference_context.pack_id,
        "pack_sha256": selected.reference_context.pack_sha256}


def test_snapshot_review_preserves_derivable_historical_source_date_without_assigning_it(tmp_path):
    source = conversation(timestamps=["2026-11-03T10:00:00Z", "2026-11-03T10:00:01Z"])
    selected = select(source, pack_file(tmp_path), mode="snapshot_review", as_of=SNAPSHOT)
    assert selected.occurred_on is None and selected.occurred_on_origin is None
    assert evidence_context_for(selected)["temporal"]["occurred_on"] == "2026-11-03"
    assert reference_applicable(selected.references[0], selected)


def test_snapshot_review_never_extends_a_normal_policy_validity_window(tmp_path):
    refs = [snapshot_reference(), Reference(id="past-rule", text="Past policy", provenance="Explicit interval",
                                           scope=SCOPE, valid_from="2026-11-03", valid_until="2026-11-03"),
            Reference(id="current-rule", text="Current policy", provenance="Explicit interval",
                      scope=SCOPE, valid_from=SNAPSHOT, valid_until=SNAPSHOT)]
    selected = select(conversation(occurred_on="2026-11-03"), pack_file(tmp_path, refs),
                      mode="snapshot_review", as_of=SNAPSHOT)
    statuses = {r["reference_id"]: r for r in evidence_context_for(selected)["references"]}
    assert statuses["official-product-guide"]["usable"] and statuses["past-rule"]["usable"]
    assert not statuses["current-rule"]["usable"]
    assert statuses["current-rule"]["rejection_reasons"] == ["before_validity_window"]


@pytest.mark.parametrize("kwargs", [
    {"mode": "snapshot_review"}, {"mode": "snapshot_review", "as_of": "20261107"},
    {"mode": "snapshot_review", "as_of": SNAPSHOT, "occurred_on": SNAPSHOT},
    {"mode": "conversation_date", "as_of": SNAPSHOT},
])
def test_ambiguous_or_conflated_assessment_dates_are_rejected(tmp_path, kwargs):
    source = conversation()
    with pytest.raises(ValueError):
        select(source, pack_file(tmp_path), **kwargs)
    assert source.occurred_on is None and source.knowledge_scope is None


@pytest.mark.parametrize("mode", ["conversation_date", "snapshot_review"])
def test_known_wrong_scope_and_source_timestamp_conflicts_cannot_be_overridden(tmp_path, mode):
    path = pack_file(tmp_path)
    kwargs = {"as_of": SNAPSHOT} if mode == "snapshot_review" else {"occurred_on": SNAPSHOT}
    with pytest.raises(ValueError, match="scope"):
        select(conversation(scope="another-broker"), path, mode=mode, **kwargs)
    source = conversation(occurred_on=SNAPSHOT,
                          timestamps=["2026-11-03T10:00:00Z", "2026-11-03T10:00:01Z"])
    with pytest.raises(ValueError, match="conflicts with original source timestamps"):
        select(source, path, mode=mode, **kwargs)


def test_actual_date_cannot_override_a_partial_absolute_timestamp(tmp_path):
    source = conversation(timestamps=["2026-11-03T10:00:00Z", "00:02"])
    with pytest.raises(ValueError, match="conflicts with original source timestamps"):
        select(source, pack_file(tmp_path), occurred_on=SNAPSHOT)


def test_repeated_selection_is_idempotent_but_changed_source_content_is_not_silently_replaced(tmp_path):
    path = pack_file(tmp_path)
    selected = select(conversation(occurred_on=SNAPSHOT), path)
    repeated = select(selected, path)
    assert repeated == selected and len(repeated.references) == 1
    pack_file(tmp_path, [snapshot_reference(text="Different source content")])
    with pytest.raises(ValueError, match="different source content"):
        select(selected, path)


def test_pack_context_requires_a_meaningful_rationale_and_exact_manifest_hash(tmp_path):
    with pytest.raises(ValueError, match="rationale"):
        select_reference_context(conversation(), pack_file(tmp_path), SCOPE, mode="snapshot_review",
                                 as_of=SNAPSHOT, rationale="  ")
    with pytest.raises(ValueError):
        ReferenceContext(mode="snapshot_review", scope=SCOPE, as_of=SNAPSHOT, rationale="Explicit assumption",
                         pack_id="guide", pack_sha256="not-a-hash")


def test_new_context_cannot_bypass_conflict_checks_when_validating_without_derivation(tmp_path):
    selected = select(conversation(occurred_on=SNAPSHOT), pack_file(tmp_path))
    forged = selected.model_copy(update={"messages": [Message(id="bad-date", speaker="client",
                                                               text="Source", timestamp="2026-11-03T00:00:00Z")]})
    assert "source_date_conflict" in reference_rejection_reasons(forged.references[0], forged)
    wrong_scope = selected.model_copy(update={"knowledge_scope": "another-broker"})
    assert "reference_context_scope_mismatch" in reference_rejection_reasons(wrong_scope.references[0], wrong_scope)


def test_payload_carries_usable_official_text_and_context_while_fingerprinting_the_basis(tmp_path):
    source, path, rubric = conversation(occurred_on=SNAPSHOT), pack_file(tmp_path), load_checklist()
    actual = select(source, path)
    review = select(source, path, mode="snapshot_review", as_of=SNAPSHOT)
    payload = json.loads(payload_for(review, rubric, grounded=True))
    assert payload["usable_reference_ids"] == ["official-product-guide"]
    assert payload["conversation"]["references"][0]["text"] == snapshot_reference().text
    assert payload["conversation"]["knowledge_scope"] is None
    assert payload["conversation"]["occurred_on"] == SNAPSHOT
    assert payload["evidence_context"]["assessment"]["conditional"]
    assert fingerprint(actual, rubric, grounded=True) != fingerprint(review, rubric, grounded=True)
    assert source.reference_context is None and source.references == []


def test_legacy_payload_and_validation_are_not_reinterpreted_by_new_optional_fields():
    source = conversation(occurred_on=SNAPSHOT, scope=SCOPE, timestamps=["2026-11-03T00:00:00Z"])
    legacy = Reference(id="old-guide", text="Legacy policy", provenance="Old source", scope=SCOPE,
                       valid_from=SNAPSHOT, valid_until=SNAPSHOT)
    source.references = [legacy]
    assert reference_applicable(legacy, source)
    assert not reference_applicable(legacy, source, derive_dates=True)
    payload = json.loads(payload_for(source, load_checklist()))
    assert "reference_context" not in payload["conversation"]
    assert "snapshot_on" not in payload["conversation"]["references"][0]
    assert "date_basis" not in payload["conversation"]["references"][0]
    assert "evidence_context" not in payload
    assert PROMPT_VERSION == "evaluator-v2-452e92fc403a" and GROUNDED_VERSION.startswith("evaluator-v9-")

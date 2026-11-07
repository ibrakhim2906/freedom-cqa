"""Source references are exact immutable selections, not automatic quote repairs."""

from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from cqa.models import Checklist, Conversation, Evaluation, Judgment
from cqa.scoring import calculate_score
from cqa.source_spans import VERSION, build_catalog


def fixture():
    conversation = Conversation.model_validate({
        "id": "diagnostic-case-id", "channel": "agent chat", "language": "KZ",
        "knowledge_scope": "training-portal", "occurred_on": "2026-11-07",
        "messages": [
            {"id": "client-source", "timestamp": "11:00", "speaker": "client",
             "text": "I see the button. I have not clicked it."},
            {"id": "operator-source", "timestamp": "11:01", "speaker": "operator",
             "text": "\r\n  Сәлеметсіз бе 👩🏽‍💻. Екінші сөйлем!\r\n"},
            {"id": "system-source", "timestamp": "11:02", "speaker": "system",
             "text": "No later actions occurred. No file was opened."},
            {"id": "bot-source", "timestamp": "11:03", "speaker": "bot",
             "text": "Здравствуйте. Это сообщение бота."}],
        "references": [
            {"id": "same-text-one", "text": "Execution follows review. No deadline is stated.",
             "provenance": "Saved source one", "scope": "training-portal", "valid_from": "2026-01-01"},
            {"id": "same-text-two", "text": "Execution follows review. No deadline is stated.",
             "provenance": "Saved source two", "scope": "different-product", "valid_from": "2026-01-01"}]})
    checklist = Checklist.model_validate({"id": "custom-checklist", "version": "3", "title": "Review",
        "instructions": ["Global instructions are not criterion-rule quotation sources."], "criteria": [
            {"id": "opening", "title": "Opening", "instruction": "Greet and introduce yourself. Keep the first response courteous.",
             "kind": "binary", "weight": 40, "na_condition": None,
             "levels": [{"value": "yes", "fraction": 1, "description": "The opening meets the rule."},
                        {"value": "no", "fraction": 0, "description": "The opening misses a required action."}],
             "channel_guidance": {"voice call": "Assess understandable speech. Do not invent audio evidence."}},
            {"id": "completion", "title": "Completion", "instruction": "Distinguish visibility from completion.",
             "kind": "binary", "weight": 60, "na_condition": None,
             "levels": [{"value": "yes", "fraction": 1, "description": "The opening meets the rule."},
                        {"value": "no", "fraction": 0, "description": "The task claim is wrong."}],
             "channel_guidance": {}}]})
    return conversation, checklist


def source_fields(conversation, checklist):
    result = {("dialogue", m.id, "text"): m.text for m in conversation.messages}
    result.update({("reference", r.id, "text"): r.text for r in conversation.references})
    for criterion in checklist.criteria:
        result[("rule", criterion.id, "instruction")] = criterion.instruction
        for i, level in enumerate(criterion.levels):
            result[("rule", criterion.id, f"levels[{i}].description")] = level.description
        for channel, text in criterion.channel_guidance.items():
            result[("rule", criterion.id, 'channel_guidance["' + channel + '"]')] = text
    return result


def test_catalog_exact_ranges_cover_every_original_field_without_normalization():
    conversation, checklist = fixture()
    catalog = build_catalog(conversation, checklist)
    originals = source_fields(conversation, checklist)
    full_fields = set()
    for span in catalog.entries.values():
        original = originals[(span.kind, span.source_id, span.field)]
        assert span.quote == original[span.start:span.end]
        assert 0 <= span.start <= span.end <= len(original)
        if span.is_full:
            full_fields.add((span.kind, span.source_id, span.field))
            assert span.start == 0 and span.end == len(original)
    assert full_fields == set(originals)
    assert catalog.full_source_count == len(originals)
    kazakh_full = next(s for s in catalog.entries.values() if s.source_id == "operator-source" and s.is_full)
    assert kazakh_full.quote == "\r\n  Сәлеметсіз бе 👩🏽‍💻. Екінші сөйлем!\r\n"
    assert kazakh_full.end != len(kazakh_full.quote.encode("utf-16-le")) // 2
    assert any(not s.is_full and "👩🏽‍💻" in s.quote for s in catalog.entries.values())
    assert not any(s.quote in checklist.instructions for s in catalog.entries.values())


def test_resolve_returns_exact_source_text_not_model_supplied_prose():
    conversation, checklist = fixture()
    catalog = build_catalog(conversation, checklist)
    op = catalog.ids("dialogue", roles={"operator"})[0]
    assert catalog.resolve(op, kind="dialogue", roles={"operator"}) == {
        "message_id": "operator-source", "quote": conversation.messages[1].text}
    ref = catalog.ids("reference")[0]
    assert catalog.resolve(ref, kind="reference") == {
        "reference_id": "same-text-one", "quote": conversation.references[0].text}
    rule = catalog.ids("rule", criterion_id="opening")[0]
    assert catalog.resolve(rule, kind="rule", criterion_id="opening") == {
        "criterion_id": "opening", "quote": checklist.criteria[0].instruction}
    # A misspelled greeting is not a known ID and is never searched or repaired.
    with pytest.raises(ValueError, match="unknown source-span"):
        catalog.resolve("Сәлемсіз бе", kind="dialogue")


@pytest.mark.parametrize("fault", ["unknown", "wrong_role", "wrong_kind", "wrong_rule", "invalid_roles", "role_on_rule"])
def test_resolution_rejects_wrong_identity_kind_role_or_criterion(fault):
    conversation, checklist = fixture()
    catalog = build_catalog(conversation, checklist)
    target = catalog.ids("dialogue", roles={"client"})[0]
    kwargs = {"kind": "dialogue", "roles": {"client"}}
    if fault == "unknown":
        target = "d_c_999999"
    elif fault == "wrong_role":
        kwargs["roles"] = {"operator"}
    elif fault == "wrong_kind":
        kwargs = {"kind": "reference"}
    elif fault == "wrong_rule":
        target = catalog.ids("rule", criterion_id="opening")[0]
        kwargs = {"kind": "rule", "criterion_id": "completion"}
    elif fault == "invalid_roles":
        kwargs["roles"] = {"supervisor"}
    else:
        target = catalog.ids("rule")[0]
        kwargs = {"kind": "rule", "roles": {"operator"}}
    with pytest.raises(ValueError):
        catalog.resolve(target, **kwargs)


def test_duplicate_quote_text_keeps_different_reference_and_rule_identities():
    conversation, checklist = fixture()
    catalog = build_catalog(conversation, checklist)
    refs = [s for s in catalog.entries.values() if s.kind == "reference" and s.is_full]
    assert refs[0].quote == refs[1].quote and refs[0].span_id != refs[1].span_id
    assert catalog.resolve(refs[1].span_id, kind="reference")["reference_id"] == "same-text-two"
    descriptions = [s for s in catalog.entries.values() if s.kind == "rule" and s.field == "levels[0].description"]
    assert descriptions[0].quote == descriptions[1].quote and descriptions[0].span_id != descriptions[1].span_id
    with pytest.raises(ValueError, match="another criterion"):
        catalog.resolve(descriptions[1].span_id, kind="rule", criterion_id="opening")


@pytest.mark.parametrize("change", ["text", "role", "timestamp", "scope", "date", "ref_scope", "ref_text", "rule", "version"])
def test_binding_rejects_changed_source_or_applicability_context(change):
    conversation, checklist = fixture()
    catalog = build_catalog(conversation, checklist)
    c, r = conversation.model_copy(deep=True), checklist.model_copy(deep=True)
    if change == "text":
        c.messages[1].text = c.messages[1].text.replace("Сәлеметсіз", "Сәлемсіз")
    elif change == "role":
        c.messages[1].speaker = "client"
    elif change == "timestamp":
        c.messages[1].timestamp = "later"
    elif change == "scope":
        c.knowledge_scope = "other-platform"
    elif change == "date":
        c.occurred_on = "2026-11-06"
    elif change == "ref_scope":
        c.references[0].scope = "other-platform"
    elif change == "ref_text":
        c.references[0].text += " Changed policy."
    elif change == "rule":
        r.criteria[0].instruction = "A different expectation."
    else:
        r.version = "4"
    with pytest.raises(ValueError, match="does not match"):
        catalog.assert_sources(c, r)


def test_diagnostic_case_id_is_not_a_source_identity_or_payload_hint():
    conversation, checklist = fixture()
    catalog = build_catalog(conversation, checklist)
    renamed = conversation.model_copy(update={"id": "negative-incomplete-forced-gold"})
    same = build_catalog(renamed, checklist)
    assert same.fingerprint == catalog.fingerprint
    assert same.payload() == catalog.payload()
    catalog.assert_sources(renamed, checklist)
    assert "diagnostic-case-id" not in str(catalog.payload())


def test_budget_never_drops_full_sources_and_fragment_ids_remain_stable():
    conversation, checklist = fixture()
    all_spans = build_catalog(conversation, checklist)
    tiny = build_catalog(conversation, checklist, max_spans=1)
    assert tiny.over_budget
    assert len(tiny.entries) == tiny.full_source_count == all_spans.full_source_count
    assert all(s.is_full for s in tiny.entries.values())
    capped = build_catalog(conversation, checklist, max_spans=all_spans.full_source_count + 4)
    assert len(capped.entries) == capped.full_source_count + 4
    assert not capped.over_budget
    for span_id, entry in capped.entries.items():
        assert all_spans.entries[span_id] == entry
    # Optional fragments are distributed over distinct sources, not all spent on
    # the first long message or instruction.
    fragment_sources = {s.source_id for s in capped.entries.values() if not s.is_full}
    assert len(fragment_sources) == 4


@pytest.mark.parametrize("budget", [0, -1, True, 1.5, "500"])
def test_invalid_fragment_budgets_rejected(budget):
    conversation, checklist = fixture()
    with pytest.raises(ValueError, match="positive integer"):
        build_catalog(conversation, checklist, max_spans=budget)


def test_catalog_and_entries_are_immutable_and_payload_is_a_detached_copy():
    conversation, checklist = fixture()
    catalog = build_catalog(conversation, checklist)
    entry = next(iter(catalog.entries.values()))
    with pytest.raises(FrozenInstanceError):
        entry.quote = "invented"
    with pytest.raises(FrozenInstanceError):
        catalog.fingerprint = "changed"
    with pytest.raises(TypeError):
        catalog.entries[entry.span_id] = entry
    payload = catalog.payload()
    assert payload["version"] == VERSION
    assert all("text" not in s for s in payload["spans"] if s["is_full"])
    assert all("text" in s for s in payload["spans"] if not s["is_full"])
    payload["spans"][0]["source_id"] = "invented"
    assert catalog.entries[entry.span_id].source_id == entry.source_id


def test_blank_fields_retained_for_source_coverage_but_not_usable_as_evidence():
    conversation, checklist = fixture()
    conversation.messages[0].text = " \r\n\t"
    catalog = build_catalog(conversation, checklist)
    blank = next(s for s in catalog.entries.values() if s.source_id == "client-source")
    assert blank.is_full and blank.quote == " \r\n\t"
    assert blank.span_id not in catalog.ids("dialogue", roles={"client"})
    with pytest.raises(ValueError, match="Blank"):
        catalog.resolve(blank.span_id, kind="dialogue")


def test_building_and_resolving_catalog_does_not_mutate_input_or_choose_a_score():
    conversation, checklist = fixture()
    before = deepcopy((conversation.model_dump(), checklist.model_dump()))
    evaluation = Evaluation(judgments=[Judgment(criterion_id=c.id, status="scored", answer="yes",
        explanation="Explicit test judgment, not produced by the catalog.", evidence=[], counterevidence=[],
        checked_message_ids=[], uncertainty=None) for c in checklist.criteria], request_coverage=[], scope_notes=[])
    score = calculate_score(evaluation, checklist)
    catalog = build_catalog(conversation, checklist)
    for span_id in catalog.ids():
        entry = catalog.entries[span_id]
        catalog.resolve(span_id, kind=entry.kind)
    assert (conversation.model_dump(), checklist.model_dump()) == before
    assert calculate_score(evaluation, checklist) == score

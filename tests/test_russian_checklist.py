"""Protect the versioned Russian edition's schema and deterministic scoring contract."""

import re
from pathlib import Path

import pytest

from cqa.models import Evaluation, Judgment
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score

ROOT = Path(__file__).resolve().parents[1]


def test_farewell_clarification_preserves_all_other_rules_and_scoring():
    previous = load_checklist(ROOT / "checklists/freedom-reviewed-017.json").model_dump()
    current = load_checklist(ROOT / "checklists/freedom-reviewed-018.json").model_dump()
    assert current["version"] == "1-reviewed-018"
    current["version"] = previous["version"]
    old_closing = next(c for c in previous["criteria"] if c["id"] == "closing")
    new_closing = next(c for c in current["criteria"] if c["id"] == "closing")
    assert new_closing["instruction"].startswith(old_closing["instruction"] + "\n\n")
    assert len(new_closing["instruction"]) > len(old_closing["instruction"])
    new_closing["instruction"] = old_closing["instruction"]
    assert current == previous


@pytest.fixture(scope="module")
def editions():
    return tuple(load_checklist(ROOT / f"checklists/freedom-reviewed-{version}.json") for version in ("016", "017"))


def test_russian_edition_is_distinct_with_identical_scoring_schema(editions):
    previous, russian = editions
    assert previous.id == russian.id == "freedom-chat-quality"
    assert previous.version == "1-reviewed-016"
    assert russian.version == "1-reviewed-017"
    assert [criterion.id for criterion in russian.criteria] == [criterion.id for criterion in previous.criteria]
    for old, new in zip(previous.criteria, russian.criteria, strict=True):
        assert (new.kind, new.weight) == (old.kind, old.weight)
        assert [(level.value, level.fraction) for level in new.levels] == [
            (level.value, level.fraction) for level in old.levels]
        assert bool(new.na_condition) == bool(old.na_condition)
        assert new.channel_guidance.keys() == old.channel_guidance.keys()


def test_all_displayed_rule_text_is_russian(editions):
    _, russian = editions
    texts = [russian.title, *russian.instructions]
    for criterion in russian.criteria:
        texts.extend([criterion.title, criterion.instruction, criterion.na_condition or "",
                      *criterion.channel_guidance.values(), *[level.description for level in criterion.levels]])
        assert "\n\n" in criterion.instruction
    assert all(not re.search(r"[A-Za-z]", text) for text in texts)


@pytest.mark.parametrize("changes,total,applicable", [
    ({}, 100, 100),
    ({"contact": ("scored", "no", None)}, 90, 100),
    ({"consultation": ("scored", "15", None)}, 95, 100),
    ({"management": ("scored", "7", None)}, 95.5, 100),
    ({"management": ("scored", "4", None)}, 91, 100),
    ({"needs": ("not_applicable", None, None)}, 100, 85),
    ({"closing": ("needs_review", None, "Неясно, была ли возможность ответить.")}, None, 100),
    ({"serious": ("scored", "yes", None)}, 100, 100),
    ({"identity": ("not_applicable", None, None), "management": ("scored", "7", None)}, 94.38, 80),
])
def test_scoring_na_flags_and_uncertainty_are_preserved(editions, changes, total, applicable):
    previous, russian = editions
    judgments = []
    for criterion in previous.criteria:
        answer = "no" if criterion.kind == "flag" else criterion.levels[0].value
        status, answer, uncertainty = changes.get(criterion.id, ("scored", answer, None))
        judgments.append(Judgment(criterion_id=criterion.id, status=status, answer=answer,
            explanation="Ручной пример для проверки арифметики.", evidence=[], counterevidence=[],
            checked_message_ids=[], uncertainty=uncertainty))
    evaluation = Evaluation(judgments=judgments, request_coverage=[], scope_notes=[])
    original_score = calculate_score(evaluation, previous)
    russian_score = calculate_score(evaluation, russian)
    assert russian_score == original_score
    assert russian_score["total"] == total
    assert russian_score["applicable_weight"] == applicable
    if changes.get("serious", (None, None, None))[1] == "yes":
        assert russian_score["flags"]["serious"] == "yes"

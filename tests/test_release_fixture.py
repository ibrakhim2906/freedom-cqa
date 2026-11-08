"""Keep the corrected release benchmark grounded before spending on inference."""

import pytest

from cqa.datasets import load_cases
from cqa.grounding import evidence_context_for
from cqa.settings import ROOT

CORRECTED = load_cases(ROOT / "evals/fresh-release-v2.jsonl")


@pytest.mark.parametrize("case", CORRECTED, ids=lambda case: case.id)
def test_release_reference_policy_is_available_to_the_evaluator(case):
    references = evidence_context_for(case.evaluator_input())["references"]
    assert references, f"{case.id}: expected self-contained reference policy"
    assert all(reference["usable"] for reference in references), references


def test_scope_repair_preserves_dialogues_references_and_frozen_labels():
    original = load_cases(ROOT / "evals/fresh-release-v1.jsonl")
    assert len(original) == len(CORRECTED) == 10
    for before, after in zip(original, CORRECTED, strict=True):
        expected = before.model_dump()
        expected["conversation"]["knowledge_scope"] = after.conversation.knowledge_scope
        assert after.model_dump() == expected

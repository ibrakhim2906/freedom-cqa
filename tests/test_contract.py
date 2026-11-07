from dataclasses import replace
from decimal import Decimal

import pytest

from cqa.datasets import authored_cases
from cqa.ledger import BudgetExceeded, Ledger
from cqa.models import Checklist, Criterion, Evaluation, Evidence, Judgment, Level
from cqa.prompt import payload_for
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import Settings


@pytest.fixture
def rubric():
    return load_checklist()


@pytest.fixture
def clean_case():
    return authored_cases()[0]


@pytest.fixture
def valid(clean_case):
    return Evaluation(judgments=[Judgment(criterion_id=e.criterion_id, status=e.status,
        answer=e.answer, explanation=e.rationale, evidence=[Evidence(message_id="m2",
        quote="Hello, I'm Dana.")], counterevidence=[], checked_message_ids=["m1", "m2", "m3", "m4"],
        uncertainty=None) for e in clean_case.expectations], request_coverage=[], scope_notes=[])


def test_weight_redistribution_and_separate_serious_flag(valid, rubric, clean_case):
    validate_evaluation(valid, clean_case.conversation, rubric)
    scored = calculate_score(valid, rubric)
    assert scored["applicable_weight"] == 65
    assert scored["total"] == 100
    next(j for j in valid.judgments if j.criterion_id == "serious").answer = "yes"
    assert calculate_score(valid, rubric)["total"] == 100
    assert calculate_score(valid, rubric)["flags"]["serious"] == "yes"


def test_discrete_scale_converted_to_weight_and_rounded(valid, rubric):
    next(j for j in valid.judgments if j.criterion_id == "management").answer = "7"
    result = calculate_score(valid, rubric)
    assert result["total"] == 93.08
    assert next(x for x in result["contributions"] if x["criterion_id"] == "management")["points"] == 10.5


def test_unresolved_is_not_silently_na(valid, rubric):
    judgment = next(j for j in valid.judgments if j.criterion_id == "consultation")
    judgment.status, judgment.answer, judgment.uncertainty = "needs_review", None, "Missing reference"
    score = calculate_score(valid, rubric)
    assert score["total"] is None and score["provisional"]
    assert score["applicable_weight"] == 65


@pytest.mark.parametrize("change", ["illegal_na", "illegal_scale", "missing_criterion", "duplicate_criterion", "invented_quote"])
def test_invalid_model_outputs_are_rejected(valid, rubric, clean_case, change):
    if change == "illegal_na":
        judgment = next(j for j in valid.judgments if j.criterion_id == "empathy")
        judgment.status, judgment.answer = "not_applicable", None
    elif change == "illegal_scale":
        next(j for j in valid.judgments if j.criterion_id == "consultation").answer = "13"
    elif change == "missing_criterion":
        valid.judgments.pop()
    elif change == "duplicate_criterion":
        valid.judgments.append(valid.judgments[0])
    else:
        valid.judgments[0].evidence[0].quote = "I verified your identity."
    with pytest.raises(ValueError):
        validate_evaluation(valid, clean_case.conversation, rubric)


def test_new_runtime_rubric_uses_generic_scoring():
    rubric = Checklist(id="unseen", version="1", title="New", instructions=[], criteria=[
        Criterion(id="arbitrary-new-id", title="Custom", instruction="Choose the defined tier.", kind="scale",
                  weight=3, levels=[Level(value="bronze", fraction=.2, description="Partial"),
                                    Level(value="gold", fraction=1, description="Complete")])])
    result = Evaluation(judgments=[Judgment(criterion_id="arbitrary-new-id", status="scored", answer="bronze",
        explanation="Partial", evidence=[], counterevidence=[], checked_message_ids=["m1"], uncertainty=None)],
        request_coverage=[], scope_notes=[])
    assert calculate_score(result, rubric)["total"] == 20


def test_labels_and_diagnostic_ids_are_not_in_inference(clean_case, rubric):
    case = clean_case.model_copy(deep=True)
    case.id = case.conversation.id = "SECRET_EXPECTED_FAILURE_ID"
    case.expectations[0].rationale = "SECRET_REFERENCE_LABEL"
    payload = payload_for(case.evaluator_input(), rubric)
    assert "SECRET_EXPECTED_FAILURE_ID" not in payload
    assert "SECRET_REFERENCE_LABEL" not in payload
    assert '"expectations"' not in payload and '"label_provenance"' not in payload


def test_suite_integrity_and_no_claimed_human_labels():
    cases = authored_cases()
    assert len(cases) == 40 and len({c.id for c in cases}) == 40
    assert {c.conversation.language for c in cases} == {"RU", "KZ", "EN"}
    assert all(c.label_provenance == "ai_authored_provisional" for c in cases)
    assert any(c.checklist_override for c in cases)
    assert all(c.evaluator_input().messages for c in cases)


def test_reservations_and_unknown_costs_cannot_evade_budget(tmp_path):
    ledger = Ledger(tmp_path / "usage.sqlite3", .1)
    call = ledger.reserve("test", .08, .1)
    ledger.finish(call, "failed")
    with pytest.raises(BudgetExceeded):
        ledger.reserve("test", .03, .1)
    assert ledger.committed() == pytest.approx(.08)
    ledger.finish(call, "completed", cost=.01, input_tokens=1, output_tokens=1)
    ledger.reserve("test", .08, .1)
    assert ledger.committed() == pytest.approx(.09)


def test_run_budget_does_not_reset_lifetime_budget(tmp_path):
    ledger = Ledger(tmp_path / "usage.sqlite3", .1)
    call = ledger.reserve("test", .08, .1)
    ledger.finish(call, "completed", cost=.08)
    reopened = Ledger(tmp_path / "usage.sqlite3", .1)
    with pytest.raises(BudgetExceeded):
        reopened.reserve("test", .03, .5)


def test_missing_key_is_an_error_not_a_fallback():
    settings = Settings(api_key="")
    with pytest.raises(ValueError, match="no offline"):
        settings.require_key()
    assert "secret-key" not in repr(replace(settings, api_key="secret-key"))


def test_binary_fraction_arithmetic_is_decimal(valid, rubric):
    assert sum(Decimal(str(c.weight)) for c in rubric.criteria) == Decimal(100)
    for judgment in valid.judgments:
        if judgment.status == "scored" and judgment.criterion_id != "serious":
            criterion = next(c for c in rubric.criteria if c.id == judgment.criterion_id)
            judgment.answer = min(criterion.levels, key=lambda level: level.fraction).value
    assert calculate_score(valid, rubric)["total"] == 0

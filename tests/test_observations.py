import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cqa.datasets import authored_cases
from cqa.evaluator import Evaluator
from cqa.ledger import BudgetExceeded, Ledger
from cqa.models import Evaluation, Judgment
from cqa.observations import Observations, observation_schema, validate_observations
from cqa.settings import Settings


def fixture_data():
    case = authored_cases()[-1]
    conversation, checklist = case.conversation, case.checklist_override
    item = {"criterion_id": checklist.criteria[0].id, "factual_summary": "The human made this statement.",
            "evidence": [{"message_id": "m2", "quote": conversation.messages[1].text}],
            "counterevidence": [], "checked_message_ids": ["m1", "m2"], "unknowns": []}
    return conversation, checklist, {"criteria": [item]}


@pytest.mark.parametrize("defect", ["quote", "duplicate", "missing", "span"])
def test_observations_reject_fabricated_sources_and_bad_criterion_coverage(defect):
    conversation, checklist, data = fixture_data()
    if defect == "quote":
        data["criteria"][0]["evidence"][0]["quote"] = "Invented protected balance"
    elif defect == "duplicate":
        data["criteria"] *= 2
    elif defect == "missing":
        data["criteria"] = []
    else:
        data["criteria"][0]["checked_message_ids"] = ["not-real"]
    with pytest.raises(ValueError):
        validate_observations(Observations.model_validate(data), conversation, checklist)


def test_two_stage_real_contract_retains_transcript_and_accounts_each_api_call(tmp_path):
    async def run():
        conversation, checklist, data = fixture_data()
        observed = Observations.model_validate(data)
        validate_observations(observed, conversation, checklist)
        schema = observation_schema(conversation, checklist)
        assert schema["$defs"]["CriterionObservations"]["properties"]["criterion_id"]["enum"] == [checklist.criteria[0].id]
        grade = Evaluation(judgments=[Judgment(criterion_id=checklist.criteria[0].id, status="scored",
            answer=checklist.criteria[0].levels[0].value, explanation="Configured tier", evidence=[],
            counterevidence=[], checked_message_ids=["m1", "m2"], uncertainty=None)], request_coverage=[], scope_notes=[])
        ledger = Ledger(tmp_path / "usage.sqlite3", 1)
        evaluator = Evaluator(Settings(api_key="fictional-test"), ledger, 1, strategy="evidence-first")
        def response(text):
            return SimpleNamespace(id="fictional", model=evaluator.settings.model, output_text=text,
                                   status="completed", usage=SimpleNamespace(input_tokens=100, output_tokens=100))
        evaluator.client.responses.create = AsyncMock(side_effect=[response(observed.model_dump_json()),
                                                                  response(grade.model_dump_json())])
        try:
            result = await evaluator.evaluate(conversation, checklist)
            assert result["status"] == "completed" and result["attempt_count"] == 2
            assert [a["stage"] for a in result["attempt_records"]] == ["observations", "grading"]
            assert result["usage"]["estimated_cost_usd"] == pytest.approx(ledger.committed())
            calls = evaluator.client.responses.create.call_args_list
            assert calls[0].kwargs["max_output_tokens"] == 3000
            payload = json.loads(calls[1].kwargs["input"])
            assert payload["source_observations"] == data
            assert payload["conversation"]["messages"] == [m.model_dump() for m in conversation.messages]
            assert "expectations" not in payload
            assert result["attempt_records"][0]["score"] is None
        finally:
            await evaluator.close()
    asyncio.run(run())


@pytest.mark.parametrize("failure", ["invalid", "budget"])
def test_failed_stage_has_no_silent_direct_fallback_and_keeps_paid_work(tmp_path, failure):
    async def run():
        conversation, checklist, data = fixture_data()
        evaluator = Evaluator(Settings(api_key="fictional-test"), Ledger(tmp_path / "usage.sqlite3", 1), 1,
                              strategy="evidence-first")
        good = {"status": "completed", "observations": data, "evaluation": None, "score": None,
                "stage": "observations", "ledger_call_id": 1, "latency_seconds": 1,
                "usage": {"input_tokens": 100, "output_tokens": 100, "estimated_cost_usd": .0012}}
        bad = good | {"status": "failed", "error": "invalid_evaluation_ValueError"}
        evaluator._attempt = AsyncMock(side_effect=[bad, bad] if failure == "invalid" else [good, BudgetExceeded()])
        try:
            result = await evaluator.evaluate(conversation, checklist)
            assert result["status"] == "failed" and result["score"] is None
            assert evaluator._attempt.call_count == 2
            assert evaluator._attempt.call_args_list[0].kwargs["stage"] == "observations"
            if failure == "invalid":
                assert evaluator._attempt.call_args_list[1].kwargs["stage"] == "observations"
                assert result["attempt_count"] == 2
            else:
                assert result["error"] == "grading_budget_limit" and result["attempt_count"] == 1
            assert result["usage"]["estimated_cost_usd"] >= .0012
        finally:
            await evaluator.close()
    asyncio.run(run())

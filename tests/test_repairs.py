import asyncio
from unittest.mock import AsyncMock

from cqa.datasets import authored_cases
from cqa.evaluator import Evaluator, schema_for
from cqa.ledger import BudgetExceeded, Ledger
from cqa.rubric import load_checklist
from cqa.settings import Settings


def test_schema_constrains_actual_ids_without_fixed_rubric_ids():
    case = authored_cases()[-1]
    rubric = case.checklist_override
    schema = schema_for(case.conversation, rubric)
    definitions = schema["$defs"]
    assert definitions["Judgment"]["properties"]["criterion_id"]["enum"] == ["followup-contract"]
    assert definitions["Evidence"]["properties"]["message_id"]["enum"] == ["m1", "m2"]
    assert definitions["RequestCoverage"]["properties"]["answer_message_ids"]["items"]["enum"] == ["m2"]


def test_bounded_repair_preserves_first_failure_and_accounts_both_attempts(tmp_path):
    async def run():
        evaluator = Evaluator(Settings(api_key="fictional-test", ledger_path=tmp_path / "usage.sqlite3"),
                              Ledger(tmp_path / "usage.sqlite3", 1), 1)
        evaluator._attempt = AsyncMock(side_effect=[
            {"status": "failed", "error": "invalid_evaluation_ValueError", "validation_reason": "Bad reference",
             "raw_output_text": "Rejected", "latency_seconds": 1,
             "usage": {"input_tokens": 10, "output_tokens": 20, "estimated_cost_usd": .01}},
            {"status": "completed", "error": None, "latency_seconds": 2,
             "usage": {"input_tokens": 30, "output_tokens": 40, "estimated_cost_usd": .02}},
        ])
        try:
            result = await evaluator.evaluate(authored_cases()[0].conversation, load_checklist())
            assert result["attempt_count"] == 2
            assert result["attempt_records"][0]["status"] == "failed"
            assert result["usage"]["estimated_cost_usd"] == .03
            assert result["latency_seconds"] == 3
            assert evaluator._attempt.call_args_list[1].args[2]["validation_error"] == "Bad reference"
        finally:
            await evaluator.close()
    asyncio.run(run())


def test_repair_budget_exhaustion_keeps_original_billable_failure(tmp_path):
    async def run():
        evaluator = Evaluator(Settings(api_key="fictional-test"), Ledger(tmp_path / "usage.sqlite3", 1), 1)
        evaluator._attempt = AsyncMock(side_effect=[
            {"status": "failed", "error": "invalid_evaluation_ValueError", "latency_seconds": 1,
             "usage": {"input_tokens": 10, "output_tokens": 20, "estimated_cost_usd": .01}},
            BudgetExceeded(),
        ])
        try:
            result = await evaluator.evaluate(authored_cases()[0].conversation, load_checklist())
            assert result["status"] == "failed" and result["attempt_count"] == 1
            assert result["repair_skipped"] == "budget_limit"
            assert result["usage"]["estimated_cost_usd"] == .01
        finally:
            await evaluator.close()
    asyncio.run(run())

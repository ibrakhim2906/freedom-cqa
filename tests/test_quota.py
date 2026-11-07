import asyncio
from unittest.mock import AsyncMock

import httpx
from openai import APIStatusError

from cqa.datasets import authored_cases
from cqa.evaluator import Evaluator
from cqa.ledger import Ledger
from cqa.metrics import summarize
from cqa.rubric import load_checklist
from cqa.settings import Settings


def test_explicit_exhausted_credit_rejection_settles_zero_and_stops_following_requests(tmp_path):
    async def run():
        ledger = Ledger(tmp_path / "usage.sqlite3", 1)
        evaluator = Evaluator(Settings(api_key="fictional-test"), ledger, 1)
        response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        error = APIStatusError("Credits exhausted", response=response,
                               body={"code": "credit_balance_exhausted", "type": "insufficient_quota"})
        evaluator.client.responses.create = AsyncMock(side_effect=error)
        try:
            case = authored_cases()[0]
            first = await evaluator.evaluate(case.conversation, load_checklist())
            second = await evaluator.evaluate(case.conversation, load_checklist())
            assert first["status"] == second["status"] == "failed"
            assert first["settled_cost_usd"] == 0 and first["attempt_count"] == 1
            assert second["billing_state"] == "not_submitted" and second["attempt_count"] == 0
            assert first["evaluation"] is second["evaluation"] is None
            assert evaluator.client.responses.create.call_count == 1
            assert ledger.committed() == 0
            rows = [{"source": "authored", "language": "EN", "channel": "agent chat", "record": r,
                     "comparison": {"checks": [], "total_absolute_error": None}} for r in [first, second]]
            assert summarize(rows)["unknown_cost_attempts"] == 0
        finally:
            await evaluator.close()
    asyncio.run(run())

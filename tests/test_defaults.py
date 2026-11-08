import asyncio
from unittest.mock import AsyncMock

from cqa.datasets import authored_cases
from cqa.evaluator import Evaluator
from cqa.ledger import Ledger
from cqa.assessor import CONTRACT_VERSION, PROMPT_VERSION
from cqa.rubric import load_checklist
from cqa.settings import DEFAULT_STRATEGY, Settings


def test_default_entry_point_uses_assessor_v3_and_reviewed_016(tmp_path):
    async def run():
        evaluator = Evaluator(Settings(api_key="fictional-test"), Ledger(tmp_path / "ledger.sqlite3", 1), 1)
        evaluator._attempt = AsyncMock(return_value={"status": "completed", "latency_seconds": 0,
                                                     "usage": None, "error": None})
        try:
            rubric = load_checklist()
            assert DEFAULT_STRATEGY == evaluator.strategy == "assessor"
            assert evaluator.assessor and not evaluator.grounded
            assert evaluator.workflow_version == PROMPT_VERSION
            assert evaluator.assessor_contract == CONTRACT_VERSION == "rubric-assessor-v3"
            assert rubric.version == "1-reviewed-016"
            result = await evaluator.evaluate(authored_cases()[0].conversation, rubric)
            assert result["strategy"] == "assessor"
        finally:
            await evaluator.close()
    asyncio.run(run())

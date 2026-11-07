import asyncio
from unittest.mock import AsyncMock

from cqa.datasets import authored_cases
from cqa.evaluator import Evaluator
from cqa.ledger import Ledger
from cqa.prompt import GROUNDED_VERSION
from cqa.rubric import load_checklist
from cqa.settings import DEFAULT_STRATEGY, Settings


def test_default_entry_point_uses_grounded_contract_and_reviewed_015(tmp_path):
    async def run():
        evaluator = Evaluator(Settings(api_key="fictional-test"), Ledger(tmp_path / "ledger.sqlite3", 1), 1)
        evaluator._attempt = AsyncMock(return_value={"status": "completed", "latency_seconds": 0,
                                                     "usage": None, "error": None})
        try:
            rubric = load_checklist()
            assert DEFAULT_STRATEGY == evaluator.strategy == "grounded"
            assert evaluator.grounded and evaluator.workflow_version == GROUNDED_VERSION
            assert rubric.version == "1-reviewed-015"
            result = await evaluator.evaluate(authored_cases()[0].conversation, rubric)
            assert result["strategy"] == "grounded"
        finally:
            await evaluator.close()
    asyncio.run(run())

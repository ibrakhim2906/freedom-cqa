import asyncio

import pytest

from cqa.evaluator import Evaluator
from cqa.ledger import Ledger
from cqa.settings import Settings, reservation_input_rate, usage_cost


def test_standard_cache_cost_and_single_attempt_budget(tmp_path):
    assert usage_cost('gpt-6.1-sol', 1000, 100, cached_tokens=200, cache_write_tokens=300) == pytest.approx(.00277)
    assert reservation_input_rate('gpt-6.1-sol') == 2.5
    evaluator = Evaluator.__new__(Evaluator)
    evaluator.settings = Settings(api_key='not-used', repair_attempts=0)
    evaluator.ledger = Ledger(tmp_path / 'usage.sqlite3', .1)
    evaluator.run_ceiling = .1
    evaluator._prepare = lambda *args, **kwargs: ('Instructions', '{}', {}, 512)
    calls = []

    async def attempt(*args, **kwargs):
        calls.append(kwargs)
        return {'status': 'failed', 'error': 'invalid_evaluation_ValueError'}

    evaluator._attempt = attempt
    rows = asyncio.run(evaluator._stage(None, None))
    assert len(calls) == len(rows) == 1
    assert rows[0]['repair_policy'] == 'no_automatic_repair'
    assert evaluator.ledger.committed() == 0

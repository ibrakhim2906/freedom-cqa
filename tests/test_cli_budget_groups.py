import argparse
import asyncio

import pytest

from cqa import cli
from cqa.datasets import authored_cases
from cqa.ledger import Ledger
from cqa.settings import Settings


def test_benchmark_budget_is_independent_of_another_active_run(tmp_path, monkeypatch):
    settings = Settings(api_key="fixture-test", max_spend=1, ledger_path=tmp_path / "ledger.sqlite3")
    competing = Ledger(settings.ledger_path, 1, budget_group="other", group_limit=.5)
    prior = competing.reserve("test-only", .01, 1)
    competing.finish(prior, "completed", cost=.01)
    class TestOnlyEvaluator:
        def __init__(self, settings, ledger, ceiling, strategy):
            self.ledger, self.ceiling = ledger, ceiling
            competing.reserve("test-only", .4, 1)  # Arrives after this run's starting balance was read.
        async def evaluate(self, *_):
            assert self.ledger.budget_group.startswith("benchmark-") and self.ledger.group_limit == .2
            call = self.ledger.reserve("test-only", .15, self.ceiling)
            self.ledger.finish(call, "completed", cost=.01)
            return {"status": "failed", "error": "isolated_fixture", "evaluation": None, "score": None,
                    "usage": {"estimated_cost_usd": .01}, "attempt_records": []}
        async def close(self):
            pass
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli.Settings, "load", lambda *_: settings)
    monkeypatch.setattr(cli, "load_suite", lambda *_: authored_cases()[:1])
    monkeypatch.setattr(cli, "Evaluator", TestOnlyEvaluator)
    args = argparse.Namespace(model=None, concurrency=1, cases_file=None, suite="authored", case=None,
        limit=None, budget_usd=.2, output="artifacts/test.json", checklist=None, strategy="grounded")
    asyncio.run(cli.benchmark(args))
    assert competing.committed() == pytest.approx(.42)  # Unknown competitor reservation was never erased.

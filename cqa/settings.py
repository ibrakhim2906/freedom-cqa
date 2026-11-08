import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STRATEGY = "grounded"

# Standard short-context rates checked against official model pages on 2026-11-07.
# Uncached input is conservatively charged even when the API reports cached tokens.
RATES = {
    "gpt-6.1-sol": (2.0, 10.0),
    "gpt-6-astra": (10.0, 50.0),
    "gpt-6.1-terra": (1.0, 5.0),
    "gpt-6-luna": (0.1, 0.5),
}
# Standard cache read/write rates verified from the official Sol model page.
CACHE_RATES = {"gpt-6.1-sol": (0.10, 2.50)}


def reservation_input_rate(model):
    return max(RATES[model][0], CACHE_RATES.get(model, (0, 0))[1])


def usage_cost(model, input_tokens, output_tokens, *, cached_tokens=0, cache_write_tokens=0, service_tier="default"):
    input_rate, output_rate = RATES[model]
    cached_rate, write_rate = CACHE_RATES.get(model, (input_rate, input_rate))
    cached = min(input_tokens, max(0, cached_tokens))
    written = min(input_tokens - cached, max(0, cache_write_tokens))
    multiplier = 2 if service_tier in {"priority", "fast"} else .5 if service_tier == "flex" else 1
    return multiplier * ((input_tokens - cached - written) * input_rate + cached * cached_rate +
                         written * write_rate + output_tokens * output_rate) / 1_000_000


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str = "gpt-6.1-sol"
    effort: str = "medium"
    max_output_tokens: int = 6000
    timeout: float = 120.0
    max_spend: float = 3.5
    concurrency: int = 3
    ledger_path: Path = ROOT / "data/runtime/usage.sqlite3"
    strategy: str = DEFAULT_STRATEGY
    repair_attempts: int = 1

    @classmethod
    def load(cls, model=None):
        values = {**dotenv_values(ROOT / ".env"), **os.environ}
        settings = cls(
            api_key=values.get("OPENAI_API_KEY") or "",
            model=model or values.get("OPENAI_MODEL") or "gpt-6.1-sol",
            effort=values.get("CQA_REASONING_EFFORT") or "medium",
            max_output_tokens=int(values.get("CQA_MAX_OUTPUT_TOKENS") or 6000),
            timeout=float(values.get("CQA_TIMEOUT_SECONDS") or 120),
            max_spend=float(values.get("CQA_MAX_SPEND_USD") or 3.5),
            concurrency=int(values.get("CQA_CONCURRENCY") or 3),
            ledger_path=Path(values.get("CQA_LEDGER_PATH") or ROOT / "data/runtime/usage.sqlite3"),
            strategy=values.get("CQA_STRATEGY") or DEFAULT_STRATEGY,
            repair_attempts=int(values.get("CQA_REPAIR_ATTEMPTS") or 1),
        )
        settings.validate()
        return settings

    def validate(self):
        if self.repair_attempts not in {0, 1}:
            raise ValueError("Repair attempts must be 0 or 1")
        if self.strategy not in {"direct", "evidence-first", "grounded", "assessor", "assessor-reviewed"}:
            raise ValueError("Unknown evaluator strategy")
        if self.model not in RATES:
            raise ValueError("Model has no configured cost rates; add verified rates before use")
        if not 1 <= self.concurrency <= 8 or not 512 <= self.max_output_tokens <= 16000:
            raise ValueError("Concurrency must be 1-8 and output-token limit 512-16000")
        if not math.isfinite(self.timeout) or not math.isfinite(self.max_spend) or self.timeout <= 0 or self.max_spend <= 0:
            raise ValueError("Timeout and lifetime cost limit must be positive")

    def require_key(self):
        if not self.api_key or self.api_key in {"your_key_here", "YOUR_API_KEY"}:
            raise ValueError("Set OPENAI_API_KEY locally in .env; there is no offline evaluation fallback")

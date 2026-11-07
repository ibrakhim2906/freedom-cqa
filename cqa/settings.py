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
        )
        settings.validate()
        return settings

    def validate(self):
        if self.model not in RATES:
            raise ValueError("Model has no configured cost rates; add verified rates before use")
        if not 1 <= self.concurrency <= 8 or not 512 <= self.max_output_tokens <= 16000:
            raise ValueError("Concurrency must be 1-8 and output-token limit 512-16000")
        if not math.isfinite(self.timeout) or not math.isfinite(self.max_spend) or self.timeout <= 0 or self.max_spend <= 0:
            raise ValueError("Timeout and lifetime cost limit must be positive")

    def require_key(self):
        if not self.api_key or self.api_key in {"your_key_here", "YOUR_API_KEY"}:
            raise ValueError("Set OPENAI_API_KEY locally in .env; there is no offline evaluation fallback")

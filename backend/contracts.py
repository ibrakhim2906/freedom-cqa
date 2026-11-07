from typing import Literal

from pydantic import Field

from cqa.models import Judgment, Reference, StrictModel


class ImportRequest(StrictModel):
    content: str = Field(min_length=1, max_length=10_000_000)


class RunRequest(StrictModel):
    conversation_ids: list[str] = Field(min_length=1, max_length=100)
    checklist_id: str
    request_id: str = Field(min_length=1, max_length=100)
    budget_usd: float = Field(gt=0, le=20, allow_inf_nan=False)
    force: bool = False


class RetryRequest(StrictModel):
    request_id: str = Field(min_length=1, max_length=100)
    budget_usd: float = Field(gt=0, le=20, allow_inf_nan=False)


class ReferenceRequest(StrictModel):
    pack_id: str
    scope: str
    mode: Literal["conversation_date", "snapshot_review"] = "conversation_date"
    occurred_on: str | None = None
    as_of: str | None = None
    rationale: str = Field(min_length=1, max_length=3000)


class AppealRequest(StrictModel):
    criterion_id: str
    author: str = Field(min_length=1, max_length=150)
    reason: str = Field(min_length=1, max_length=6000)
    message_ids: list[str] = Field(min_length=1)
    proposed_status: Literal["scored", "not_applicable", "needs_review"] | None = None
    proposed_answer: str | None = None


class ResolveRequest(StrictModel):
    decision: Literal["accept", "reject"]
    reviewer: str = Field(min_length=1, max_length=150)
    rationale: str = Field(min_length=1, max_length=6000)
    expected_revision: int = Field(ge=0)
    judgment: Judgment | None = None
    supporting_references: list[Reference] = Field(default_factory=list)

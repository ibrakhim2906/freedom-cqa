"""Native lean candidate contract; deliberately not a span-v5 Evaluation."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT = "lean-span-v1"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Interval(Strict):
    start_message_id: str
    end_message_id: str
    message_ids: list[str]


class Deduction(Strict):
    defect: str
    overlap_note: str


class Judgment(Strict):
    criterion_id: str
    status: Literal["scored", "not_applicable", "needs_review"]
    answer: str | None
    explanation: str
    evidence_span_ids: list[str]
    counterevidence_span_ids: list[str]
    rule_span_id: str
    omission: Interval | None
    uncertainty: str | None
    deduction: Deduction | None


class Request(Strict):
    request: str
    request_span_ids: list[str]
    status: Literal["answered", "partial", "unanswered", "next_step", "withdrawn"]
    answer_span_ids: list[str]
    withdrawal_span_ids: list[str]
    omission: Interval | None
    explanation: str


class Correction(Strict):
    correction_span_ids: list[str]
    recovery_span_ids: list[str]
    remaining_consequences: Literal["none_established", "present", "uncertain"]
    explanation: str


class Fact(Strict):
    claim: str
    # Actual truth-dependent grading duties; exclude merely topical/wording links.
    criterion_ids: list[str]
    operator_source_span_ids: list[str]
    kind: Literal["policy", "interaction", "private_state", "commitment", "grading_rule"]
    status: Literal["supported", "contradicted", "unverified"]
    proof_source_span_ids: list[str]
    context_source_span_ids: list[str]
    uncertain_criterion_ids: list[str]
    # Required only for a broader negative: initial-state proof plus every later turn.
    negative_interval: Interval | None
    correction: Correction | None
    explanation: str


class LeanAssessment(Strict):
    contract: Literal["lean-span-v1"]
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewed_message_ids: list[str]
    judgments: list[Judgment]
    request_coverage: list[Request]
    facts: list[Fact]
    scope_notes: list[str]


CONTRACT_HASH = hashlib.sha256(json.dumps(
    LeanAssessment.model_json_schema(), sort_keys=True, separators=(",", ":"),
).encode()).hexdigest()

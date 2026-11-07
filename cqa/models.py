from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def validate_iso_date(value: str):
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("Date must use canonical YYYY-MM-DD format")


class Message(StrictModel):
    id: str
    timestamp: str
    speaker: Literal["client", "operator", "bot", "system"]
    text: str


class Reference(StrictModel):
    id: str
    text: str
    provenance: str
    source_url: str | None = None
    retrieved_on: str | None = None
    scope: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None

    @model_validator(mode="after")
    def valid_dates(self):
        for value in [self.retrieved_on, self.valid_from, self.valid_until]:
            if value is not None:
                validate_iso_date(value)
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("Reference validity window is reversed")
        return self


class Conversation(StrictModel):
    id: str
    channel: Literal["agent chat", "voice call"]
    language: str
    messages: list[Message]
    references: list[Reference] = Field(default_factory=list)
    knowledge_scope: str | None = None
    occurred_on: str | None = None

    @model_validator(mode="after")
    def unique_messages(self):
        if not self.messages or len({m.id for m in self.messages}) != len(self.messages):
            raise ValueError("Conversation needs nonempty, unique message IDs")
        if len({r.id for r in self.references}) != len(self.references):
            raise ValueError("Reference IDs must be unique")
        if self.occurred_on is not None:
            validate_iso_date(self.occurred_on)
        return self


class Level(StrictModel):
    value: str
    fraction: float = Field(ge=0, le=1)
    description: str


class Criterion(StrictModel):
    id: str
    title: str
    instruction: str
    kind: Literal["binary", "scale", "flag"]
    weight: float = Field(ge=0)
    levels: list[Level]
    na_condition: str | None = None
    channel_guidance: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_levels(self):
        if not self.levels or len({x.value for x in self.levels}) != len(self.levels):
            raise ValueError("Criterion needs nonempty, unique allowed levels")
        if self.kind == "flag" and self.weight != 0:
            raise ValueError("A flag must have zero scoring weight")
        return self


class Checklist(StrictModel):
    id: str
    version: str
    title: str
    instructions: list[str]
    criteria: list[Criterion]

    @model_validator(mode="after")
    def unique_criteria(self):
        if not self.criteria or len({c.id for c in self.criteria}) != len(self.criteria):
            raise ValueError("Checklist needs nonempty, unique criteria")
        return self


# Every output field is required (nullable where appropriate), for strict JSON Schema.
class Evidence(StrictModel):
    message_id: str
    quote: str


class Judgment(StrictModel):
    criterion_id: str
    status: Literal["scored", "not_applicable", "needs_review"]
    answer: str | None
    explanation: str
    evidence: list[Evidence]
    counterevidence: list[Evidence]
    checked_message_ids: list[str]
    uncertainty: str | None


class RequestCoverage(StrictModel):
    request: str
    request_message_ids: list[str]
    status: Literal["answered", "partial", "unanswered", "next_step", "withdrawn"]
    answer_message_ids: list[str]
    explanation: str
    # Default preserves the ability to read historical v1 evaluation records.
    withdrawal_message_ids: list[str] = Field(default_factory=list)


class ReferenceEvidence(StrictModel):
    reference_id: str
    quote: str


class ClaimOutcome(StrictModel):
    status: Literal["scored", "not_applicable", "needs_review"]
    answer: str | None


class ClaimImpact(StrictModel):
    criterion_id: str
    when_true: ClaimOutcome
    when_false: ClaimOutcome
    rule_quote: str
    evidence: list[Evidence]
    checked_message_ids: list[str]
    explanation: str


class ClaimCorrection(StrictModel):
    operator_evidence: list[Evidence]
    outcome_evidence: list[Evidence]
    reference_evidence: list[ReferenceEvidence]
    remaining_consequence: Literal["none_established", "present", "uncertain"]
    explanation: str


class ClaimAssessment(StrictModel):
    lifecycle: Literal["active", "corrected"]
    correction: ClaimCorrection | None
    impacts: list[ClaimImpact]


class FactualClaim(StrictModel):
    claim: str
    criterion_ids: list[str]
    operator_evidence: list[Evidence]
    status: Literal["supported", "contradicted", "unverified"]
    material: bool
    reference_evidence: list[ReferenceEvidence]
    dialogue_evidence: list[Evidence]
    explanation: str
    # Historical records retain the original conservative dependency contract.
    # The current provider schema requires a non-null assessment for every claim.
    assessment: ClaimAssessment | None = None


class Deduction(StrictModel):
    criterion_id: str
    rule_quote: str
    defect: str
    evidence: list[Evidence]
    checked_message_ids: list[str]
    overlap_note: str


class Evaluation(StrictModel):
    judgments: list[Judgment]
    request_coverage: list[RequestCoverage]
    scope_notes: list[str]
    # Defaults allow reading frozen historical results, not omitting new API fields.
    factual_claims: list[FactualClaim] = Field(default_factory=list)
    deductions: list[Deduction] = Field(default_factory=list)


class Expectation(StrictModel):
    criterion_id: str
    status: Literal["scored", "not_applicable", "needs_review"]
    answer: str | None
    rationale: str


class TestCase(StrictModel):
    id: str
    family: str
    source: Literal["authored", "organizer"]
    label_provenance: Literal["ai_authored_provisional", "human_reviewed", "unlabelled"]
    tags: list[str]
    conversation: Conversation
    expectations: list[Expectation]
    checklist_override: Checklist | None = None

    def evaluator_input(self):
        # Explicit allowlist: labels, rationale, family, tags and origin never enter inference.
        return self.conversation

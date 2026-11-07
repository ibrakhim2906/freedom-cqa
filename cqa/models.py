from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Message(StrictModel):
    id: str
    timestamp: str
    speaker: Literal["client", "operator", "bot", "system"]
    text: str


class Reference(StrictModel):
    id: str
    text: str
    provenance: str


class Conversation(StrictModel):
    id: str
    channel: Literal["agent chat", "voice call"]
    language: str
    messages: list[Message]
    references: list[Reference] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_messages(self):
        if not self.messages or len({m.id for m in self.messages}) != len(self.messages):
            raise ValueError("Conversation needs nonempty, unique message IDs")
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
    status: Literal["answered", "partial", "unanswered", "next_step"]
    answer_message_ids: list[str]
    explanation: str


class Evaluation(StrictModel):
    judgments: list[Judgment]
    request_coverage: list[RequestCoverage]
    scope_notes: list[str]


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

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
    # Historical references retain their original validity-window semantics.
    # A retrieved snapshot supplies evidence only at its explicit snapshot date.
    date_basis: Literal["policy_validity", "snapshot"] = "policy_validity"
    snapshot_on: str | None = None

    @model_validator(mode="after")
    def valid_dates(self):
        for value in [self.retrieved_on, self.valid_from, self.valid_until, self.snapshot_on]:
            if value is not None:
                validate_iso_date(value)
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("Reference validity window is reversed")
        if self.date_basis == "snapshot":
            if self.snapshot_on is None:
                raise ValueError("Snapshot references require an explicit snapshot_on date")
            if self.valid_from is not None or self.valid_until is not None:
                raise ValueError("Snapshot dates must not be presented as policy validity intervals")
        elif self.snapshot_on is not None:
            raise ValueError("Only snapshot references may set snapshot_on")
        return self


class ReferenceContext(StrictModel):
    mode: Literal["conversation_date", "snapshot_review"]
    scope: str
    as_of: str | None = None
    rationale: str
    pack_id: str
    pack_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def explicit_context(self):
        if not all(value.strip() for value in [self.scope, self.rationale, self.pack_id]):
            raise ValueError("Reference context needs a scope, rationale and pack ID")
        if self.as_of is not None:
            validate_iso_date(self.as_of)
        if self.mode == "snapshot_review" and self.as_of is None:
            raise ValueError("Snapshot review requires an explicit as_of date")
        if self.mode == "conversation_date" and self.as_of is not None:
            raise ValueError("Actual conversation context cannot substitute an assessment date")
        return self


class Conversation(StrictModel):
    id: str
    channel: Literal["agent chat", "voice call"]
    language: str
    messages: list[Message]
    references: list[Reference] = Field(default_factory=list)
    knowledge_scope: str | None = None
    occurred_on: str | None = None
    occurred_on_origin: Literal["supplied", "source_iso_timestamps"] | None = None
    reference_context: ReferenceContext | None = None

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


class OmissionSupport(StrictModel):
    # The interval covers the complete opportunity after the linked request.
    # Its quotes are context for absence, never proof that an answer was given.
    start_message_id: str
    end_message_id: str
    context_evidence: list[Evidence]


class AnswerSupport(StrictModel):
    basis: Literal["explicit", "implied", "next_step", "none", "withdrawn"]
    evidence: list[Evidence]
    inference: str | None
    unresolved_aspects: list[str]
    # Default is historical deserialization only; fresh v2 output must supply it.
    omission: OmissionSupport | None = None


class RequestCoverage(StrictModel):
    request: str
    request_message_ids: list[str]
    status: Literal["answered", "partial", "unanswered", "next_step", "withdrawn"]
    answer_message_ids: list[str]
    explanation: str
    # Default preserves the ability to read historical v1 evaluation records.
    withdrawal_message_ids: list[str] = Field(default_factory=list)
    support: AnswerSupport | None = None


class ReferenceEvidence(StrictModel):
    reference_id: str
    quote: str


class RuleEvidence(StrictModel):
    criterion_id: str
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
    # Historical records predate explicit contextual counterfactual dependencies.
    fixed_claim_ids: list[str] | None = None


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


class ProofPremise(StrictModel):
    premise_id: str
    # Explicit null in a direct source premise aliases the canonical claim.
    # Conjunctive premises describe their own independently needed propositions.
    proposition: str | None
    evidence: list[Evidence]
    reference_evidence: list[ReferenceEvidence]
    rule_evidence: list[RuleEvidence]
    depends_on_claim_id: str | None
    required_status: Literal["supported", "contradicted"] | None


class ClaimProof(StrictModel):
    relation: Literal["direct", "all_of"]
    premises: list[ProofPremise]
    required_premise_ids: list[str]
    explanation: str


class AssertionGroup(StrictModel):
    group_id: str
    composition: Literal["atomic", "all_of"]
    operator_evidence: list[Evidence]
    claim_ids: list[str]


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
    evidence_kind: Literal["product_fact", "account_state", "grading_rule", "workflow_commitment", "general_fact"] = "product_fact"
    rule_evidence: list[RuleEvidence] = Field(default_factory=list)
    observation_scope: Literal["none", "reported_state", "control_visible", "action_completed", "task_completed", "system_record"] = "none"
    supported_proposition: str | None = None
    verification_scope: Literal["interaction", "policy", "private_record", "grading_rule", "commitment"] = "policy"
    # Customer reports/acknowledgments that do not independently verify the claim.
    # Keep these separate from observation proof in dialogue_evidence.
    context_evidence: list[Evidence] = Field(default_factory=list)
    # Source-contract v3 requires these explicitly; old records remain unchanged.
    claim_id: str | None = None
    assertion_group_id: str | None = None
    proof: ClaimProof | None = None


class Deduction(StrictModel):
    criterion_id: str
    rule_quote: str
    defect: str
    evidence: list[Evidence]
    checked_message_ids: list[str]
    overlap_note: str


class SemanticExclusion(StrictModel):
    evidence: Evidence
    reason: Literal["social", "context_or_confirmation", "observable_commitment", "criterion_behavior", "not_grade_changing"]
    criterion_ids: list[str]
    explanation: str


class SemanticAudit(StrictModel):
    version: Literal["coverage-v1", "coverage-v2", "coverage-v3", "coverage-v4"]
    reviewed_message_ids: list[str]
    exclusions: list[SemanticExclusion]


class SelectedSourceSpan(StrictModel):
    kind: Literal["dialogue", "reference", "rule"]
    source_id: str
    field: str
    role: Literal["client", "operator", "system", "bot"] | None
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class SourceCitationAudit(StrictModel):
    version: Literal["source-spans-v1"]
    catalog_fingerprint: str
    # Bind the new persisted projection to its audit contract. Historical source
    # audits omit this; changing coverage-v4 to v3 cannot bypass group checks.
    projection: Literal["derived-groups-v4"] | None = None
    # JSON pointers into the persisted evaluation, mapped to explicitly selected
    # source spans. Exact quote strings come only from those immutable sources.
    selections: dict[str, str]
    spans: dict[str, SelectedSourceSpan]


class Evaluation(StrictModel):
    judgments: list[Judgment]
    request_coverage: list[RequestCoverage]
    scope_notes: list[str]
    # Defaults allow reading frozen historical results, not omitting new API fields.
    factual_claims: list[FactualClaim] = Field(default_factory=list)
    deductions: list[Deduction] = Field(default_factory=list)
    semantic_audit: SemanticAudit | None = None
    assertion_groups: list[AssertionGroup] | None = None
    source_citations: SourceCitationAudit | None = None


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

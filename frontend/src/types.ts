export type CitationSelection = {source_span_id?: string; source_id?: string;
  source_kind?: 'dialogue'|'reference'|'rule'; source_field?: string; source_start?: number; source_end?: number;
  source_citation_expected?: boolean}
export type HighlightRange = {start: number; end: number; quote: string}
export type Evidence = {message_id: string; quote: string} & CitationSelection
export type OmissionSupport = {start_message_id: string; end_message_id: string; context_evidence: Evidence[]}
export type AnswerSupport = {basis: 'explicit'|'implied'|'next_step'|'none'|'withdrawn'; evidence: Evidence[];
  inference: string|null; unresolved_aspects: string[]; omission?: OmissionSupport|null}
export type RequestCoverage = {request: string; status: string; request_message_ids: string[];
  answer_message_ids: string[]; explanation: string; support?: AnswerSupport|null}
export type ReferenceEvidence = {reference_id: string; quote: string}
export type RuleEvidence = {criterion_id: string; quote: string}
export type ClaimOutcome = {status: 'scored'|'not_applicable'|'needs_review'; answer: string|null}
export type ClaimImpact = {criterion_id: string; when_true: ClaimOutcome; when_false: ClaimOutcome;
  rule_quote: string; evidence: Evidence[]; checked_message_ids: string[]; explanation: string;
  fixed_claim_ids?: string[]|null}
export type ClaimCorrection = {operator_evidence: Evidence[]; outcome_evidence: Evidence[];
  reference_evidence: ReferenceEvidence[]; remaining_consequence: 'none_established'|'present'|'uncertain'; explanation: string}
export type ClaimAssessment = {lifecycle: 'active'|'corrected'; correction: ClaimCorrection|null; impacts: ClaimImpact[]}
export type ProofPremise = {premise_id: string; proposition: string|null; evidence: Evidence[];
  reference_evidence: ReferenceEvidence[]; rule_evidence: RuleEvidence[];
  depends_on_claim_id: string|null; required_status: 'supported'|'contradicted'|null}
export type ClaimProof = {relation: 'direct'|'all_of'; premises: ProofPremise[];
  required_premise_ids: string[]; explanation: string}
export type AssertionGroup = {group_id: string; composition: 'atomic'|'all_of'; operator_evidence: Evidence[]; claim_ids: string[]}
export type SourceSpanLocation = {kind: 'dialogue'|'reference'|'rule'; source_id: string; field: string;
  role: string|null; start: number; end: number}
export type SourceCitationAudit = {version: string; catalog_fingerprint: string; selections: Record<string,string>;
  spans?: Record<string,SourceSpanLocation>}
export type FactualClaim = {claim: string; criterion_ids: string[]; status: string; explanation: string;
  operator_evidence: Evidence[]; dialogue_evidence: Evidence[]; context_evidence?: Evidence[];
  reference_evidence: ReferenceEvidence[]; observation_scope?: string;
  supported_proposition?: string|null; verification_scope?: string; assessment?: ClaimAssessment|null;
  claim_id?: string|null; assertion_group_id?: string|null; proof?: ClaimProof|null}
export type Judgment = {criterion_id: string; status: 'scored'|'not_applicable'|'needs_review'; answer: string|null;
  explanation: string; evidence: Evidence[]; counterevidence: Evidence[]; checked_message_ids: string[]; uncertainty: string|null}
export type Criterion = {id: string; title: string; instruction: string; kind: 'binary'|'scale'|'flag'; weight: number;
  na_condition: string|null; channel_guidance: Record<string,string>; levels: {value: string; fraction: number; description: string}[]}
export type Checklist = {id: string; version: string; title: string; instructions: string[]; criteria: Criterion[]}
export type Reference = {id: string; text: string; provenance: string; source_url?: string; scope?: string;
  valid_from?: string|null; valid_until?: string|null; retrieved_on?: string|null;
  date_basis?: 'policy_validity'|'snapshot'; snapshot_on?: string|null}
export type ReferenceMode = 'conversation_date'|'snapshot_review'
export type ReferenceSelectionContext = {mode: ReferenceMode; scope: string; as_of: string|null; rationale: string;
  pack_id: string; pack_sha256: string}
export type AssessmentContext = {mode: ReferenceMode; conditional: boolean; scope: string|null; as_of: string|null;
  rationale?: string|null; pack_id?: string|null; pack_sha256?: string|null}
export type EvidenceContext = {temporal: {occurred_on: string|null; origin: string; has_conflict: boolean;
  conflict_reason?: string|null; unavailable_reason?: string|null}; assessment: AssessmentContext;
  references: {reference_id: string; usable: boolean; rejection_reasons: string[]}[]}
export type ReferenceOption = {reference: Reference; usable: boolean; rejection_reasons: string[]}
export type ReferencePack = {id: string; scope: string; title?: string; usage_notes?: string[]; references: Reference[]}
export type Conversation = {id: string; channel: string; language: string; messages: {id: string; timestamp: string;
  speaker: string; text: string}[]; references: Reference[]; knowledge_scope?: string|null; occurred_on?: string|null;
  occurred_on_origin?: string|null; reference_context?: ReferenceSelectionContext|null}
export type ConversationRow = {id: string; external_id: string; content_hash: string; created_at: string;
  channel: string; language: string; message_count: number; reference_count: number}
export type ConversationDetail = ConversationRow & {content: Conversation; metadata: {recording_url?: string}}
export type ChecklistRow = {id: string; external_id: string; version: string; content_hash: string; title: string; content: Checklist}
export type Score = {total: number|null; provisional: boolean; flags: Record<string,string>; unresolved_criteria: string[];
  score_bounds: {lower: number|null; upper: number|null}; contributions: {criterion_id: string; status: string; points: number|null}[]}
export type Appeal = {id: string; job_id: string; criterion_id: string; author: string; reason: string; message_ids: string[];
  proposed: {status: Judgment['status']; answer: string|null}|null; status: string; created_at: string;
  resolution: {reviewer: string; rationale: string; revision: number; before: Judgment; after: Judgment; supporting_references?: Reference[];
    assessment_context?: AssessmentContext}|null}
export type JobRow = {id: string; batch_id: string; conversation_id: string; checklist_id: string; status: string;
  review_revision: number; created_at: string; started_at: string|null; finished_at: string|null; retry_of: string|null}
export type JobDetail = JobRow & {conversation: ConversationDetail; checklist: ChecklistRow; appeals: Appeal[];
  evidence_context?: EvidenceContext;
  evidence_context_origin?: 'captured_with_request'|'reconstructed_for_inspection';
  effective: {judgments: Judgment[]; score: Score; source: string; accepted_revisions: number; assessment_context?: AssessmentContext}|null;
  record: {evaluation: {judgments: Judgment[]; scope_notes: string[]; request_coverage: RequestCoverage[];
    factual_claims: FactualClaim[];
    assertion_groups?: AssertionGroup[]|null; source_citations?: SourceCitationAudit|null;
    deductions: {criterion_id: string; rule_quote: string; defect: string; overlap_note: string}[]};
    score: Score; error: string|null; model: string; prompt_version: string; workflow_version: string; response_id: string;
    usage: {estimated_cost_usd: number; input_tokens: number; output_tokens: number}|null;
    attempt_count: number; latency_seconds: number; billing_state?: string; validation_reason?: string;
    repair_skipped?: string; error_detail?: string; budget_required_usd?: number; budget_available_usd?: number;
    assessment_context?: AssessmentContext}|null}
export type Config = {api_key_configured: boolean; model: string; strategy: string;
  default_checklist: {id: string; version: string};
  ledger: {lifetime_committed_usd: number; lifetime_limit_usd: number}}
export type BatchResult = {batch_id: string|null; job_ids: string[]; reused: string[]}

export type Evidence = {message_id: string; quote: string}
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
  record: {evaluation: {judgments: Judgment[]; scope_notes: string[]; request_coverage: {request: string; status: string;
    request_message_ids: string[]; answer_message_ids: string[]; explanation: string}[];
    factual_claims: {claim: string; criterion_ids: string[]; status: string; explanation: string; operator_evidence: Evidence[];
      dialogue_evidence: Evidence[]; reference_evidence: {reference_id: string; quote: string}[]}[];
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

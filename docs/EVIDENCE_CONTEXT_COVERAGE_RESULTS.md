# Evidence context and semantic coverage — 2026-11-07

Implemented from the [existing-results audit](EXISTING_RESULTS_AUDIT.md), with no
paid API tests. This milestone improves source context, claim provenance and
inspectability. It does not measure a live accuracy increase or assign a product
grade. The supplied numeric rubric, legitimate deductions, allowed levels and
single protected repair remain unchanged.

## Source context is preserved instead of guessed

Fresh organizer/API imports and fresh organizer-suite loading now derive a date
only from consistent, complete, timezone-aware ISO timestamps. Original messages,
timestamps and offsets remain intact. Derivation uses each timestamp's source-local
calendar date, not the machine timezone, conversation language or today's date.

- All five supplied calls derive **2026-11-03** with
  `occurred_on_origin=source_iso_timestamps`.
- All60 supplied chats remain undated and unscoped.
- Missing, relative, naive, invalid or mixed blank timestamps prevent automatic
  derivation. Multi-date/midnight disagreement remains ambiguous.
- Supplied dates are not overwritten. Contradictions and unsupported claims of
  derived provenance are exposed as conflicts.
- Import metadata retains the source timestamps/IDs, offsets and derivation reason.
- Historical `Conversation` parsing and frozen `load_cases` stay inert. Old source
  inputs and assessments are not silently rewritten.

New grounded payloads include `evidence_context`: temporal provenance plus each
reference's usability and rejection reasons. Exact scope and validity checks remain;
a derived date cannot authorize a wrong-scope or out-of-window reference. Explicit
date/source conflicts block dated-reference verification and conflicting reference
attachment. Retrieval date does not become an effective policy date.

The cached guides' one-day assessment window has not been widened or represented
as an organizer requirement. Private account records and genuinely missing product
policies have not been invented. Previously imported records may remain undated;
new versioned payloads can report their safe timestamp consensus without altering
the historical source object.

## Grading requirements have a different authority from product truth

Claims now declare an evidence kind and verification scope:

| Evidence kind | What can establish it |
| --- | --- |
| Grading rule | Exact quotation from the selected criterion/rule, with source evidence for its application |
| Product/general fact | Applicable reference for a policy, or a narrowly observed interaction outcome |
| Private account state | Applicable record reference or independent system-record evidence, not customer assertion alone |
| Workflow commitment | The operator's observable offered next step, distinct from proof of backend completion |

An operator's assertion that verification is unnecessary can be assessed against
the actual supplied checklist prerequisite; no second product manual is required
to apply that grading rule. Rule citations must be verbatim, refer to a related
configured criterion and cannot be used to verify fees, eligibility or account facts.

Both supported and contradicted policy/private-state claims need appropriate
evidence. A customer's report cannot prove either that a private restriction exists
or that it does not. Customer evidence can still establish a specific failed route
in that interaction without proving a general policy false.

Observation scope is explicit: reported state, visible control, completed action,
completed task or system record. A claim supported only by a narrow observation
must state exactly the proposition being supported; it cannot carry a separate
broader verified proposition. The validator checks declared scope and consistency,
not whether natural-language evidence truly entails the claim.

## Every relevant source message receives a disposition

New grounded output requires `semantic_audit` version `coverage-v1`:

- Every customer/operator message must appear exactly once in the reviewed list.
  Bot/system events remain full context and evidence; they are not graded as human
  operator behavior.
- Every customer message belongs to a canonical request or an explicit exclusion.
- Every operator message belongs to a canonical claim/correction or an explicit
  exclusion. Merely citing it as an answer does not exempt its assertions from review.
- Exclusions retain an exact source quote, reason and explanation. Substantive
  exclusions must link to configured criteria and judgments actually reviewing that
  source. They may describe a commitment or grade-independent conduct without
  claiming product truth is verified.
- Existing deduction audits still apply. An exclusion does not cancel a deduction,
  remove a serious flag, or override conditional claim outcomes.

This makes the formerly invisible decision to skip a statement reviewable. It is
**not a certificate of semantic completeness**: one message can contain several
clauses, and a model can still misclassify a material clause as incidental. No
conversation-ID rules, prepared answers, language-specific detectors or audit
reference labels are loaded by the evaluator.

## Answer coverage exposes inference and remaining questions

Each request now includes explicit support:

- Basis: explicit, implied, next step, none or withdrawn.
- Exact response/withdrawal evidence with the correct source role and linked span.
- An inference explanation for implied answers.
- Remaining unresolved aspects; `answered` cannot retain any and `partial` must
  identify them.

The prompt distinguishes an answer that entails the requested conclusion from a
positive statement about one option that says nothing about alternatives. This
does not implement a hardcoded English-language rule or prove all implications
correct. The evidence and inference remain available for review in saved/exported
records. A concrete appropriate next step remains valid without requiring eventual
backend completion; customer thanks does not withdraw an unanswered request.

## Strict transport and compatibility

New grounded requests use `evaluator-v5-*` and record
`claim_contract_version=evidence-coverage-v1`. The provider schema requires the
new semantic audit, request support and evidence-class fields. The decoder rejects
their omission instead of silently falling back to historical defaults. Defaults
exist only for reading historical records and are removed from the strict wire
schema. Existing quote, rule, role, reference, correction-order, allowed-level,
N/A, dependency and deduction validators remain mandatory.

Historical outputs retain the previous validation path when the new semantic
audit is absent. Old saved records are not given fabricated exclusions or support.
The experimental direct/evidence-first paths keep their previous output contracts.
The standard model, output-token cap and retry count have not been increased.

## Local evidence and limits

**212 tests passed; Ruff passed.** Meaningful controls include:

- Explicit dates, source offsets, midnight/mixed/blank timestamps, forged derivation,
  conflicting reference attachment and missing-scope/expired-source rejection.
- Supplied grading-rule evidence preserving a verification deduction and serious
  flag without another product policy; fake rules cannot establish product truth.
- Uncovered source messages, fake/foreign-role exclusions, absent answer support,
  answered-with-unresolved contradiction and unsupported implied answers rejected.
- Visible controls cannot be promoted to policy truth; customer assertions cannot
  establish private state in either direction.
- Corrected advice remains compatible with strict historical-error criteria and
  real deductions; an appropriate next step does not require completed execution.
- The mocked provider/repair boundary accepts a fully validated new-contract fixture,
  retains rejected output and costs, and does not substitute scores.

An independent offline verification script checked all65 fresh imports and their
schemas, then revalidated all65 latest available historical assessments against
their frozen source and exact numeric arithmetic. Their scores and source hashes
remain unchanged. This is compatibility verification, not 65 new model evaluations.

**Provider acceptance and live output quality were not tested**, as requested. The
additional source accounting can increase output length, especially on noisy calls;
the existing token cap may need a later measured check. New fields being mandatory
can reject an incomplete model response. No relaxed validator, offline fallback,
automatic extra grader or hidden unlimited retry was added to conceal that risk.
Do not describe passing local tests as improved expert agreement or proven coverage.

## Cost and reproduction

No new model requests were made. Read-only ledger checks before/after show the same
548 entries, latest call548 and settled-cost sum $19.694328. Incremental API cost:
**$0**. Temporary unit-test ledgers are separate and use mocked responses.

```powershell
uv run pytest -q
uv run python -m scripts.verify_evidence_coverage_offline
```

The private report is
`artifacts/evidence-coverage-v1/offline-verification.json`. It explicitly records
that provider-schema acceptance and live model quality remain untested. The
original benchmark, labels, audit source files and submitted results are unchanged.

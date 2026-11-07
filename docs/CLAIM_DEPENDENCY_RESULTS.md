# Claim dependencies and corrected advice — 2026-11-07

The grounded evaluator now represents a factual assertion's relationship to a
criterion separately from whether the grade depends on that assertion's truth.
It also records later corrections and their remaining consequences. The numeric
rubric, weights, allowed levels, reviewed-015 interpretations and repair allowance
are unchanged. There is no offline scoring fallback.

## What changed

Every newly generated factual claim requires an `assessment`:

- `lifecycle`: active or corrected. The original assertion and original truth
  status remain intact after a correction.
- `correction`: a later operator statement, independent customer/system outcome
  evidence or an applicable reference, and an assessment of remaining consequences.
  An unsupported operator self-correction is insufficient to establish recovery.
- `impacts`: one entry for each related criterion, with conditional allowed
  outcomes `when_true` and `when_false`, its exact rule quotation, source evidence
  or checked span, and an explanation.

For an unverified claim, different conditional outcomes require that criterion to
remain `needs_review`. Identical definite outcomes allow a grade independently
established by the evidence. For supported/contradicted claims, a scored judgment
must match the established conditional outcome. Other unresolved evidence may
still require review. Grade-changing claims must be marked material.

This does not equate any independently established defect with a determinate score.
For example, an unanswered question can establish an omission while the truth of
a key recommendation still distinguishes consultation 5 from 0. That uncertainty
must remain. Conversely, a premature private disclosure can be a definite security
violation regardless of whether the disclosed account fact is true.

Correction does not automatically grant full credit. A criterion about successful
final guidance can credit independently evidenced recovery; a criterion explicitly
penalizing any historical error still fails. Harmful consequences, actual unclear
instructions and independently established security failures remain assessable.

Provider schemas now constrain original-assertion citations to operators and
independent dialogue/outcome citations to customer/system messages. Nonexistent
references cannot be emitted in claim reference arrays when none were supplied.
Runtime quotation, role, temporal-order, source scope/date, rule and deduction
validators remain enforced. The schema change prevents a repeated structural error
rather than accepting operator self-verification.

Historical records with no assessment retain their original conservative validation
semantics. New grounded responses cannot omit or null the assessment to opt into
legacy validation. The evaluator workflow is now versioned `evaluator-v4-*`, with
`claim_contract_version=dependencies-v1`; exact request/schema fingerprints and core
source hashes remain in the saved records. Direct/evidence-first experimental
contracts are unchanged.

## Frozen paired baseline and focused candidate

Twelve fictional cases in six contrasts were frozen before implementation. They
cover private disclosure with unknown versus supported factual content, wrong
navigation with and without recovery, correction with avoided versus incurred
harm, unknown versus contradicted timing guarantees, Kazakh unclear instructions
with and without recovery, and two custom checklist treatments of historical
errors. Expectations are assistant-authored provisional labels, not expert GT.

The full old-evaluator paired baseline completed 10/12 cases and matched 22/26
declared judgments. Its two correction-related failures were preserved. It also
produced one management disagreement; no expected label was changed to hide it.

To limit spending, the candidate used six of those cases plus the four original
organizer failures. The other six synthetic cases and the four additional saved
organizer controls were not rerun under the candidate. This is a focused regression
check, not a new full-suite accuracy or repeatability measurement.

| Matched six-case synthetic subset | Before | After |
| --- | ---: | ---: |
| Valid assessments | 4/6 | 6/6 |
| Declared judgment agreement, including failures | 7/10 | 10/10 |

The successful controls explicitly retained:

- Consultation 0 after harmful key advice, despite a later correction.
- Custom outcome criterion pass after successful correction, but custom historical
  error criterion failure on the same dialogue.
- Management 4 after the customer had to clarify vague Kazakh instructions, despite
  eventual task success and consultation 20.
- Consultation review when an unsupported exact timing guarantee could change its
  allowed outcome; missing documentation was not converted into a confident pass.

## Four organizer failures

Original inputs, original partial expectations and original failed outputs remain
unchanged. None of these four cases has a frozen complete expert reference vector.

| Case | New assessment | Retained findings and limits |
| --- | --- | --- |
| `p1-ru-018` | Valid, consultation provisional | NeedsNo is independent of diagnosis truth. Unsupported exchange diagnosis can distinguish 5 from 0, so no final total is invented. Management10; seriousNo. |
| `p1-kz-005` | Valid, 92.31 | Initial wrong route is recorded as contradicted and corrected; customer confirms finding the requested destination. Consultation20, management10, closingNo. |
| `p1-en-014` | Valid, 58.82 | IdentityNo, seriousYes, consultation10 and closingNo remain. The missing follow-up answer is not forgiven. |
| `p4-ru-003` | Valid, closing provisional | Superseded profile-processing assertion no longer blocks the trading-order investigation/callback assessment. NeedsNo, identityYes and consultation20 remain; closing opportunity is unresolved. |

All four now have valid assessments, but only two have final numeric totals.
The recovered organizer coverage is not evidence of four perfectly correct scores.

Two judgments differ from the old rejected drafts and remain important to review:

- EN014 empathyNo became Yes. The new explanation treats the verification challenge
  and unanswered follow-up as neutral task/security issues under R014 rather than
  an explicit dissatisfaction cue; whether “we can skip that” is independently
  dismissive remains a semantic review question. The security violations remain.
- The call's management4 became 10. The new explanation treats the garbled OTP
  exchange as insufficient to establish a wording defect. This could be sensible
  ASR handling, but it is not independently adjudicated and is not claimed as a
  measured accuracy improvement.

EN014 returned no factual-claim entries: its explanation treats the waiver as
observable security conduct rather than a separate grade-changing factual
question. Source existence and dependency validation do not prove extraction
completeness. That limitation also remains visible.

## Preserved unsuccessful candidate and recovery

The first candidate report contains seven completed assessments, one exhausted
role-validation failure (`p1-ru-018`), and two budget deferrals with no API request.
The failed Russian repair again put an operator admission into independent factual
proof. Validation correctly rejected it. The provider schema was then constrained
by speaker role and that one case was explicitly rechecked under the changed
schema; its prior paid failure remains in the record.

The two deferred controls were subsequently submitted once, sequentially after
the earlier reservations were released. The follow-up budget was $0.77, keeping
the candidate's aggregate declared allowance below the announced $1.50 cap.
No successful case was repeated or selected for a more favorable score. No full
65-case rerun or repeated-run stability claim is included.

## Cost and verification

| Batch | Estimated uncached cost |
| --- | ---: |
| Twelve-case old-evaluator baseline | $0.737220 |
| First focused candidate, including rejected outputs | $0.720648 |
| Role-constrained recheck and two unsubmitted controls | $0.233228 |
| **Total** | **$1.691096** |

Candidate validation alone cost $0.953876. All billable attempts are retained;
costs reconcile to ledger call IDs; unknown-cost attempts: zero. Protected repair
reservations can defer a concurrent case even while actual settled spending is
below the batch cap. Those deferrals incurred no model charge.

Ruff passed. **133 tests passed**, including historical compatibility, mandatory
new assessments, allowed conditional levels, illegal N/A rejection, incomplete
impact rejection, missing audits, fake citations, wrong source roles, premature
corrections, unsupported self-correction, and wrong-scope/expired recovery sources.
All selected successful model outputs were revalidated against their original
sources and exact scoring arithmetic without further API calls.

Mechanical checks establish structure, references and internal consistency. They
do not prove that a quoted passage entails a claim, that conditional reasoning is
correct, or that the assistant's provisional labels match organizer experts.
Missing policy references, noisy call interpretation, empathy boundaries and
corpus-wide coverage remain unfinished. These results do not justify a 95–100 claim.

## Artifacts and reproduction

- `evals/claim-dependencies-v1.jsonl`: public-safe fictional cases and frozen labels.
- `artifacts/claim-dependencies-v1/protocol.json`: pre-change experiment protocol.
- `paired-baseline.json`, `focused-candidate.json`, `role-constrained.json` and their
  `.suite.jsonl` snapshots: immutable model outputs and inputs.
- `report.json`: source-identity checks, all three batches, original-draft changes,
  provisional-label comparison and reconciled spending.

Regenerate the comparison without model calls:

```powershell
uv run python -m scripts.report_claim_dependencies
```

The saved 65-case benchmark remains the old frozen baseline; its 34 numeric,
27 provisional and four failed outcomes have not been retroactively replaced.

# Deduction-audit and repair reliability — 2026-11-07

## Outcome

The missing binary-deduction audit is now structurally prevented in grounded
provider requests. The existing source/rule validators remain mandatory. The
first attempt and one mechanical repair are protected by an atomic ledger hold
before a paid request starts. This fixes the observed output-delivery boundary;
it does not establish general accuracy or semantic repeatability.

The original failed browser record is unchanged. Its fresh CLI reevaluation and
subsequent browser reevaluation both completed, matching all five previously
declared judgments. The browser now displays 64.71 with a justified identity
deduction and separate serious-error flag. That is a conversation score, not a
grade for the product.

## Implementation

- The provider's `judgments` object requires one key per configured criterion.
  Each allowed lower-than-maximum numeric answer, including a binary failing
  answer, requires a non-null deduction audit in its own judgment. Maximum
  answers, flags, N/A and review statuses require null. Custom answer names work.
- The transport is normalized to the historical persisted `Evaluation` shape.
  It copies model-supplied audits; it never fabricates an audit or a score.
- Rule quotations, original message quotations, source scope/date, allowed
  answers, applicability, coverage, and factual-support checks still run. Duplicate
  audits for one criterion are additionally rejected. Missing-audit errors identify
  the criterion. Strict structure does not establish semantic correctness.
- The ledger atomically reserves an envelope for one attempt plus one repair.
  Individual submitted calls consume the envelope; unused allowance is released.
  Other concurrent work cannot take the protected repair allowance.
- Repair feedback has a 24,000-byte JSON-encoded bound, including escaping. A
  large prior candidate may be explicitly truncated; the original full transcript
  remains in the repair input and the full rejected candidate stays in the record.
- Attempts remain bounded at two per stage. An invalid second answer still fails;
  no offline result, relaxed validation or hidden unlimited retry was added.
- Restart recovery releases only unspent holds for interrupted application batches.
  Submitted calls with unknown usage keep their conservative reservation; unrelated
  CLI reservations are not cleared.
- The UI default allowance is $1.00 and failed preflight displays the required
  conservative allowance and available amount. Validation reasons and skipped
  repair reasons are visible without an export. This was functional error handling,
  not a visual redesign.

The dynamic nested `anyOf` contract uses the supported subset documented in
[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
Actual calls accepted this schema. Semantic/source validation remains our own
separate responsibility.

## Frozen fresh checks

`evals/reliability-v2.jsonl` was saved before inference. Expected labels and test
metadata were excluded by the existing explicit input allowlist. The original
failure is a separate regression, not a new case.

| New case | Focus | Valid completion | Frozen agreement |
| --- | --- | --- | --- |
| 51 RU | Protected disclosure before verification; unanswered follow-up | First attempt | 5/5 |
| 52 RU | Matched source with verification before disclosure | First attempt | 5/5 |
| 53 EN | Bot greeting cannot satisfy human contact; closing opportunity | First attempt | 6/6 |
| 54 KZ call | Internal farewell followed by a proper customer closing | First attempt | 8/8 |
| 55 EN | Independently contradicted instructions | First attempt | 4/5 |
| 56 RU | Exact tariff claim without an independent source | First attempt, provisional | 3/4 |
| 57 EN custom | Missing keyboard activation; custom binary failing answer | First attempt | 1/1 |
| 58 EN custom | Explicit keyboard activation | First attempt | 1/1 |

**8/8 fresh conversations completed on their first attempts; 33/35 (94.29%)
matched the frozen provisional expectations.** No automatic repair was needed.
Three completely labelled fresh configurations had numeric totals with MAE 0:
one eight-criterion call and two simple custom-criterion cases. This is a tiny
assistant-authored set, not an independent accuracy benchmark.

The two frozen disagreements were closing labels in cases 55 and 56. The author
incorrectly expected a bare farewell to satisfy the configured requirement. The
model correctly cited the absence of a summary or further-help offer. This is a
post-run label review, not independent adjudication: the frozen labels and 33/35
headline are unchanged. The evaluator was not changed to match these labels.

The original case-41 failure regression separately matched 5/5 declared judgments.
All 65 organizer records were checked for protected context-size feasibility
without model calls; the largest input bound plus repair allowance was below
the existing 200,000 bound.

## Organizer data and actual application

- `p1-ru-007` again completed at 84.62; the late withdrawal-retry question remained
  uncovered. No organizer reference score is available.
- `p1-ru-028` again completed with provisional consultation because the relevant
  product-route claim has no independently applicable source in the original
  input. The model did not turn customer acknowledgment into policy verification.
- The user's open `p4-ru-001` call was retried through the browser. It completed
  with provisional consultation, citing absent sources for consequential manager
  eligibility/service-policy claims. It did not pretend to assess audio qualities.
  These three organizer records are unlabelled and earn no invented accuracy rate.
- An intentionally insufficient $0.20 allowance for the old Russian test was
  rejected with **zero API attempts**. The UI reported $0.4809 required for the
  protected path. A subsequent $1.00 retry completed for an actual estimated
  $0.057834, with the identity audit, source links and old failure preserved.
- A separate **real repair replay** sent the historical rejected candidate and
  validation feedback to OpenAI under the new contract. It completed with identity
  and consultation audits. Its initial failure is historical; this is not a new
  first-pass case or a naturally occurring automatic repair in the fresh batch.

## Remaining weakness found by repeated requests

Two designated fresh cases were repeated with identical request fingerprints.
**14/16 complete-vector judgments stayed unchanged (87.5%).** The bot/human case
retained all eight judgments and 76.92. The Russian case 51 changed:

| Criterion | First run | Repeat |
| --- | --- | --- |
| Empathy | yes | no |
| Management | 7 | 10 |
| Conversation score | 59.41 | 47.06 |

The score drift is **12.35 points**. The repeated runs still matched the five
predeclared partial labels; reporting only partial-label agreement would conceal
this instability.

The empathy outputs disagree about whether the late factual follow-up expresses
a separate inconvenience. The management outputs disagree about treating the
explicit verification-order violation as a sequencing defect. Current R013
explicitly permits independently evidenced prerequisite sequencing deductions;
simply suppressing every overlap would contradict the configured rule.

These are semantic boundary/stability issues, not missing-audit failures. They
were not hidden, replaced by favorable reruns, or solved by loosening validation.
The next core milestone should settle those particular boundaries and test
independent counterexamples, while preserving legitimate overlapping violations.
This review does not claim 95-100 accuracy or a new product grade.

## Verification and cost

- **93 pytest tests passed**, including the preserved actual rejected draft,
  schema-level audit coverage, source-rule rejection, full two-attempt accounting,
  budget competition, no-charge preflight, bounded feedback, cancellation, and
  restart recovery with unknown submitted costs retained.
- Ruff and diff whitespace checks passed; TypeScript and Vite build passed.
- **16 paid API requests produced 16 valid assessments:** 15 ordinary evaluation
  requests and one historical repair replay. No automatic repair was needed in
  the ordinary live checks. Unit tests injected invalid responses only in isolated
  tests to verify the automatic two-attempt path and its failure modes.
- Of those 16 assessments, 13 had numeric totals and three were appropriately
  provisional. Valid completion is not synonymous with having a numeric score.
- Unspent protected allowance after all live work: **$0**.

| Phase | Estimated USD |
| --- | ---: |
| Eight new cases + one original-failure regression | 0.384550 |
| Two organizer chats via CLI | 0.110744 |
| Organizer call through browser | 0.078196 |
| Original-failure retry through browser | 0.057834 |
| Two identical-input repeats | 0.102788 |
| One real historical repair replay | 0.064178 |
| Total new spending | **0.798290** |

These are conservative ledger estimates, not a live provider billing statement.
The user authorized lifting the previous spending restriction. The ignored local
lifetime ceiling was increased by $5 of headroom to $14.302438; $0.798290 was used,
moving commitment from $9.302438 to $10.100728. No key was printed or committed.

Raw reports, source snapshots, downloaded browser exports, repair replay and
screenshots remain in ignored `artifacts/reliability-v2/`. Recompute the combined
report without model calls, using a new output filename:

```powershell
uv run python -m scripts.report_reliability_v2 --output artifacts/reliability-v2/summary-copy.json
```

The earlier [browser review](BROWSER_ACCEPTANCE_REVIEW.md) and its failures remain
unchanged. Passing this narrower delivery milestone does not erase that history
or the new repeat-consistency concern.

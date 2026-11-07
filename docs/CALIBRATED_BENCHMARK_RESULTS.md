# Updated-rubric benchmark — 2026-11-07

Status: the 117-case updated-rubric run, 24-case same-input control, and three
targeted empathy diagnostics are complete. No further paid calls were made.

## Scope and protocol

Model: `gpt-6.1-sol`, medium reasoning, 6,000 maximum output tokens. All inference
used the real API. Updated checklist: `1-reviewed-012`. No offline result or
prepared-score substitution was used.

The frozen suite contains 40 original authored cases, 12 authored review cases,
and all 65 organizer conversations. Two authored cases deliberately use arbitrary
custom checklists; the other 115 use the updated eight-criterion checklist.
All five real call recordings are assessed through their supplied transcripts;
audio was not analyzed. The authored set also contains fictional call transcripts.

The reference overlay includes our 20 review dispositions, preserving their
different provenance. Original labels are retained elsewhere, including known
disputes. There are 213 declared reference decisions, of which two are explicitly
unscored needs-review dispositions. The 211 determinate references remain
AI-authored or assisted, not independent expert labels or organizer Ground Truth.

Cases, references, checklist, selection and historical comparison were frozen
before the new run. Expectations, case names that indicate diagnostic intent,
and the review journal do not enter inference. The old raw results and datasets
are unchanged. These are development/calibration cases already inspected; none
is described as an independent unseen holdout.

Private evidence: ignored `artifacts/benchmark/calibrated-v3/`. The suite file
SHA256 is `10aceb3f245d14baa3dd27fee9cd9ad180b226907967905e0a10ae4b327b0b3e`.

## Updated-rubric results

| Measure | Observed result |
| --- | ---: |
| Completed, mechanically validated evaluations | 117 / 117 |
| API attempts | 118 |
| Bounded validation repairs | 1 |
| Determinate provisional references matched | 203 / 211 = 96.2% |
| Authored references matched | 176 / 182 = 96.7% |
| Organizer references matched | 27 / 29 = 93.1% |
| User-accepted determinate reference judgments matched | 12 / 12 |
| Derived accepted-policy judgments matched | 2 / 2 |
| Assistant-only determinate call assessments matched | 2 / 4 |
| Explicitly uncertain reference dispositions matched | 2 / 2, separate from scored agreement |
| High-impact determinate identity/serious references matched | 38 / 39 |
| Mean total-score absolute error on 17 full authored reference vectors | 2.59 points |
| Numeric totals across all cases | 97 / 117 |
| Numeric totals on organizer cases | 58 / 65 |
| Estimated updated-rubric run cost | $3.438734 |

Passing mechanical validation checks allowable values, reference IDs, and literal
quote correctness. It does not prove that the evidence entails the judgment.
The single repair was EN-009: a request was marked answered without an operator
reference. The real repair call supplied only the mechanical error and rejected
output, never expected labels; both attempts and their costs are retained.

The two organizer disagreements are the provisional identity and closing labels
for call RU-002. The new model treats the early exchange as generic troubleshooting
before protected review, and the later restriction statement as a recap before
the customer-facing farewell. Those are plausible alternatives to the assistant's
provisional labels. Do not tune them to match a weak reference just to raise a rate.

Only 29 of the organizer's 520 criterion judgments have determinate provisional
references here. No organizer conversation has a full independently reviewed
reference vector. Therefore organizer total-score error is not measurable, and
96.2% development agreement is not competition accuracy or a 96/100 product grade.

## The coverage tradeoff

20 totals remain provisional. Nineteen concern closing opportunity; one concerns
the corrupted human self-introduction. Thirteen of these are authored cases,
often short diagnostic fragments lacking an end state. Seven are organizer cases:

- KZ-008: source ends after customer confirmation, with no subsequent operator
  reply or end-state event.
- RU-012, KZ-011 and EN-009: external connection loss after the customer's final
  message; opportunity to close is not established under the accepted policy.
- Calls RU-003 and RU-004: customer termination/overlapping ending leaves closing
  opportunity uncertain.
- Call RU-005: first human introduction is corrupted; audio was unavailable.

The earlier historical coverage phase had 64 numeric organizer totals out of 65.
The new 58/65 is a real cost of the stricter uncertainty policy. Keep this visible;
do not silently exclude hard cases or replace them with confident invented grades.
This is the main product-readiness issue exposed by this run.

## Historical comparison on the same frozen references

The initial historical attempts are regraded against exactly the same current
reference decisions, retaining the five old structural failures. They match
191/211 = 90.5%, versus 203/211 = 96.2% now. Historical full-vector MAE is 3.24,
versus 2.59 now.

This comparison changes prompt/validation history as well as rubric and contains
structural failures already fixed before calibration. It must not be used to
attribute the full difference to the new checklist. The separately run same-model,
same-prompt control below is a cleaner, still-small comparison.

## Disagreements and reference quality

All eight disagreements remain in the report. They include the four review-v2
boundaries (username workaround, repeated filename question, empathy overlap,
missing-ticker sequencing), the two provisional call RU-002 decisions, and two
original authored expectations:

- `auth-en-secondary-detail`: the customer explicitly withdrew the filename
  question, but the original reference still expects a deduction.
- `auth-ru-empathy-absent`: the operator opens a technical ticket for the exact
  stated issue without an explicit emotional phrase. Our adopted policy permits
  this as implicit acknowledgment, so the old No expectation conflicts with it.

These observations do not retroactively change frozen labels or make the model
automatically correct. They show why model-authored references need independent
adjudication and why an apparently high rate is not proof of judge alignment.

## Cleaner same-input control: mixed, not uniformly improved

The original checklist and updated checklist were evaluated on exactly the same
24 pilot cases and frozen references, with the same model, system prompt, medium
reasoning, output-token limit, and evaluator source. The suite hash and these
settings were checked. The original control used concurrency one; updated inference
used concurrency two. This is one sample per variant/case, not a stability study.

| Measure on the same 24 cases | Original checklist | Updated checklist |
| --- | ---: | ---: |
| Valid outputs | 24 / 24 | 24 / 24 |
| Determinate provisional references matched | 100 / 110 = 90.9% | 104 / 110 = 94.5% |
| Full-reference MAE on nine authored vectors | 3.96 points | 4.90 points |
| Numeric totals | 23 / 24 | 21 / 24 |
| Estimated cost | $0.637790 | $0.758832 |

Criterion agreement improves, but synthetic aggregate-score error and numeric
coverage worsen. Do not declare the updated rubric unconditionally more accurate.
The score error depends on disputed synthetic references and weighting; no full
organizer reference vectors are available to settle the actual competition effect.
The observed agreement improvement is mainly alignment with the team's explicit
interpretations, not proof those interpretations match hidden organizer Ground Truth.

Budget-management note: the first control segment overlapped the main run. The
shared conservative budget guard deferred 16 cases before an API attempt, after
eight completed. Those 16 were then run sequentially; the merge replaces only
unattempted budget skips and rejects repeated actual attempts. No failed or completed
result was replaced with a more favorable sample. Aggregate control spending remained
below its $0.75 ceiling. The original component reports remain intact.

## Targeted diagnostic: relevant action versus generic politeness

Three fictional Notifications-crash cases were frozen before inference, after
noticing the old empathy-label conflict. This is a targeted development diagnostic,
not a blind or independent holdout. Inputs and expected labels are in
`evals/empathy-contrast-v1.jsonl`; no production fallback uses these responses.

| Operator response | Empathy | Consultation |
| --- | --- | --- |
| Opens a ticket specifically for the reported Notifications crash, without an emotional phrase | Yes | 20 |
| Politely gives unrelated bond-navigation instructions | No | 0 |
| Says "I understand your frustration" but gives the same unrelated instructions | No | 0 |

All six declared checks matched in three real evaluations. Cost: **$0.069224**.
This demonstrates the intended distinction in these cases, not universal robustness.

## Spending and verified end state

| Phase | Evaluations | API attempts | Estimated new cost |
| --- | ---: | ---: | ---: |
| Updated rubric: complete frozen suite | 117 | 118 | $3.438734 |
| Original-rubric same-input control | 24 | 24 | $0.637790 |
| Targeted empathy contrast | 3 | 3 | $0.069224 |
| Total new work | 144 | 145 | $4.145748 |

Unused from the authorized $6: **$1.854252**. Overall recorded estimated cost,
including all earlier development: **$7.573490**. The existing ledger has 282
completed and six rejected attempts, no outstanding reservations or unknown-cost
entries. Costs use configured published token rates, conservatively charging input
as uncached; these are not billing-invoice or account-balance measurements.

The new run used no prepared result substitution. The two custom-checklist tests
passed. Spot checks of the RU/KZ/EN unverified-account-disclosure scenarios all
returned identification No and serious Yes. These latter spot checks are qualitative
observations, not newly invented benchmark reference labels.

26 tests, Ruff, Git whitespace checks, reference-source checks, and same-input
control settings checks passed. Private raw data, API responses, credentials,
usage state, and frozen organizer suites remain ignored by Git.

## What this establishes and what it does not

We have a measured evaluator that applies the saved rules and distinguishes several
important semantic cases. We have not established a 95-100 competition score or
organizer-level accuracy. The strongest measured limitations are the loss of numeric
coverage under the closing-uncertainty policy, unresolved reference quality, lack
of independent unseen evaluation, and unimplemented application workflow.

Do not consume more API credit merely to optimize the same labels. The next product
work should expose actual evidence, versioned evaluations, uncertainty, and reviewer
decisions in the working application. Any change to uncertainty handling or grading
policy must remain explicit and be compared without rewriting these results.

## Reproduction

`scripts/prepare_calibrated_benchmark.py` constructs the frozen suite and a
historical comparison without API calls. Outputs are never overwritten.
`scripts/report_calibrated_benchmark.py` separates determinate reference agreement
from uncertainty and keeps provenance groups visible. Tests ensure failed
predictions remain in the denominator and uncertain references do not inflate it.

The user authorized $6 of new spending. The existing ledger was retained and the
local lifetime ceiling became $9.427742 (previous $3.427742 plus $6). New model
calls are subject to both run reservations and the global cap. No key or private
organizer transcript is committed.

`scripts/merge_benchmark_segments.py` combines budget-deferred-only continuations
without choosing the best result per case. All controls and candidate outputs use
the same frozen references; uncertain reference dispositions are excluded from
determinate agreement and reported separately. Reproduce the complete updated
comparison from its retained outputs with a new destination filename:

```powershell
uv run python -m scripts.report_calibrated_benchmark artifacts/benchmark/calibrated-v3/pilot-results.json artifacts/benchmark/calibrated-v3/remaining-results.json --output artifacts/benchmark/calibrated-v3/new-comparison.json
```

That report command is offline analysis of paid outputs and incurs no API cost.

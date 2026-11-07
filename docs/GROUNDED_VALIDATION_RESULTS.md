# Grounded evaluator validation and default, 2026-11-07

The default is now the single-call **grounded** evaluator with checklist
`1-reviewed-013`. The legacy evaluator remains available through `--strategy direct`
and an explicitly selected older checklist. There is no offline fallback or
automatic second grader.

The organizer's latest clarification, supplied in chat, changes the stopping
criterion: reasonable, explained, reproducible judgments matter more than exact
agreement with every expert point. Missing facts must not be invented, and the
complete evaluation/review workflow also matters. We are closing this focused
core experiment rather than tuning repeatedly against provisional labels.

## Completed live checks

| Check | Measured result |
| --- | --- |
| Nine frozen overlap/source cases | 15/15 declared reference judgments matched after quota continuation |
| Direct baseline on those cases | 13/15 matched |
| Three identical-input overlap repeats | 24/24 judgments unchanged; all three totals unchanged |
| Wrong-advice, verification-order, and two custom-checklist regressions | 12/12 declared judgments matched |
| Full-vector regression subset | Three cases, score MAE 0 |
| Original organizer transcripts | Two evaluated; no declared reference labels, so no accuracy percentage |

These are small development checks against provisional expectations. They do not
establish organizer Ground Truth accuracy or a 95–100 competition score. The
source/overlap pack has no full reference score vectors, so it has no score MAE.
The repeat check used identical request hashes, not just identical case IDs.

The old 6.93-point drift was not reproduced in the tested late-question scenario.
One repeat per scenario is encouraging evidence, not a stability guarantee.
Genuine independent management/empathy defects still receive deductions alongside
consultation failures; the implementation does not mechanically remove overlaps.

## Organizer observations and remaining factual limitation

`p1-ru-007` received 84.62. The customer confirms finding the update form, but the
operator leaves the withdrawal-retry question unanswered. Navigation success
does not prove a withdrawal deadline or eligibility rule.

`p1-ru-028` remains provisional for consultation. The customer confirms seeing the
menu item; the operator's additional statement that it is the correct procedure
for updating questionnaire data lacks an applicable independent source in the
original input. The system records one supported observed outcome and one
unverified material assertion. It does not turn thanks into policy verification.

This is **reduced numeric coverage**, not a newly demonstrated wrong answer.
The official reference bundle contains relevant current guidance, but these
original inputs do not declare its platform/date scope. We did not invent their
dates or silently attach a differently scoped source. A reviewer can supply the
appropriate context/reference and reassess; until then the uncertainty stays visible.

The organizer clarification explicitly accepts reasonable handling of incomplete
data. Consequently, the promotion decision is based on the targeted behavioral
checks and honest uncertainty handling, not a requirement that both organizer
examples always receive point totals. The machine report separately records
`organizer_all_numeric=false`. It does not count the unlabelled examples as correct
against nonexistent references or hide the coverage tradeoff.

## Preserved failures and costs

The original interrupted candidate report is unchanged: six completed cases,
two provider credit rejections, and one unattempted budget deferral. Only those
three cases were continued. Successful semantic judgments were not replaced by
better repeated results. Reconciled zero-cost provider rejections and matching
request fingerprints are checked before accepting a continuation.

Two new calls needed the existing bounded mechanical repair: one invalid reference
quote and one wrong-role audit citation. Both original rejected outputs and their
costs are preserved. There were no remaining failures in the resumed checks.

Estimated costs, using the existing conservative usage ledger:

- After the user's top-up: **$0.413488**, 12 completed evaluations and 14 inference
  attempts including the two mechanical repairs.
- Entire grounding/boundary phase, including its previous baseline and partial
  run: **$0.810034**.
- Lifetime ledger commitment: **$9.166096** of the authorized $9.427742 limit;
  **$0.261646** remains under that limit. This is not a live account-balance reading.

The grounded nine-case run cost $0.296498 versus $0.215374 for the legacy baseline,
about 38% more on this small pack. Extra claim/rule evidence has an actual output
cost; it is not free. No additional paid checks were run after the organizer's
latest clarification. The contemplated extra default-path smoke inputs were
prepared but not run, and are not counted as validation results.

## Reproducibility and implementation status

Private raw outputs, snapshots, quota reconciliation, the frozen resume plan, and
`final-report.json` remain in `artifacts/benchmark/targeted-v5/`. Recreate the report
without model calls, using a fresh output filename:

```powershell
uv run python -m scripts.report_grounded_validation --output artifacts/benchmark/targeted-v5/report-copy.json
```

Ruff passed and **62 tests passed**, including default entry-point selection,
source and rule validation, preserved failed attempts, and repeat comparisons.
The explicit grounded API requests already tested are unchanged by promoting
that same strategy to the default. No paid default smoke run was claimed.

The core milestone is complete with documented limits. Next implementation
priority: import a new conversation, select/version a checklist and reference
context, evaluate through the real API, persist the exact result, inspect cited
evidence, and resolve an appeal while retaining the original assessment. Interface
and full-workflow tests remain necessary; these backend checks do not substitute
for them. Avoid further attempts to guess the undisclosed scoring formula.

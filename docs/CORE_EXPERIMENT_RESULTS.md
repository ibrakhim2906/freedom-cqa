# Core experiment results, 2026-11-07

The direct evaluator remains the default. Separating factual observation from
grading produced no measured accuracy gain on the frozen anchors and nearly
doubled API cost. The useful shipped improvement is deterministic score bounds
for unresolved judgments. There is no claim of 95–100 organizer accuracy.

## Real API results

All runs used gpt-6.1-sol, medium reasoning, the same frozen reviewed-012 checklist,
and original conversations plus any explicitly supplied fictional reference facts.
Diagnostic case IDs and expected labels were excluded from inference.

| Run | Conversations | Declared judgments matched | Full reference score vectors / MAE | API cost |
| --- | ---: | ---: | ---: | ---: |
| Direct baseline | 8 | 31/31 | 5 / 0 | $0.158394 |
| Evidence-first candidate | 8 | 31/31 | 5 / 0 | $0.315236 |
| Direct identical-input repeat | 8 | 31/31 | 5 / 0 | $0.157704 |
| Direct additional stress pack | 6 | 13/13 | 1 / 0 | $0.151238 |

There are **14 unique fresh conversations and 44 declared reference judgments**,
not 30 independent test conversations. Repeated evaluations are separate cost
and stability observations. Only six unique conversations have full reference
score vectors. The other cases deliberately test selected criteria without
pretending disputed cross-criterion effects have a definitive answer.

The anchor pack tests wrong versus supported advice, confirmation before versus
after confidential disclosure, Kazakh bot/human attribution, a late request, and
two configurations of an arbitrary incident-follow-up criterion. The stress pack
adds a Russian call, an internal farewell followed by an explicit customer hangup,
a refused private paid offer, bot/client quoted misconduct, a transcript instruction
attack, and an explicit withdrawal. All expected labels were frozen before their
pack's inference. They are AI-authored provisional labels, not independent expert
ratings or organizer Ground Truth. These short explicit cases are easier than
several noisy organizer calls.

## What the repeated run actually found

The repeat used the same eight actual inference request fingerprints, not merely
the same filenames. Across **all 50 emitted judgments**, including those without
declared references, **49/50 stayed unchanged (98%)**. Numeric totals stayed
unchanged in seven of eight conversations.

In `core-late-timezone`, management moved from 10 to 7, shifting the total from
84.62 to 77.69. Both outputs scored consultation 10 and identified the unanswered
timezone request. The second output additionally treated immediate closing after
that request as an independent sequencing lapse. That management judgment had
intentionally not been given a supposedly definitive reference label.

Consequently, zero MAE on the five fully labeled anchor cases does **not** show
that every total is stable. This single 6.93-point drift is a material limitation.
One repeat per case cannot establish population-level stability. No result was
replaced by a more favorable repeated answer, averaged, or silently corrected.

## Candidate keep/reject decision

The evidence-first candidate emits generic per-criterion source observations in
one API call, validates their quotes and IDs, then grades using the complete
original transcript, references, checklist and fallible observations in another.
It supports custom criteria, preserves every billable attempt, and fails visibly
if either stage cannot complete. Source matching validates quotation existence,
not semantic entailment; the extraction is not an independent truth source.

It changed **none of the 50 judgments** relative to the direct baseline. Its
observed p95 case latency was 27.035 seconds versus 14.366 for direct grading,
and its cost was 1.99 times higher. That supplies no reason to promote it. It is
retained only as an explicitly experimental CLI strategy, `--strategy evidence-first`.
There is no automatic extra grading stage in the default path.

No direct prompt or rubric was changed to force agreement with the disputed old
labels. See [the source audit](CORE_ERROR_AUDIT.md): the eight prior disagreements
do not yet identify a definite grader error that a prompt patch can safely fix.

## Shipped core changes

- Every new score contains an allowed-outcome envelope. Unresolved numeric
  criteria still produce `total=null`; N/A is included only where the configured
  criterion permits it. Flags remain separate. These are not confidence intervals.
- Bounds are generic across arbitrary weights and level fractions. Small arbitrary
  rubrics were checked against exhaustive allowed assignments, including zero
  weights and cases where no numeric denominator exists.
- All seven provisional organizer results were locally recalculated with bounds
  while preserving their original judgments and unresolved totals. No extra model
  calls or edits to the preserved 117-case benchmark were needed.
- The experimental two-stage workflow validates source references and accounts
  for extraction, grading, repair, failure, and budget exhaustion explicitly.
- A reproducible report checks actual-request identity for repeated runs and
  retains every changed judgment and score drift.

Ruff passed and **40 tests passed**, including custom-checklist evaluation,
fabricated-source rejection, stage failure without fallback, paid-attempt
accounting, uncertainty bounds, and invalid repeat comparisons.

## Cost and reproducibility

This batch cost **$0.782572** across 38 paid attempts and 30 conversation
evaluations. Lifetime ledger commitment is **$8.356062** against the authorized
local limit of $9.427742, leaving **$1.071680** under that limit. This is ledger
accounting, not a live reading of the OpenAI account balance. No usage was reset.

The stress run initially completed five cases and deferred its last case because
the conservative maximum-token reservation slightly exceeded that run's $0.25
ceiling. Only that never-attempted case was continued for $0.024784. Both segment
reports are preserved. Their source hashes differ after a bookkeeping fix to the
experimental evidence-first budget-failure path; the direct prompt, schema,
validation and scorer were unchanged between those two segments.

Frozen private outputs are in `artifacts/benchmark/core-v4/`, including
`direct-baseline.json`, `evidence-first.json`, `direct-repeat.json`,
`direct-stress.json`, `direct-stress-continuation.json`, and `final-report.json`.
The public-safe fictional inputs are in `evals/core-anchors-v4.jsonl` and
`evals/core-stress-v4.jsonl`. Never overwrite prior outputs.

Reproduce the report without paid calls, choosing a new output filename:

```powershell
uv run python -m scripts.report_core_experiment --output artifacts/benchmark/core-v4/report-copy.json
```

## Remaining accuracy gaps

The core has passed these behavioral checks, but this does not establish a
95–100 solution. The measured weakness is discretion at the management/consultation
boundary, with a significant possible aggregate-score effect. Further progress
requires a defensible rule for the boundary, corroborated by contrasting source
examples, rather than another clause that forces one desired answer.

Independent full-vector labels for organizer-like cases are still missing.
Product-policy claims need trustworthy reference material for the relevant
product and entity. Seven organizer totals remain provisional, and ambiguous
call openings/endings still need reliable audio or end-state evidence. The new
bounds expose those limitations; they do not resolve them. No frontend work was
undertaken in this core experiment.

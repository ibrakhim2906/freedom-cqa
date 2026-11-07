# Accuracy-first delivery plan

2026-11-07. Target: an excellent completed submission by 2026-11-08 12:00 Astana.
95-100 is an internal ambition, not a prediction of the organizers' score.
The user explicitly prioritizes assessment quality before product polish.

## Starting evidence

Keep the working evaluator and scorer. The latest frozen run covers 117 cases,
including every organizer transcript. Local provisional-label agreement is 96.2%,
but the cleaner 24-case comparison is mixed: criterion agreement improves while
synthetic aggregate-score error and numeric coverage worsen. No full independent
organizer reference vectors exist. See CALIBRATED_BENCHMARK_RESULTS.md.

Do not start over, keep adding case-specific clauses, relabel a test after seeing
the result, or add multiple graders merely to obtain agreement. Preserve all
current datasets, rules, outputs, and spending history as the comparison baseline.

## 1. Verify the errors before changing the grader

Review the eight disagreements and seven provisional organizer totals as one
batch, without another sequence of user confirmation requests. Classify each as
a supported model mistake, a weak/disputed reference, an interpretation choice,
or missing source evidence. Retain source IDs and counterevidence.

Where a reference is demonstrably wrong, record a new reference version separately;
score both the baseline and candidate against that same version. Do not describe
an improvement from correcting labels as an improvement to the model itself.
Keep assistant-only adjudication distinct from independent expert review.

Deliverable: short error ledger identifying what we can actually fix and how to
detect whether the fix works. This is analysis of existing outputs, not a paid rerun.

## 2. Strengthen the core validation pack

Create a small frozen set of complete conversations with full criterion vectors
and explicit policy facts where correctness depends on them. Include RU/KZ/EN,
call-like turn structure, late questions, identity ordering, bot context, internal
consultation, private offers, and true irrelevant-response negatives. Group related
variants; reserve fresh scenario families before implementing a candidate.

Use explicit checklist constraints and known facts for unambiguous anchors. Put
genuinely disputed judgments in a separate, reported category instead of pretending
they are ground truth. Report the size and provenance of both categories. This
pack strengthens behavioral validation but cannot become organizer Ground Truth
merely because we wrote it or because two models agree.

## 3. Run one focused improvement experiment

First test the current evaluator on reserved cases and repeat selected inputs
without changing settings. Change the implementation only where an actual failure
justifies it. One candidate worth testing separates source-linked factual
observations from criterion grading, while giving the grading pass the entire
original conversation as well as the observations. It must support arbitrary
configured criteria, not only the initial eight.

The observation stage is fallible and must not replace source context. Keep the
existing single-pass grader if the alternative does not improve the measured
errors enough to justify cost and latency. Do not average conflicting scores or
retry semantic judgments until the desired answer appears.

Promotion gate:

- No regression on verified identification, confidentiality, and serious-offer anchors.
- Better error on the predeclared target cases without an increased score MAE on
  full determinate vectors; aim for <=2 points on the strengthened set.
- At least 95% criterion agreement with credible reserved reference decisions.
- At least 95% stability on designated identical-input repeated runs.
- All fully assessable cases get valid numeric results; genuine uncertainty and
  failure rates remain visible and count against coverage.

Small samples are diagnostics, not statistically established guarantees. A failure
to improve means retain the baseline and report the result, not widen the experiment
indefinitely. The core experiment is time-boxed; target a keep/reject decision by
18:30 Astana on 2026-11-07, adjusting transparently if actual work requires it.

## 4. Address source evidence and uncertainty

Try the authorized audio playback route for the provided calls, concentrating on
the corrupted opening and ambiguous call segments. Do not infer diction or pace
from text. Keep product claims grounded in supplied or verified authoritative
materials with the correct entity, product, jurisdiction, and date. Operator/bot
assertions are not independent product documentation.

Treat closing uncertainty as one documented policy issue, not six unrelated patches.
Preserve the user-approved needs-review handling unless explicitly revised. Add
transparent score bounds where useful; bounds are not a secretly chosen point
grade and do not prove better Ground Truth accuracy. Resolve missing evidence
where possible, and expose residual limitations rather than force Yes/No/N/A.

## 5. Complete the application after the core decision

Protect the rest of the development window for the required product. First build
one complete path: import a fresh conversation, choose a saved checklist, run the
real evaluator, persist its exact result, and inspect source evidence. Then add
checklist editing/versioning, batch progress and failures, saved-result reuse,
audio playback, and appeals preserving original and reviewed assessments with
deterministic score recalculation. Keep implementation aligned with the selected
React/TypeScript and FastAPI/SQLite stack.

Targets: first vertical slice on 2026-11-07 evening; complete required workflow
overnight; end-to-end verification on 2026-11-08 morning. These are planned
milestones, not claims of completed work. Avoid optional analytics or decoration
that consumes time needed for the required evaluation/review workflow.

## 6. Final acceptance and freeze

Exercise new unseen-by-the-demo input, arbitrary criterion creation, RU/KZ/EN,
calls, N/A normalization, a serious flag, visible API failure, saved-result reuse,
and an appeal. Verify against the displayed result, not merely backend tests.
Rerun the small frozen validation pack after integration; do not tune against a
reserved set after seeing its results. Preserve model, checklist, prompt and
source versions in the final report.

Target code/submission freeze: 2026-11-08 11:00 Astana, leaving an hour before the
deadline. Claims in the demo must distinguish measured local agreement, provisional
references, actual organizer Ground Truth, and unimplemented or unavailable features.

## Budget and remaining limits

Remaining authorized model budget at planning: $1.854252. Plan at most $1 for the
focused core experiment, keeping the rest for repeat checks and final live-path
verification. Use the existing lifetime ledger; do not reset usage. No paid call
was made to prepare this plan. Larger comparisons require additional available
budget; more spending alone cannot establish the missing reference truth.

Independent domain-reviewed reference decisions remain the strongest missing
accuracy evidence. If they cannot be obtained, report the limitation and substantiate
the behavioral tests we can actually perform. The goal is a reliable demonstrable
product, not an unsupported 95-100 claim.

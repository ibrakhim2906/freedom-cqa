# Progress

## Setup

- [x] Read the supplied case documents.
- [x] Verify access to the 65-conversation DEV dataset.
- [x] Inspect the previous hackathon implementation and reproduce generic-reply behavior.
- [x] Create the project directory and initial documentation.
- [x] Create the private GitHub repository: https://github.com/ibrakhim2906/freedom-cqa.
- [ ] Confirm desktop browser and computer-use access with a minimal local page.

## Define the evaluation contract

- [x] Obtain and review the official checklist, including weights, scales, N/A, rounding, and the separate serious-error flag.
- [x] Select and document the frontend, backend, storage, and OpenAI API provider in STACK.md.
- [x] Record the explicit runtime requirement: no offline evaluation fallback.
- [x] Record the organizer's top-50 selection criteria and 10-transcript Ground Truth control stage in JUDGING.md.
- [x] Inspect all 65 DEV transcripts and record data-specific risks in DATA_AUDIT.md.
- [x] Record the organizer's call adaptation and flexible-checklist clarification in EVALUATION_DESIGN.md.
- [ ] Review and agree on the proposed evaluation design and independent test strategy.
- [ ] Select the exact OpenAI model using varied RU, KZ, and EN development cases.
- [x] Implement the initial configurable evaluator and scorer with no offline fallback.
- [x] Author 40 fictional diagnostic cases with explicitly provisional expected judgments.
- [x] Keep all 65 organizer records available and select 15 representative cases for the first combined benchmark.
- [x] Verify the real OpenAI structured-output path with one temporal-identification smoke case.
- [x] Run the first real combined benchmark (40 authored + 15 organizer cases), preserving failures and disagreements.
- [x] Record results and reference-label issues in BASELINE_RESULTS.md and REFERENCE_REVIEW.md.
- [x] Constrain source IDs in the response schema and add one explicitly recorded validation repair; recheck five rejected cases.
- [x] Obtain validated evaluations for all 65 organizer transcripts across the original and follow-up runs; preserve one provisional total.
- [x] Record the initial coverage phase in BENCHMARK_RUN_SUMMARY.md ($2.688466 estimated usage).
- [x] Review organizer judgment evidence and distinguish ambiguous labels from evaluator errors in SEMANTIC_REVIEW.md.
- [x] Freeze 12 new paired development cases and compare v1/v2 through the real API without rewriting original expectations.
- [x] Add explicit customer withdrawal evidence and missing-information dependency guidance; preserve two genuine-omission organizer controls.
- [x] Record that original-rubric RU/KZ N/A inconsistency remains; provide a separately marked scope-clarification draft rather than silently changing official wording.
- [x] Complete the 20-item calibration review, distinguishing user-accepted, derived, and assistant-only assessments; keep two items unscored for specific uncertainty.
- [x] Save accepted interpretations in immutable checklist versions; retain original checklist and benchmark outputs.
- [x] Define an explicit internal product grading rubric without claiming an organizer score or new measured accuracy.
- [x] Freeze and run 117 updated-rubric cases (52 authored + all 65 organizer conversations), preserving label provenance and original results.
- [x] Run a same-input original-checklist control on 24 cases and report mixed outcomes: better provisional-label agreement, worse synthetic score MAE and numeric coverage.
- [x] Validate three fresh targeted empathy contrasts through the real API; preserve remaining uncertainty rather than claim independent Ground Truth accuracy.
- [x] Record new benchmark spending ($4.145748 of the authorized $6) and limitations in CALIBRATED_BENCHMARK_RESULTS.md.
- [ ] Define checklist versions, transcript message IDs, evaluation results, and appeal records.
- [x] Define how missing reference procedures and unavailable audio affect judgments; retain unresolved evidence explicitly.
- [x] Freeze fresh source/overlap cases before inference and preserve prior labels and outputs.
- [x] Add generic score bounds, scoped source citations, material factual uncertainty and rule-linked deduction audits.
- [x] Finish grounded validation: 15/15 targeted judgments, 12/12 regression judgments, and 24/24 unchanged repeated judgments on three inputs.
- [x] Inspect two original organizer outputs; preserve the additional provisional consultation instead of claiming full numeric coverage.
- [x] Promote the single-call grounded evaluator and reviewed-013; keep legacy mode explicitly available.
- [x] Record the organizer clarification favoring justified, reproducible results and a complete working process over exact hidden-label matching.

## Prove evaluation behavior

- [ ] Complete one criterion from input through its final displayed explanation and evidence.
- [ ] Check equivalent paraphrases produce equivalent judgments.
- [ ] Check relevant evidence removal or speaker changes affect the appropriate judgment.
- [ ] Check irrelevant changes do not alter unrelated judgments.
- [x] Apply a new criterion through configuration without changing evaluation code (two real API cases).
- [x] Verify weighted calculations independently of model judgments.
- [x] Measure initial provisional-label agreement, source-reference validity, language/channel results, latency, and cost.
- [ ] Independently review criterion labels and semantic evidence support before claiming Ground Truth accuracy.

## Complete the product workflow

- [x] Import conversations and preserve source timestamps and speaker roles; all 65 organizer records imported into the app.
- [x] Create and save immutable checklist versions through the interface; a new criterion was evaluated through the real API from the UI.
- [x] Run real evaluations with visible progress, per-batch budgets, failures, retries and queued cancellation.
- [x] Open supporting source messages, counterevidence and reference quotes from criterion results.
- [ ] Play timestamp-aligned audio fragments inside the workspace; original recording links are available, audio remains unanalyzed.
- [x] Submit an appeal and record a reviewer's accepted/rejected decision and supporting references.
- [x] Preserve original and final results and deterministically recalculate scores after review.
- [x] Persist results and distinguish saved results from new evaluations; browser reload and actual server restart were checked.
- [x] Verify the browser's real evaluation/evidence/appeal/custom-checklist flow and a visible budget failure; no offline fallback.

## Prepare submission

- [x] Document reproducible local installation and startup in WORKFLOW.md and scripts/start-local.ps1.
- [ ] Verify the complete browser workflow on the final code.
- [ ] Demonstrate RU, KZ, and EN cases, N/A handling, an appeal, and a live criterion change.
- [ ] Process the control dataset when the organizers release it.
- [ ] Prepare the public submission repository and freeze the submission commit.

## Decisions still open

- Broader model comparisons are not complete; the tested default remains gpt-6.1-sol at medium reasoning.
- The user subsequently authorized continued API work without the old spending restriction. At the boundary-validation milestone, ledger commitment is $13.581918 and the ignored local ceiling is $19.302438. These are local accounting figures, not a live provider balance; never reset usage.
- Broader product-reference coverage and source context for undated organizer inputs remain incomplete. Three scoped official platform guides are available.
- The exact organizer comparison formula is not supplied; the organizer explicitly discourages guessing it.
- Verified audio playback/access and optional audio-analysis scope.
- Browser/computer-use behavior: the availability check stalled; WSL compatibility was not established.

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
- [ ] Define checklist versions, transcript message IDs, evaluation results, and appeal records.
- [ ] Define how missing reference procedures and unavailable audio affect judgments.
- [ ] Select a varied development subset and reserve fresh cases for checking changes.

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

- [ ] Import conversations and preserve source timestamps and speaker roles.
- [ ] Create and save checklists through the interface.
- [ ] Run evaluations with visible progress, failures, and retries.
- [ ] Open supporting messages and audio fragments from criterion results.
- [ ] Submit an appeal and record a reviewer's decision.
- [ ] Preserve original and final results and recalculate scores after review.
- [ ] Persist results and distinguish saved results from new evaluations.

## Prepare submission

- [ ] Document reproducible installation and startup.
- [ ] Verify the complete browser workflow on the final code.
- [ ] Demonstrate RU, KZ, and EN cases, N/A handling, an appeal, and a live criterion change.
- [ ] Process the control dataset when the organizers release it.
- [ ] Prepare the public submission repository and freeze the submission commit.

## Decisions still open

- Final OpenAI model selection; initial Sol access and the $3.50 local lifetime cap are configured.
- Supporting company procedures/reference sources and exact organizer comparison metric (not supplied).
- Verified audio playback/access and optional audio-analysis scope.
- Browser/computer-use behavior: the availability check stalled; WSL compatibility was not established.

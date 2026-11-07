# Progress

## Setup

- [x] Read the supplied case documents.
- [x] Verify access to the 65-conversation DEV dataset.
- [x] Inspect the previous hackathon implementation and reproduce generic-reply behavior.
- [x] Create the project directory and initial documentation.
- [x] Create the private GitHub repository: https://github.com/ibrakhim2906/freedom-cqa.
- [ ] Confirm desktop browser and computer-use access with a minimal local page.

## Define the evaluation contract

- [ ] Obtain the separate official checklist, including weights, scales, N/A, rounding, and serious-error rules.
- [ ] Discuss and select the frontend, backend, storage, and model provider.
- [ ] Define checklist versions, transcript message IDs, evaluation results, and appeal records.
- [ ] Define how missing reference procedures and unavailable audio affect judgments.
- [ ] Select a varied development subset and reserve fresh cases for checking changes.

## Prove evaluation behavior

- [ ] Complete one criterion from input through its final displayed explanation and evidence.
- [ ] Check equivalent paraphrases produce equivalent judgments.
- [ ] Check relevant evidence removal or speaker changes affect the appropriate judgment.
- [ ] Check irrelevant changes do not alter unrelated judgments.
- [ ] Apply a new criterion through configuration without changing evaluation code.
- [ ] Verify weighted calculations independently of model judgments.
- [ ] Measure criterion agreement, evidence support, language performance, latency, and cost.

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

- Application stack and model provider.
- The official checklist and any required supporting company procedures.
- Audio analysis requirements once the actual criteria are available.
- Browser/computer-use behavior: the availability check stalled; WSL compatibility was not established.

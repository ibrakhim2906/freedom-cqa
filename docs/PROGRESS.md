# Progress

Latest implementation milestone: [evidence context and semantic coverage](EVIDENCE_CONTEXT_COVERAGE_RESULTS.md).
Fresh source-date derivation, rule-versus-product evidence, explicit answer support
and source dispositions are implemented. 212 local tests pass; all65 saved scores
remain unchanged. No paid API tests were run; live accuracy/coverage is unmeasured.

Latest analysis milestone: [offline audit of existing results](EXISTING_RESULTS_AUDIT.md)
and [missing-facts inventory](MISSING_FACTS_INVENTORY.md). All65 transcripts and the
four organizer PDFs were reviewed with $0 new API spending. Source/representation
gaps, genuine missing facts, interpretation candidates and supported controls are
separate; no saved evaluation, label or runtime behavior changed. See also
[lessons from the previous hackathon](PREVIOUS_HACKATHON_LESSONS.md).

Latest focused core work: [claim dependencies and corrected advice](CLAIM_DEPENDENCY_RESULTS.md).
Four original organizer failures now have valid assessments (two still provisional);
the focused synthetic subset matches 10/10 provisional labels. All first outcomes
and costs are retained. The earlier full-run [65-case audit](ORGANIZER_65_REVIEW.md)
is unchanged; no new corpus-wide accuracy claim is made.

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
- [x] Separate positive answer evidence, omission intervals and claim observation metadata under evidence contract v2; preserve frozen expectations and prior results. Offline checks: 340 tests, seven mocked browser checks, 71 schemas and 65 unchanged historical scores. Model behavior was untested at this offline milestone; see EVIDENCE_CONTRACT_V2.md.
- [x] Run the unchanged frozen six-case suite once through v7: six first-pass valid results, 48/48 provisional pairs, no repairs, $0.3560597 reconciled token cost. Complete assessments reviewed; compound-claim granularity and fresh/repeated robustness checks remain open. See EVIDENCE_CONTRACT_V2_LIVE_RESULTS.md.
- [x] Implement source-span selections, one canonical observation proposition and atomic claim/proof dependencies in the full grounded workflow. Preserve rubric arithmetic, legitimate deductions, historical validation and frozen expectations. Offline verification: 560 tests, 18 intercepted browser checks, all 79 input/schema pairs within unchanged bounds, 110 unchanged labels/12 complete vectors, and 97 historical scores unchanged. $0 API spending; v8 live behavior remains untested. See SOURCE_SPANS_AND_ATOMIC_PROOFS.md.
- [x] Run three isolated manual diagnostics using an organizer call and two original negative paired cases, with expectations frozen and hidden from execution agents. One output passes strict validation with a qualified sequencing audit; two are rejected for group-source coverage and observation/proof mismatch. No rejected result is promoted, no ordinal ambiguity is relabeled, no runtime change is made, and API spending is $0. This is not a production API benchmark. See MANUAL_DIAGNOSTICS_V2.md.
- [x] Implement explicit span-v4/coverage-v4: derive exact group source unions from canonical atoms, couple observation/proof schema branches, and clarify claimed-action sequencing without promoting client reports into private truth. Verify 637 tests, all 79 current input bounds and unchanged historical schemas/scores. Rerun C/D/E on explicitly requested Sol6.1medium: two initial outputs valid, organizer valid after one separately recorded post-hoc repair with unchanged judgments. Preserve E's proof-scope qualification and C's reference ambiguities; $0 API spending. See SOURCE_CONTRACT_V4.md and MANUAL_DIAGNOSTICS_V3.md.
- [x] Implement span-v5/coverage-v5: derive exact judgment review unions from explicit source relations and require full time/action/route scope for negative proofs. Verify 703 tests, 82 protected requests, all 79 historical v3/v4 schema/payload pairs, 97 historical API scores, original 110 labels/12 vectors and ten previous manual receipts. Freeze three targeted scope contrasts separately before inference; do not claim untouched holdout accuracy. See SOURCE_CONTRACT_V5.md.
- [x] Run six frozen manual cases on explicitly requested Sol6.1medium with one submission each and no repairs. Five pass strict validation; F remains rejected for observation classification. C review links and E broader-opening status improve; G retains a wrong prerequisite counterfactual and E retains actor/route qualifications. Independent full reviews and every failure are preserved. No API calls or grade increase. See MANUAL_DIAGNOSTICS_V4.md.
- [x] Build an isolated native lean evaluator without proof DAGs/counterfactual branch pairs. Freeze six new multilingual cases and 47 exact labels/five vectors before inference; keep the corrected-advice ordinal unscored. Run 12 cold Sol6.1medium submissions and three independent paired reviews, no repairs/API. Lean passes 1/6 versus current 3/6; compact output is 35.65% smaller but the reliability gate fails. Keep current default and preserve all rejected payloads, reference ambiguity and provenance caveat. See LEAN_EVALUATOR.md and LEAN_EVALUATOR_COMPARISON_RESULTS.md.

## Prepare submission

- [x] Freeze and run eight fresh cases three times with unchanged engine, including mixed-truth claims, positive observations and corrected advice. Reliability gate failed: 18/24 first-pass,22/24 final valid, five repairs, two retained failures, 6/8 stable vectors; $1.7116115 token-priced cost. See FRESH_REPEAT_V1_RESULTS.md before claiming robustness.

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

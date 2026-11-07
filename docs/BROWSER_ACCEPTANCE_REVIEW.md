# Browser acceptance review — 2026-11-07

The existing Codex in-app browser at localhost was exercised through the UI. No
application implementation, prompt, validator, expected label, or budget cap was
changed during the review. Four genuine inference requests used three newly
written fictional conversations. The two English requests used the same source
conversation with different immutable checklist versions.

The conversations and provisional expectations were frozen in
`evals/browser-acceptance-v1.json` before inference. Only its `conversations` array
was uploaded; expected answers were not provided to the evaluator. These are
assistant-authored acceptance checks, not independent expert or organizer labels.
All 65 organizer conversations remained in the application; they were not rerun
or assigned invented reference scores in this review.

## Fresh observations

| Case | Test | Delivered result | Frozen expectation | Outcome |
| --- | --- | --- | --- | --- |
| 41, Russian chat | Confidential disclosure before system verification; late unanswered question | No assessment; validation failure | Five partial judgments declared | Failed, 0/5 delivered |
| 42, Kazakh call transcript | Internal colleague farewell; withdrawn request; actual customer closing absent | 92.31, all eight judgments | 92.31, same eight judgments | Passed, 8/8 |
| 43, English chat, checklist v1 | Keyboard navigation AND activation | complete, 100 | complete, 100 | Passed, 1/1 |
| 43, same source, checklist v2 | Direct shortcut required; Tab then Enter is half credit | workaround, 50 | workaround, 50 | Passed, 1/1 |

Completion: **3/4 evaluations**. End-to-end declared judgment delivery/agreement:
**10/15 (66.7%)**, counting failed determinate predictions as incorrect. Among
completed evaluations alone, 10/10 matched, but that excludes the failed case and
is not the primary success claim. The three completely labelled evaluation
configurations produced numeric scores with MAE 0 against these provisional
references. Two configurations share one simple source conversation. Case 41 has
partial labels and is excluded from whole-score MAE; its failure remains visible.
This tiny, authored sample does not establish general Ground Truth accuracy or a
25% production failure rate.

## Concrete failure

Job `90eb8819-7664-40c7-a97a-84a884ff8b17` cost $0.043168 and failed with:

> Every numeric deduction requires a source-linked rule audit

The rejected draft contained the expected five substantive decisions. Its deduction
audit covered consultation but omitted the weighted binary identity deduction.
The original draft is preserved as rejected diagnostic data, not counted as a
successful evaluation. Repair was skipped with `budget_limit`; the ordinary
$0.20 batch allowance could not reserve the larger repair request. Neither the
budget cap nor the validation requirement was weakened to obtain a passing result.
The UI exposed `invalid_evaluation_ValueError`, cost and explicit billable retry,
but the useful validation reason and repair-budget explanation required exporting
the record. The reviewer paid without receiving a usable assessment.

## Workflow observations

- Fresh file import worked; 69 conversations are now available, including the 65
  original organizer records and the earlier workflow test.
- A genuinely new scale criterion was created in the UI. Editing it as immutable
  version 2 changed the actual model result from 100 to 50 as expected. The old
  result retained its version and score.
- Evidence selection highlighted the exact source quotation. The Kazakh result
  distinguished internal speech, a withdrawn request and a real closing opportunity.
  It explicitly declined to assess absent audio qualities.
- A fictional appeal claimed the internal farewell should count. Rejecting it with
  a source-based rationale persisted before/after judgments, reviewer and reason.
  The exported original AI score and effective score remained equal, source
  `ai_original`, accepted revisions 0, review revision 1.
- Reloading the English version-2 result restored the saved 50 score without a
  new inference. Saved failed records also reopened with their failure intact.
- Accepting an appeal and recalculating a score was demonstrated in the prior
  workflow walkthrough, not newly repeated here.
- Calls currently have transcript assessment and external original-audio links;
  integrated audio playback/seeking is missing. Conversation search/filtering is
  missing; browsing 69 records is cumbersome. Reviewer names are self-reported,
  without authenticated roles; this remains a single-process local prototype.
- The old queued notice can remain visible after completion, although the batch
  completion and selected-job states are accurate. Failure recovery needs a more
  useful explanation than a validation exception label.

## Grade against the frozen internal rubric

**47/100 demonstrated readiness**, not a forecast of the organizer's decision.
The strict rubric withholds substantial unverified accuracy points. The product
has meaningful working analysis and review features; those do not certify its
accuracy on unseen organizer Ground Truth.

| Category | Awarded | Reason |
| --- | ---: | --- |
| Accuracy | 12/60 | 0/25 score-validation points: only tiny assistant-authored full-vector sets, no credibly independent reference set. 0/20 fresh criterion points: 66.7% end-to-end is below the frozen 80% floor. 12/15 discretionary high-impact partial credit uses previous verification/factual regressions and today's legitimate-conduct handling; the fresh positive disclosure case failed to deliver an assessment. |
| Robustness | 13/15 | 3/5 language/call/role delivery after today's Russian failure; 5/5 controlled-change development evidence including changed rules; 5/5 previous 24/24 identical-input judgments. These are small development checks, not broad generalization proof. |
| Functionality | 14/15 | Import/jobs, runtime checklist versions, source navigation, prior accepted appeals/recalculation, fresh rejected appeals and persisted failures/results work. Withhold one point for missing integrated call playback. |
| Usability | 3/5 | Complete basic review journey; opaque failure recovery, long unfiltered list and stale queued notice reduce clarity. |
| Authenticity and traceability | 5/5 | Fresh source and changed rules reached genuine model calls; snapshots, versions, evidence, usage and rejected output are preserved. |

Only criterion agreement and score-error thresholds have preset numerical cutoffs;
other partial allocations above are reviewer judgment. The high-impact and repeat
credit explicitly includes earlier documented development evidence in
`docs/GROUNDED_VALIDATION_RESULTS.md`; this review did not spend money repeating it.
Previous stress/regression checks are not pooled into the fresh primary criterion
rate to conceal today's failed predictions. The unverified 25 points are withheld,
not an assertion that measured score MAE is bad. A larger independent set could
change this readiness assessment in either direction.

## Next work in priority order

1. Make the generated audit complete for every score-reducing criterion, including
   binary failures. Add the observed rejected payload as a regression for the
   generation/validation boundary; retain strict source requirements.
2. Make budget preflight account for the explicitly bounded repair path, or clearly
   state that the chosen allowance funds only one attempt. Never silently increase
   spending or invent an offline result. Explain validation and budget failures in
   the UI with an explicit, estimated-cost retry action.
3. Verify the repair with the preserved failure, then a separately frozen fresh
   batch covering both privacy violations and legitimate conduct. Keep first-pass
   and after-repair completion separate; do not replace this run in its report.
4. Obtain independent review of a reserved reference set and measure adequate
   full-vector coverage. Assistant-authored examples alone cannot certify 95-100.
5. Add call playback and conversation filtering after the reliability defect.

A wholesale architectural rewrite is not supported by this test. The concrete
blocker is reliable delivery of validated assessments under the configured budget.

## Cost and artifacts

| Request | Estimated API cost USD |
| --- | ---: |
| Russian failed evaluation | 0.043168 |
| Kazakh evaluation | 0.037156 |
| English checklist v1 | 0.010518 |
| English checklist v2 | 0.011844 |
| Total | **0.102686** |

These are the existing ledger's conservative cost estimates, not a live OpenAI
billing statement. Lifetime commitment moves from $9.199752 to $9.302438 against
the unchanged authorized $9.427742 cap, leaving $0.125304 of local authorization.
No paid retries were used to replace the failure. Appeal handling, exports and
saved-result reloads made no model calls.

Private downloaded exports, machine-readable aggregates, canonical upload and
screenshots are under ignored `artifacts/browser-acceptance-v1/`. Browser job IDs:

- Case 41: `90eb8819-7664-40c7-a97a-84a884ff8b17`
- Case 42: `77bd52aa-ebc4-42ae-92f0-a043b3f49954`
- Case 43 v1: `25b501b4-fffa-41db-88a7-82007b5a8e6e`
- Case 43 v2: `5b482f27-e6cd-4f70-8f68-48ced476130e`

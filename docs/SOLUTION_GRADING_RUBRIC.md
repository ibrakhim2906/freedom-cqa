# Internal solution grading rubric — 100 points

This grades our submitted product, not an operator's conversation. It is a proposed
internal rubric, not the organizer's numerical formula. The organizer supplied
selection priorities but no weights: accuracy is primary, followed by functionality,
usability, process correctness, and architectural diversity in the selected cohort.
See [the original announcement](JUDGING.md).

Freeze this assessment scheme before the next comparison. Do not change thresholds
or select the most favorable run after observing results. No current overall score
is assigned: too much evidence is missing to support one.

| Category | Points | Evidence required for full credit |
| --- | ---: | --- |
| Accuracy against reference judgments | 60 | Low total-score error, high criterion agreement, and correct high-impact identification/serious-error judgments on a frozen, credibly reviewed evaluation set. |
| Robustness and consistency | 15 | Appropriate behavior across languages, noisy calls, bot/internal roles, changed evidence, paraphrases, and repeated runs. |
| Complete required functionality | 15 | Import and evaluation jobs; editable versioned checklists; source evidence and call playback; appeals and recalculation; persistence and visible failures. |
| Usability | 5 | A reviewer can complete the workflow clearly, with readable evidence and visible progress, saved-result provenance, and errors. |
| Authentic analysis and traceability | 5 | New inputs and changed criteria actually reach the model; source links, versions and attempts are preserved; no prepared-score substitution. |
| Total | 100 | All categories require observable evidence, not a design promise. |

## Accuracy: 60

These thresholds are internal ambitions, not achieved metrics or the organizer's
Ground Truth comparison formula.

### Final-score error: 25

Use mean absolute error on the normalized 0-100 score, on cases with complete
reference vectors. Never infer whole-score accuracy from partial labels.

| Mean absolute error | Points |
| --- | ---: |
| At most 2 points | 25 |
| Above 2 and at most 5 | 18 |
| Above 5 and at most 10 | 8 |
| Above 10 | 0 |

Report failures, provisional totals and numeric-output coverage separately. Full
credit requires a valid numeric output for every case with a determinate reference;
do not compute an attractive MAE only over easy completed cases and hide the rest.
An incomplete evidence base remains unverified rather than earning full credit.

### Criterion decisions: 20

Compare the exact status and allowed answer, including No versus N/A and discrete
scale levels. For determinate references, failed or unresolved predictions do not
count as correct. Report reference ambiguities separately; do not label them model
successes merely because both sides are uncertain.

| Exact agreement | Points |
| --- | ---: |
| At least 95% | 20 |
| At least 90%, below 95% | 15 |
| At least 80%, below 90% | 8 |
| Below 80% | 0 |

### High-impact judgments: 15

Full credit requires no observed misses in a predeclared test set containing both
violations and legitimate conduct: verification ordering, protected actions,
confidential disclosures, insults, and private paid offers. Check false positives
as well: flagging everything is not success. A known high-impact error prevents
full credit in this subsection. Such a small set still does not prove zero future
errors, and an ambiguous reference cannot certify a correct security judgment.

## Robustness: 15

- 5: consistent interpretation across controlled RU/KZ/EN variants and appropriate
  handling of calls, ASR uncertainty, bot context and internal consultation. Do not
  demand matching scores from merely similar cases with materially different facts.
- 5: expected changes when relevant evidence, speaker attribution, verification
  order or an actual customer request changes; invariance under irrelevant changes.
- 5: at least 95% criterion agreement across designated repeated runs with identical
  inputs and settings, without concealing genuine semantic disagreements.

Stress cases are separate from the primary accuracy set. Stable errors are still
errors; repeatability does not substitute for correct reference judgments.

## Functionality: 15

Three points for each functioning, demonstrated group:

1. Import new conversations and run evaluation jobs with visible state.
2. Create immutable checklist versions and actually apply a newly added criterion.
3. Navigate exact source evidence and play the supplied call audio where authorized.
4. Appeal a judgment, retain the original, and recalculate the reviewed result.
5. Persist and reopen results without a new paid call; display actual failures and
   support explicit retry rather than replace errors with invented scores.

## Usability: 5

Evaluate the complete reviewer journey on the running application: understandable
controls and status, readable source/result comparison, useful evidence navigation,
and clear failures. Decorative features do not earn points without improving that
workflow. A design document does not earn implementation credit.

## Authenticity and traceability: 5

Demonstrate a fresh input and edited criterion through the actual model path.
Record the transcript/checklist version, provider/model, attempt, usage and evidence.
Distinguish old saved results from new inference. No prepared judgments, hidden
reference labels in the model input, or offline score substitution are acceptable.

## Submission readiness and interpretation

Before calling the product ready, verify the new-conversation and changed-checklist
workflow, arithmetic, evidence, saved-result provenance, visible failure behavior,
and review history. A stronger model or more stages earn no automatic points.

The organizer's architecture-diversity consideration concerns cohort selection.
We assign no invented bonus for choosing cloud or local inference.

To justify 95-100 internally, nearly all measured accuracy/robustness requirements
and the working product requirements must be satisfied. That would still not
guarantee the organizer's score or selection decision.

## Current evidence and gaps

The following paragraphs are the historical pre-workflow snapshot. Current
implementation and measurements are in [WORKFLOW.md](WORKFLOW.md) and
[BOUNDARY_VALIDATION_RESULTS.md](BOUNDARY_VALIDATION_RESULTS.md). The scoring
weights and thresholds above remain unchanged; development agreement is not
independent organizer Ground Truth.

The CLI, deterministic scorer, source-reference validation and real API benchmark
history exist. Runtime criteria outside the original eight have been tested. The
20-item calibration pass is complete: 13 assistant proposals accepted by the user,
two applications of accepted rules, and five assistant-only provisional assessments.
Eighteen items have scores and two remain unscored. These are labels, not a new
measurement of model accuracy, and none are organizer Ground Truth.

The accumulated reviewed checklist has not been rerun against an independent
reserved reference set. The API application, frontend, appeals, and reliable call
playback are not implemented yet. Therefore the earlier 60-65 or 85-90 estimates
should not be treated as evidence-based current scores. No new total is claimed.

# Decision: improve the evidence and calibration process before considering a rewrite

2026-11-07. Discussion and experiment proposal; not a validated replacement architecture.
The user's submission deadline is 2026-11-08 at 12:00 Astana.

## Correct the score framing

The previously discussed 60-65/100 assessment was subjective, not measured organizer
performance or an architectural ceiling. Likewise, 85-90 and 95-100 are ambitions,
not supported forecasts. The organizers have not supplied a numerical selection
rubric or Ground Truth labels, and no architecture guarantees their unseen scores.

Keep the current repository, locked environment, dataset adapters, configurable
checklists, structured output validation, deterministic arithmetic, budget ledger,
and frozen baseline reports. They are useful comparison infrastructure. Do not
discard them based on an invented overall score.

## The gap worth addressing

One call currently combines identifying evidence and deciding every criterion.
The model can make an unsupported assumption and use its own explanation to support
the resulting score. Exact quote existence and legal scale values do not catch that.
The other major limitation is calibration: most organizer criterion decisions lack
independently reviewed references, and our own AI labels have genuine disputes.

Neither additional model votes nor a separate extraction stage creates Ground Truth.
Extraction can omit evidence; a critic can reinforce the first model's error.
Treat any extra stage as a hypothesis to compare, not a promised quality upgrade.

## Proposed workflow experiment

1. **Record an explicit rubric interpretation.** Keep allowed values, weights,
   N/A anchors, and channel adaptations in a saved, versioned checklist. Distinguish
   organizer wording from team interpretation. New criteria still work through
   configuration; do not introduce eight hardcoded grading functions.
2. **Extract source-linked observations without assigning criterion scores.**
   Identify customer requests, explicit withdrawals, answers, known details at
   handoff, verification confirmation, protected actions, internal consultation,
   and end-state events. Preserve evidence IDs and short exact quotes. Distinguish
   observable events from inferred motives or missing product knowledge.
3. **Assess the checklist using the complete original source and checked observations.**
   The observations assist the grader; they never replace the transcript. Require
   a rule, relevant evidence, and material counterevidence for each deduction.
4. **Check material contradictions only when justified.** A separate verification
   call may test a disputed claim against the full source. Do not average incompatible
   scores, repeatedly regenerate until agreement, or treat agreement as correctness.
   A changing answer must retain the evidence and reason for revision.
5. **Compute and preserve the result in code.** Keep the existing scorer, separate
   serious flags, explicit failures, and provisional totals for genuine uncertainty.
   Report review coverage so abstaining on difficult cases cannot inflate accuracy.

No offline fallback, prepared ratings, or case-ID-specific grading is introduced.

## Compare before choosing

Use a small, frozen, independently reviewed development set with full criterion
vectors covering RU/KZ/EN, calls, and important rating boundaries. These already
inspected organizer cases are development data, not an unseen holdout.

First compare the present evaluator with the same evaluator using clarified
checklist policy and approved product references where available. Then compare
either a stronger model directly or the evidence-extraction workflow if the observed
errors justify it. Avoid changing model, checklist policy, and workflow together
and attributing the outcome to one cause. Test only a small number of candidates
within available time and funds.

Reserve fresh scenario families and their reviewed labels before the final check;
do not tune on those results. AI-authored labels remain provisional unless a real
reviewer adjudicates them; a non-expert human label is still not organizer Ground Truth.

Record criterion agreement, total-score absolute error, serious-error misses,
unresolved/failure rate, language/channel differences, repeat-run stability, latency,
and actual estimated cost. A few high-impact errors can matter more than an improved
average. Promote a replacement only when the comparison supports it without
introducing material regressions. Retain the baseline if the extra stage does not help.

Useful internal ambitions are mean total-score error no greater than three points
on reviewed full vectors, no observed misses of the defined serious violations,
and at least 95% judgment agreement across designated repeat cases. These are proposed
engineering targets, not achieved results, statistically established guarantees,
or the organizer's selection formula.

## Product completion is part of the task

Protect enough time to implement and verify import, editable checklist versions,
actual evaluation, source navigation, saved results, and an appeal that preserves
the original assessment and recalculates the reviewed score. Resolve audio playback
without pretending transcript analysis includes audio qualities. Avoid consuming
the whole remaining development window on synthetic benchmark tuning.

## Concrete first step, without paid calls

`scripts/prepare_human_review.py` creates a private worksheet and pending-review
JSON manifest with 20 high-value judgments across 12 organizer conversations.
It includes complete transcripts and criterion definitions and omits AI predictions
and expected labels. Its selection follows prior AI error review, so it is calibration,
not a blind test. No labels are marked human-reviewed until someone actually reviews them.

The script is tracked; its generated source excerpts stay in ignored `artifacts/`.
Preparing this worksheet and proposal made no OpenAI calls and did not change the
spending cap. Further paid comparisons must fit the locally configured budget and
available credit.

## External guidance

Official OpenAI documentation recommends task-specific evaluations, human calibration,
and evaluation-driven decisions about additional architecture complexity:
[Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

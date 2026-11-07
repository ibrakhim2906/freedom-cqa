# Evaluation design for discussion

Status: recommended design informed by the full DEV transcript audit. This is
not an implemented or validated evaluator and is not a promise of a judge score.

User deadline: 2026-11-08 12:00, Astana time (UTC+05:00).
Prioritize a working, measured evaluation path early enough to integrate and
verify the full review workflow before the deadline.

## Product objective

A configurable conversation evaluator that follows the saved checklist on new
conversations, grounds each judgment in source evidence, calculates scores
correctly, and supports accountable human review. Accuracy against organizer
Ground Truth is the principal selection criterion.

The supplied eight-criterion checklist is an initial configuration, not eight
hardcoded scoring handlers. Other checklists and chat/call interpretations must
be saved and applied through the interface.

## Generic criterion contract

Each versioned criterion needs an ID, title, actual instruction, allowed answer
values or discrete rating levels with descriptions, weight, N/A permission and
conditions, evidence requirements, and any channel-specific interpretation.
Represent flags separately from weighted scores. Preserve original rubric wording.

For the supplied checklist:

- Weights are 10, 15, 20, 20, 15, 15, 5 for criteria 1-7; criterion 8 is a separate flag.
- Criterion 4 allows exactly 0/5/10/15/20, or justified N/A.
- Criterion 6 allows exactly 0/4/7/10; its maximum contributes 15 weighted points.
- N/A is available only for criteria 2, 3, 4, and 7 under their specific conditions.
- Required but unconfirmed identification is No, not N/A or a generic uncertainty escape.
- A serious-error flag does not automatically zero/cap the supplied checklist total.
- Exclude the three-minute first-response threshold, tags, and attachment scoring.
- Normalize applicable weights and round the final total to two decimal places.

## Recommended pipeline

1. **Preserve and annotate input.** Retain every original message, role, timestamp,
   and stable ID. Add derived handoff, hold/internal-consultation, verification,
   and end-state annotations with evidence references. Do not delete noisy text or
   replace the complete transcript with a summary.
2. **Evaluate from the complete source.** Supply the actual checklist, channel,
   full transcript, and any approved reference material. Return per-criterion
   applicability, allowed answer, concise rationale, supporting/counterevidence,
   and checked spans for omissions. Decompose a criterion into the factual checks
   its wording requires; these checks must follow the configured criterion.
3. **Track customer requests.** Associate substantial questions and follow-ups
   with operator answers or next steps. Preserve unresolved requests. Keep
   consultation completeness separate from communication quality.
4. **Validate.** Reject illegal scale values and N/A choices, missing or invalid
   evidence IDs, and contradictory result structures. Check arithmetic in code.
   Evidence existence does not establish relevance or entailment.
5. **Compare a verification variant.** Test a separate critic against the same
   full source, looking for unsupported evidence, omitted requests, attribution,
   and sequence mistakes. Keep this stage only if measured development results
   improve enough to justify its latency and cost. Do not average incompatible
   labels or assume agreement between models is Ground Truth.
6. **Render and persist actual results.** Expose source-linked explanations,
   unresolved issues, provenance, version comparisons, and original/human-reviewed
   results. There is no offline fallback or prepared-score substitution.

## Channel-aware evaluation

Organizer clarification supplied in chat on 2026-11-07 states:

- The initial checklist was written for chats; the same evaluation logic applies
  to calls with written-communication criteria adapted to spoken interaction.
- For calls, criterion 6 covers logical progression, comprehensible explanations,
  inappropriate expressions, wording, and pause management. Pace, diction, and
  pronunciation clarity may additionally be assessed when audio is available.
- Criterion 4 covers correctness/completeness, errors, and necessary actions.
- A per-control-conversation reference answer guide is not currently supplied.
- Supporting different checklists, including for calls, is central to the task.

Use transcript evidence for assessable spoken-content properties. Do not infer
pace or diction from a text transcript. Treat ASR uncertainty explicitly and
resolve audio playback before adding audio analysis. Internal consultation and
recording boundaries require care when attributing customer-facing speech.

## Reference knowledge

The transcript can establish omitted questions, contradictions, unsupported
assertions, and whether the proposed next step addresses the request. Specific
product facts may require a reference source.

Do not turn an operator's or bot's claim into company policy merely because it
appears in DEV data. Any product/service knowledge added to the evaluator should
have a documented source and scope; do not invent rates, deadlines, or procedures.
Keep lack of a reference distinct from an explicitly contradicted answer.

## Own evaluation dataset

Maintain three separately labeled sets:

1. Provided DEV cases with candidate annotations. AI-authored judgments remain
   provisional until independently reviewed; they are not organizer Ground Truth.
2. Controlled mutations of cases. Specify the intended criterion effect before
   running the evaluator: paraphrase, speaker change, verification order, omitted
   subquestion, lost connection versus operator closure, and rubric change. Other
   criteria can also change; review the mutation's full implications.
3. Fresh realistic cases with reference decisions frozen before evaluator output
   is inspected. Keep related variants together and exclude these cases from
   prompt-example selection until the reserved evaluation is complete.

Prioritize disputed rubric boundaries and representative languages/channels.
Generation by one model and scoring by the same model is not independent quality
evidence. Human review is the strongest available calibration; model disagreement
and exact behavioral invariants are useful diagnostics when reviewers are limited.

## Measurements and build gate

- Exact agreement for binary, flag, and N/A decisions, by criterion.
- Confusion between No and N/A, especially identification and closing.
- Discrete rating agreement/error for criteria 4 and 6.
- Final-score absolute error, alongside criterion-level errors.
- Evidence relevance and whether the evidence actually supports the judgment.
- Serious-error misses and false positives.
- Results by language/channel, repeated-run stability, latency, and actual token cost.

Before expanding the UI, complete a real API baseline, inspect its errors, and
compare the proposed improvement on reference cases not used to author that fix.
Do not claim high competition accuracy from a small synthetic suite alone.

## Distinctive product behavior

- Clicking a judgment reveals the precise supporting and contradicting evidence.
- A request-coverage view shows which customer questions remain unanswered.
- A saved checklist change can be reevaluated with an explanation of changed results.
- Call review distinguishes customer-facing segments from internal hold consultation.
- Appeals preserve the AI result, reviewer evidence and decision, and recalculated total.

These features should expose the evaluation's quality and weaknesses, rather
than hide them behind a generic explanation or a single aggregate score.

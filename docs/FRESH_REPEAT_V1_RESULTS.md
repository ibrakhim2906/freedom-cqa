# Fresh cases and three repeated runs: results

Run date: 2026-11-07. **The reliability gate failed.** Of 24 independent initial
evaluations, 18 passed first attempt (75%). Five permitted mechanical repairs
produced four further valid assessments. Two samples remained failed: 22/24 valid
final results (91.67%). No validator, expected label, source or runtime code was
changed during the experiment. Rejected outputs receive no accepted score.

The selected judgments in the 22 valid assessments are defensible under the
configured rubric. That does not make their complete dependency/evidence audits
equally sound. The run exposes repeatable transport fragility and residual
reasoning/provenance weaknesses. This evidence does not justify a 95–100 product
grade or organizer Ground Truth accuracy.

## Prospective protocol

Eight freshly authored conversations were committed in `535feaf` before API
execution. Two conversation-only AI reviewers assessed the drafts; the parent
adjudicated the final expectations before inference. There are 62 frozen
provisional labels and 31 semantic checks. Two consultation ordinal boundaries
(cases 01/05) were explicitly unscored before the run, while their factual and
evidence requirements remained mandatory. Case 07 consultation20 is a prospective
team adjudication of corrected final advice, not an organizer label.

All eight criterion outputs, including the two unscored cells, enter stability
analysis. Every case received three independent initial requests with identical
input/schema hashes; no previous-round outputs or expected answers entered the
model input. The engine stayed at runtime commit `4b1bb16`, prompt
`evaluator-v7-0d77742ac102`, `gpt-6.1-sol`, medium reasoning and 6,000 output tokens.
SDK retries were disabled; at most one existing mechanical repair per sample
was allowed. The [original freeze](FRESH_REPEAT_V1.md) remains unchanged.

## Quantitative outcome

| Measure | Result |
| --- | ---: |
| Planned and actually submitted initial samples | 24/24 |
| Valid first attempt | 18/24 (75%) |
| Valid after bounded repair | 22/24 (91.67%) |
| Provider requests, including repairs | 29 |
| Repairs / successful repairs | 5 / 4 |
| Initial end-to-end labeled agreement | 141/186 (75.81%) |
| Final end-to-end labeled agreement | 172/186 (92.47%) |
| Accepted-only labeled agreement | 172/172 (100%) |
| Cases with three valid, labeled-correct samples | 7/8 |
| Cases with three valid, identical complete grade vectors | 6/8 |
| Pairwise full-vector agreement, invalid pairs receive no credit | 19/24 |
| Pairwise criterion agreement, invalid pairs receive no credit | 166/192 |
| Numeric total MAE, fully labeled finalized cases | 0 on all 12 eligible samples |

Agreement concerns AI-authored provisional labels. Accepted-only 100% excludes
the failures and the two prospectively unscored ordinal cells. It is not overall
accuracy. Numeric MAE likewise does not certify evidence entailment or audit
quality. No first-pass failure receives retroactive first-pass credit after repair.

| Case | Consultation across rounds 1 / 2 / 3 | Final validity | What the result establishes |
| --- | --- | --- | --- |
| 01: Correct tariff routes + false incidental report description | 20 / 20 / 15 | 3/3, all first pass | The false clause is consistently identified separately; exact numeric output is unstable within a pre-flagged rubric ambiguity. |
| 02: Same routes + true report description | 20 / 20 / 20 | 3/3, all first pass | The matching source supports the content; missing introduction remains deducted. |
| 03: Confirm visible, unverified ten-minute guarantee | Review / Review / Review | 3/3, all first pass | Seeing a control does not establish submission, execution or an unlock deadline. Closing No remains. |
| 04: Submitted for review, same guarantee | Review / Review / Review | 3/3, all first pass | Submission is not execution; the active material guarantee remains unverified. Closing No remains. |
| 05: Training PDF not downloaded, false completion assurance | Failed / Failed / 0 | 1/3, repaired | Known false completion is identified in the final valid result, but the workflow fails twice. Consultation had no exact numeric gold label. |
| 06: Training PDF actually downloaded/opened | 20 / 20 / 20 | 3/3, each requires repair | Narrow interaction evidence is sufficient; all three initial outputs fail redundant wording equality. Hold management7 remains. |
| 07: False immediate-execution advice explicitly corrected | 20 / 20 / 20 | 3/3, all first pass | Original falsehood and supported correction remain visible; introduction and hold deductions survive. One dependency audit is too coarse. |
| 08: Same false execution advice remains active | 0 / 0 / 0 | 3/3, all first pass | A correct navigation route does not excuse active wrong key advice. Introduction and hold deductions survive. |

Case 01's exact-vector instability is counted even though the numeric boundary
was pre-flagged. Case 05's two failures are counted even though its consultation
ordinal was unscored. The independent evidence/control changes produce meaningful
differences; stable but incorrect reasoning would not earn semantic acceptance.

## Complete-assessment review

Reviewers read all 176 selected judgments in accepted records, their claims,
coverage, deductions, source references and exclusions, and all three samples
for each case. Root separately revalidated every accepted result and score.
Rejected raw proposals were inspected only diagnostically. Reviewers saw the
frozen expectations; they are not independent human experts.

Of 93 scheduled semantic-check instances,83 passed, two were qualified, and eight
could not earn accepted credit because their outputs were rejected. Additional
audit-quality findings below are retained even when a frozen check or selected
grade passed. No expectation or recorded output was rewritten after inspection.

### Failures and repeated fragility

1. **Whitespace stalling, round 1/case 05.** The provider stopped at the output cap.
   The raw response contains 19,905 trailing whitespace characters, stopping after
   opening `next_step.support.unresolved_aspects`, whose schema requires an empty
   array. This suggests constrained-generation stalling; it is not proof that
   ordinary response verbosity alone caused the failure. Raising the cap could
   merely bill more whitespace. The incomplete response remains rejected.
2. **Duplicated proposition equality, case 06 in all three rounds.** The initial
   claim and supported proposition were narrow and semantically compatible, but
   not literally identical. The strict equality check rejected all three. Each
   sole repair preserved every grade and supplied identical wording. This is a
   repeated contract fragility, not three established policy-to-completion errors.
3. **Metadata-kind mismatch, case 05 rounds2/3.** Initial output used
   `account_state` with `interaction` scope for the fictional training task. The
   existing validator rejected it. Both repairs used `general_fact/interaction`.
4. **Invented quote during round 2/case 05 repair.** The repaired audit added a
   duplicate greeting exclusion quoting `Сәлемсіз бе`; the source says
   `Сәлеметсіз бе`. This is a nonverbatim quote, not a source-role change. The
   result remains rejected. No local quote cleanup or deletion promoted it.

All five repairs retained the same proposed eight-grade vector. The initially
rejected proposals are still not accepted evaluations or first-pass successes.

### Reasoning and provenance qualifications

- **Evidence chain, round 3/case 05.** The completion contradiction needs both the
  client's noncompletion report at m3 and the later system audit establishing no
  intervening action. Only the system audit is declared observational proof; the
  essential client premise is placed in non-proving context. The explanation
  cites both and reaches a defensible grade, but the typed proof route is incomplete.
- **Compound counterfactual, round 3/case 07.** The final supported claim combines
  review/execution guidance with the ancillary absence of a guide deadline and
  maps the whole false branch to 0. If only the deadline clause were false, the
  key review guidance could remain correct. Earlier rounds separated the detail
  or excluded it as grade-independent. Stable actual grades hide audit imprecision.
- **Counterfactual drift, round 2/case 03.** A combined submission/review proposition's
  false branch changes 0 → Review → 0 across rounds. The real grade remains correctly
  provisional because the separate ten-minute guarantee is unverified.
- **Irrelevant counterevidence, round 2/case 02.** Ordinary navigation wording is
  listed as counterevidence to missing self-introduction. It is verbatim but does
  not counter that criterion's opening defect. The main selected grade remains sound.

The negative training fixture also lacks independent positive verification of
the exact filename/Downloads route. Genuine route uncertainty is different from
its prospectively declared ordinal ambiguity. It was not silently relabeled as
an evaluator error; the known false completion can still independently determine
the final 0 branch. The frozen data and labels remain unchanged.

## Scheduling continuation and preservation

The original shared $3.50 local cap protects whole first-plus-repair stages. Under
concurrent holds, the base runner skipped the never-submitted round 3/case 07. After
all holds released, its protected stage fit within the SAME group and SAME cap.
A separate protocol was recorded before submitting only that missing sample.
It passed first attempt. No failed paid sample was resubmitted.

The original 24-row `benchmark.json`, including its 21 valid, two failed and one
budget-skipped row, is unchanged. `continuation.json` preserves the one later
sample. A separately saved `completed-schedule.json` composes the planned schedule
for analysis, retaining the original skipped row and source hashes as provenance.
There was no budget increase, expected-label change, code change or adaptive
selection of a replacement for a bad response.

All ten older preservation hashes and every new freeze/source/schema hash still
match. There are 24 unique initial sample pairs and 29 unique provider responses.
The older known-case live run and 65 organizer results were not overwritten or
unnecessarily reevaluated. The new scenarios use the saved official materials
and explicitly fictional training data; all eight are chats, without audio.

## Actual token-priced cost

**$1.7116115 (about $1.71)** for 24 initial requests plus five repairs, including
rejected and truncated outputs. Base execution: $1.6548496; completion of the
previously unsent sample: $0.0567619. No unknown-usage or unrelated new calls were
found; all receipts match attempts and ledger IDs 563–591.

| Round | Requests | Token-priced cost |
| --- | ---: | ---: |
| 1 | 9 | $0.7017437 |
| 2 | 10 | $0.5086914 |
| 3, including unsent-sample completion | 10 | $0.5011764 |

Provider usage: 596,698 input tokens = 87 ordinary + 443,500 cache reads + 153,111
default 30-minute cache writes; 128,431 output tokens include 7,967 reasoning tokens.
Reasoning is not charged twice. Prices use [official OpenAI model rates](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
and [disjoint cache accounting](https://developers.openai.com/api/docs/guides/prompt-caching).
This is captured-usage reconciliation, not an independently retrieved invoice.
The preserved ledger estimate is $2.477706, exceeding token-priced cost by $0.7660945.

Repairs cost $0.3653059. Failed evaluation attempts cost $0.4148027, including the
truncated request at $0.107121. These categories overlap and must not be added to
the total again.

Private evidence is under `artifacts/fresh-repeat-live-v1/`; public machine results
are in `audits/fresh-repeat-v1-results.json`. The next engineering priorities are
source-span references that avoid retyping quotes, a canonical observation
proposition that avoids redundant free-text equality, and explicit atomic proof
dependencies that preserve all necessary premises. These are proposed mechanism
changes; none was introduced to this frozen run. Further UI polish does not resolve
the measured reliability and audit-quality gaps.

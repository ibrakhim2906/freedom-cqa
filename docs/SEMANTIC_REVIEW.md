# Semantic review before UI integration

Review date: 2026-11-07. This review uses the supplied checklist, all saved organizer
evaluations, and selected source transcripts. It is AI review, not independent
adjudication. Original datasets and first-run results remain unchanged.

## Is the architecture suitable?

Yes: complete transcript + configurable rubric + source-linked structured judgments
+ deterministic arithmetic is a practical architecture for this task. Each new
evaluation actually analyzes its inputs. There is no prepared answer lookup or
offline scoring fallback. A new arbitrary criterion already ran through the real API.

The current evidence does not establish competition accuracy. Only 14 provisional
expectations cover the 520 possible judgments in the 65 organizer conversations.
Eight fully labeled original authored cases mostly share one simple family.
Agreement with our own AI-authored labels can reveal regressions but cannot certify
agreement with the organizers' unknown reference labels.

The highest-value next improvement is better interpretation and review of evidence,
not a larger agent architecture. A second model pass is not automatically independent
or more accurate and would add recurring cost. No extra critic is enabled by default.

## Findings from organizer sources

| Case | Observed result | Assessment and next action |
| --- | --- | --- |
| RU-015 | Consultation 10 because the follow-up about waiting for a username lacked a direct answer | Likely overly literal: the operator already explains retention after closure and advises another username. Whether permanent retention is actually established remains a product-policy limitation. Test explicit logical entailment with a fictional, unambiguous reference before changing grading. |
| EN-006 | Needs No because transfer timing was collected after referral | Unsupported prerequisite: nothing supplied says timing is required before creating a referral. Currency was collected first, identity verified, timing subsequently attached. Progressive clarification is not itself failure; the missing fact must be necessary for the answer/action it precedes. |
| RU-014 / KZ-008 | Needs N/A versus No, despite the same website being identified by the bot before human handoff and redundantly requested again | Clear inconsistency of interpretation. The checklist does not explicitly settle whether "from the beginning" means first customer message or human entry. Record this ambiguity; do not silently proclaim either interpretation organizer policy. |
| RU-024 | Consultation 10 because D-account transfer instructions were absent | Borderline inferred need. The customer explicitly asks which account to use, but the funds-location follow-up may imply a practical transfer question. Do not invent a mandatory full transfer tutorial or assume the implied need is irrelevant. Keep for human review. |
| RU-020 | Consultation 10 for an unresolved existing-position question | Do not automatically raise this because it resembles the username case. Saying the current-order setting is separate from existing positions may still fail to explain its effect on an existing holding. Product reference or clearer language is needed. |
| KZ-013 / EN-013 | Consultation 20 versus 10 with the same serious paid-offer flag | Not an exact translation pair: the Kazakh customer confirms finding the item; the English customer renews a request for app help before the operator closes. Different coverage can be justified. An independent serious flag does not automatically force every other criterion to fail. |
| EN-009 | Closing No versus our provisional N/A | Connection loss alone does not prove whether the operator had an opportunity to close. A customer's thanks alone does not prove time to respond either. The original exact N/A label is weak and should be excluded from claims of adjudicated accuracy. |
| RU-003 / EN-007 | Consultation 10 | Useful negative controls: a substantial commission/retry-timing question genuinely remains unanswered. Improving implicit-answer recognition must not erase these omissions. |
| Call RU-002 | Internal consultation while on hold excluded from customer closing | Useful successful behavior: several people share the operator role. Do not flatten that passage into a customer-facing farewell. |
| Call RU-005 | Contact needs review, total provisional | Appropriate limitation: noisy opening and unavailable audio do not justify inventing a self-introduction. Transcript-only judgments cannot establish diction or pace. |

Case identifiers omit the common `p1-` / `p4-` prefix in this table. No private
source transcripts, signed URLs, or audio are included in this public-ready note.

## Changes to test

- Accept answers entailed by the operator's words; do not require keyword repetition.
  Reference facts alone do not count as an answer the operator gave.
- Track explicit question withdrawals separately from answered and unresolved requests.
  Thanks, silence, or refusal of a private offer do not automatically withdraw other questions.
- Tie missing-information deductions to the particular answer or action requiring that
  fact. Acknowledgment or a permitted referral can precede further clarification.
- Accept policy-supported concrete escalation without demanding immediate resolution.
  Preserve failures when an explicitly required detail was never obtained.
- Require a separate criterion-specific reason for each deduction. Serious-error
  flags neither cap totals nor automatically imply incomplete consultation.
- Preserve uncertainty about unspecified applicability boundaries rather than putting
  invented thresholds or case-specific scores into the evaluator.

## Frozen development comparison

`evals/review-v2.jsonl` adds 12 fictional cases in five scenario families, including
Russian and Kazakh variants. Expectations were frozen before either comparison run.
They cover implicit versus absent answers, progressive versus premature advice,
withdrawn versus outstanding details, valid versus unsupported escalation, and a
resolved navigation request versus a new unanswered question after a private offer.

These are targeted development regressions, not a hidden test set. Most have full
vectors; disputed secondary effects are deliberately not labeled. Full-vector
agreement still depends on provisional labels and is not organizer score accuracy.

Both real API runs completed all 12 cases without structural repair:

| Measure | Control v1 | Candidate v2 |
| --- | ---: | ---: |
| Matched provisional expectations | 86 / 90 (95.6%) | 87 / 90 (96.7%) |
| Consultation expectations matched | 11 / 12 | 10 / 12 |
| Empathy expectations matched | 8 / 10 | 10 / 10 |
| Mean total absolute error on nine full provisional vectors | 6.13 points | 3.19 points |
| Estimated cost | $0.251634 | $0.262926 |

Do not describe this as a demonstrated large accuracy improvement. The new
consultation disagreement concerns whether an alternative registration step
satisfies the waiting question without a username-retention explanation. Both
readings need review under the checklist's "correct next step" clause. Two empathy
labels moved toward our expectations; those expectations are also subjective.
The missing-ticker sequencing deduction remains a defensible disagreement.

The explicitly withdrawn filename question now has status `withdrawn` with the
customer message cited separately. This is a traceability improvement even when
the final consultation score is unchanged. The validator checks customer attribution
and ordering; it cannot prove the cited text semantically cancels the request.

This was one sample per version/case, not a repeated stability study or hidden
holdout. The suite is short and reference-explicit and includes no real calls.

Artifacts, all ignored: `semantic-review-control-v1.json`,
`semantic-review-candidate-v2.json`, their frozen suites, and
`semantic-review-comparison-v2.json`. Reproduce the comparison with:

```powershell
uv run python -m scripts.compare_benchmarks artifacts/benchmark/semantic-review-control-v1.json artifacts/benchmark/semantic-review-candidate-v2.json --output artifacts/benchmark/new-comparison.json
```

## Focused organizer recheck

Six organizer cases completed under candidate v2, costing $0.168326. The comparison
control was frozen before this run using the first completed result in the declared
chronological report order, never the result with the most favorable score.

- EN-006 needs changed No to Yes: timing was gathered progressively and no source
  established that it was required before initial referral. This removes an unsupported
  prerequisite rather than introducing a fabricated transfer procedure.
- RU-015 consultation changed 10 to 20: the retained-login explanation and alternative
  registration step were accepted as answering the practical follow-up. This is
  plausible, not an adjudicated organizer label.
- RU-003 and EN-007 both retained consultation 10 for real unanswered substantial
  questions. The change did not erase these two negative controls.
- RU-014 / KZ-008 still received needs N/A versus No under the original checklist.
  This remains an actual consistency weakness. Other communication judgments also
  vary and are not independently adjudicated.

The four existing sparse provisional checks in these six cases matched. There are
no full organizer reference vectors here; do not market that as "100% organizer accuracy."

## Explicit draft to settle N/A scope

`checklists/freedom-v2-draft.json` preserves weights and allowed levels and explicitly
defines "beginning" for needs N/A as the **first substantive customer request in the
whole conversation**, including the bot phase. Information later obtained by the bot
is already known to the operator, but does not retroactively make it available at
the beginning. This follows the literal time wording and makes bot-context handling
separate from the N/A time anchor.

This is a team interpretation draft, not an organizer clarification. The original
`freedom-v1.json` remains unchanged and remains the default. The alternative anchor
at human handoff could give a different result; state the chosen policy explicitly
before presenting benchmark conclusions or final scores.

A two-case real API check of the draft is recorded separately; it changes the
rubric interpretation, so it is calibration evidence rather than an apples-to-apples
accuracy comparison with the original rubric.

Both completed with needs **No** and the same full eight-criterion vector, total
56.88. Cost: $0.056390. This one pair supports the value of a precise interpretation;
it does not prove that our chosen anchor matches the organizer's hidden policy.
The unrelated empathy change between samples also reminds us that repeated-run
stability has not been established.

Execution note: the first three semantic-review runs used 6,000 maximum output
tokens; the two-case draft calibration used 4,000 to keep conservative reservations
within the remaining lifetime cap. All used Sol medium and concurrency one, and
all completed without truncation or repair. Because the token cap also changed,
do not attribute every judgment difference solely to the rubric clarification.

## Implementation and verification

Candidate v2 keeps one full-source evaluation pass rather than introducing an
unmeasured extra critic. The scorer stays generic; no conversation-ID checks,
expected-answer lookup, language-specific scores, or fallback judgments were added.
The key, private organizer data, raw responses, and usage database remain ignored.

New request lifecycle validation requires customer references for withdrawals,
rejects a withdrawal preceding the request, and preserves historical v1 records.
The API schema requires the new field while constraining its IDs to actual customer
messages. Custom JSONL suites and bounded per-run concurrency are supported;
same-suite comparison rejects mismatched suites or duplicate case IDs.

25 tests, Ruff, and Git whitespace checks passed. Original authored-v1 cases,
baseline reports, and the official checklist configuration were not overwritten.
The frontend, saved-result reuse, and appeal workflow have not been built here.

## Spending after this review

| Phase | Calls | Estimated cost |
| --- | ---: | ---: |
| Previous initial coverage phase | 111 | $2.688466 |
| New-case control v1 | 12 | $0.251634 |
| Same-case candidate v2 | 12 | $0.262926 |
| Focused organizer candidate v2 | 6 | $0.168326 |
| Explicit N/A-scope draft calibration | 2 | $0.056390 |
| Total | 143 | $3.427742 |

This review added $0.739276. The ledger has 138 completed and five rejected attempts,
no unknown-cost entries or outstanding reservations. The $3.50 local lifetime cap
still applies; only $0.072258 remains under that cap. From the user's initial $3.77,
the inferred unused balance is about $0.342258 if there were no other charges.
These are conservative token-rate estimates, not an account-balance API or invoice.
No further paid tests were run after this review.

## Recurring cost observed before this comparison

Using the latest completed evaluation for each of the 65 organizer conversations:
60 chats averaged $0.025922 each (range $0.020196-$0.038072); five call transcripts
averaged $0.045578 (range $0.040780-$0.054204). These are observed token-rate
estimates, exclude hosting/audio transcription, and do not include future retries.

The $2.688466 previous development total includes repeated and synthetic tests.
Production should save completed evaluations and reuse them on reopening; a deliberate
new evaluation or checklist change incurs a new API call. Persistence/reuse is not
implemented in the web application yet.

## Remaining build gate

Use the focused comparison to decide whether to keep the change. Do not postpone
the whole application indefinitely for self-generated benchmark improvement.
Before claiming reliable aggregate accuracy, independently review varied full
vectors, especially real calls and consultation 0/5/10/15/20 boundaries. Any fresh
holdout must be family-separated and untouched during prompt tuning.

Keep original assessments and reviewer corrections separately. The UI should expose
the actual evidence, request coverage, checklist version, and genuine uncertainty.

# Frozen organizer DEV run — 65 conversations

Run and source review completed on 2026-11-07. Starting commit: `699df48`.
Checklist: `1-reviewed-015`; model: `gpt-6.1-sol`, medium reasoning;
strategy: grounded; output cap: 6,000 tokens; concurrency: 3.

**The evaluator produces useful source-grounded judgments, but final-score coverage
is not yet strong enough for a 95–100 readiness claim.** Only 34 of 65 inputs
received a final numeric score. This is a coverage finding, not measured accuracy.
There is no organizer Ground Truth or independently adjudicated complete reference
vector for these 65 inputs, so total-score MAE and an expert-agreement percentage
cannot be reported.

## Outcomes and cost

| Outcome | Count | Share of all 65 |
| --- | ---: | ---: |
| Valid assessment with final numeric total | 34 | 52.3% |
| Valid assessment requiring review; no final total | 27 | 41.5% |
| Exhausted strict validation | 4 | 6.2% |

There were 57 valid initial outputs and four further valid assessments after the
single permitted mechanical repair. Thus 61/65 assessments passed validation;
**93.8% validation success is not 93.8% accuracy**. Every saved successful result
was revalidated against its source, exact checklist, deduction audit and scoring
arithmetic after merging.

| Input group | Numeric | Provisional | Failed | Total |
| --- | ---: | ---: | ---: | ---: |
| RU, including calls | 19 | 14 | 2 | 35 |
| KZ | 8 | 6 | 1 | 15 |
| EN | 7 | 7 | 1 | 15 |
| Chats, all languages | 34 | 23 | 3 | 60 |
| Call transcripts, RU | 0 | 4 | 1 | 5 |

Language and channel rows are overlapping views, not additive categories. Calls
were evaluated from the supplied transcripts; no audio was analyzed. These group
counts describe coverage, not comparative language accuracy.

Estimated uncached cost: **$4.421314**, reconciled against 73 paid responses and
one zero-cost provider credit rejection. Unknown-cost attempts: zero.

- Before the top-up interruption: $2.884932.
- Seventeen previously unsubmitted inputs: $1.473820.
- One interrupted mechanical repair resumed: $0.062562.
- Additional spending after top-up: **$1.536382**.

Provider credits interrupted the run. Recovery submitted only never-submitted
inputs and the one repair whose preceding request was rejected at zero cost.
The rejected paid candidate and zero-cost rejection remain in its history.
Successful outputs and exhausted validation failures were never replaced by a
more favorable retry. No evaluator, checklist, source or expectation was changed.

## Four failures: concrete contract weaknesses

| Case | Source evidence | Why the strict result failed | Required design change |
| --- | --- | --- | --- |
| `p1-ru-018` | m10–m13: unsupported exchange-cancellation assertion, customer objects, operator cannot explain, then closes | A material unverified claim linked to consultation forces review even when failure to answer or give a useful next step is independently established | Represent the actual dependency of the grade, separate from a claim's topical relevance |
| `p1-kz-005` | m10–m13: wrong initial menu, corrected route, customer explicitly finds the destination | A historical contradicted claim prevents full consultation credit despite correction and confirmed resolution | Track correction/supersession and whether the original error has unresolved consequences |
| `p1-en-014` | m11–m15: account-specific disclosure before verification; explicit waiver; follow-up question unanswered | Initial output links an unverified assertion to independently provable failures; repair explains independence but leaves an empty criterion-impact list, forbidden by the schema | Give independently justified grades a valid contract; do not remove the verification violation or unanswered-question deduction |
| `p4-ru-003` | m27–m28: wrong subject corrected; m65–m76: verification, order investigation and callback | Superseded processing-schedule claim still links to needs/consultation, even while its explanation says neither grade depends on its truth | Apply the dependency and correction model to noisy calls as well as chats |

These are failed assessments, not zero operator scores. Removing the validators
would hide the conflict. The next change should make the representation correct
and preserve strict evidence validation. Some first outputs also used operator
statements as independent factual evidence; the role validator correctly rejected
those. A repair may fix the source role, but cannot resolve a contradictory
dependency contract by itself.

## Why 27 valid results remain provisional

Across these assessments, 26 consultation judgments, six closing judgments and
one contact judgment need review. Counts overlap within a conversation.

Most consultation uncertainty concerns product rules, eligibility, account state,
or unconfirmed navigation. The source pack supplies no attached, applicable
policy references. Most chats also lack dates and an explicit knowledge scope.
The existing three-guide reference pack is scoped and dated; applying it silently
to different platforms, historical calls or all entities would create false
verification. Matching bot or colleague statements are not independent evidence.

The source review also found cases where uncertainty is too broadly propagated:

- `p1-en-015`: final login route explicitly works, yet a superseded initial
  settings instruction keeps consultation provisional. Its independently supported
  management deduction should remain.
- `p1-en-008`: a substantial existing-position question remains unanswered.
  The evaluator recognizes that defect but leaves consultation wholly provisional
  because another scope claim lacks verification. Whether that claim can change
  the discrete consultation level must be represented explicitly.
- `p1-kz-008`: customer confirms opening the destination after alternative access
  routes, but ambiguity about which route worked keeps consultation provisional.
  Compare `p1-en-002`, where web success is explicit. Do not require identical
  results for different evidence; adjudicate which unused alternatives are truly
  grade-changing.
- `p1-en-013`: the customer reaches a search bar, not explicitly a bond result.
  Treating this as incomplete factual verification can be defensible. Its private
  paid-advice solicitation is nevertheless a clearly supported serious-error flag.

This is not a mandate to score every uncertain answer. Preserve uncertainty when
the missing fact can actually change the permitted outcome. Better reference
coverage and better dependency modeling solve different problems.

### Provisional case index

| Cases | Main issue requiring review |
| --- | --- |
| `p1-ru-008`, `p1-kz-004` | Withdrawal retry rule after personal-data update |
| `p1-ru-009`, `p1-kz-015` | Account state / procedural waiver; premature-disclosure flags remain assessable |
| `p1-ru-012`, `p1-kz-014`, `p1-en-011` | Language in which the provider supplies form 1042-S |
| `p1-ru-013` | Company financial-statements route not explicitly confirmed successful |
| `p1-ru-015`, `p1-kz-007`, `p1-en-001` | Username reuse after account closure |
| `p1-ru-016` | Earlier reinstall advice and final access route not demonstrated successful |
| `p1-ru-020` | Margin-setting effect on existing positions |
| `p1-ru-024`, `p1-kz-011`, `p1-en-010` | D-account trading eligibility |
| `p1-ru-027` | Additional unconfirmed tariff route alongside a successful report route |
| `p1-ru-028` | Form reached versus requested operation completed |
| `p1-kz-008` | Materiality of alternative access routes; incomplete closing |
| `p1-en-008` | Unanswered position question plus unverified scope claim |
| `p1-en-009` | Closing opportunity unknown before connection loss |
| `p1-en-013` | Bond search functionality not established by reaching a search bar |
| `p1-en-015` | Superseded advice despite confirmed final login success |
| `p4-ru-001` | Service/manager-access policy |
| `p4-ru-002` | Security-specific OTC eligibility and jurisdiction explanation |
| `p4-ru-004` | Instrument eligibility, trader route and market hours; closing overlaps disconnect |
| `p4-ru-005` | Reset/registration policy and hours; corrupted introduction and ending |

Several rows also have closing uncertainty. The complete criterion-level index,
review reasons and source message IDs are saved privately in `audit.json`.

## Weak numeric scores and remaining interpretation disputes

Low operator scores are not automatically evaluator errors. The source review
supports retaining these substantive deductions:

| Case | Total | Review finding |
| --- | ---: | --- |
| `p1-ru-014` | 56.88 | Missing introduction, redundant known-context question, separate process lapse and incomplete closing; successful final login is still credited |
| `p1-ru-022` | 38.46 | Private money/advice offer, failed consultation and ignored objection; serious error retained |
| `p1-ru-026` | 39.23 | Vague help, needless repetition, ignored experienced difficulty and deficient closing; consultation level 5 versus 0 remains a calibration boundary |
| `p1-ru-029` | 62.31 | Insult clearly supports empathy failure and serious flag; the additional management7 deduction appears to cite the same insult without a distinct clarity/process defect |

`p1-ru-023` and `p1-kz-013` each receive 92.31 **with a serious-error flag**.
That is not necessarily leniency: useful navigation remains credited, and the
critical flag is separate from the numeric score. Showing only the total would
misrepresent these results.

Additional adjudication priorities:

1. **Overlap:** resolve `p1-ru-029` against the actual management rule. Preserve
   independently justified multiple deductions; do not make scores stable by
   suppressing every overlap.
2. **Call empathy:** `p4-ru-001` acknowledges the complaint late, and the customer
   notices some improved response. The evaluator still assigns empathyNo because
   no practical response addresses that complaint. This is a rubric boundary,
   not a proven tone failure. Its counterevidence must remain visible.
3. **Answer coverage:** `p4-ru-004` repeatedly asks whether contact is necessary
   for every purchase. Repeated email/telephone alternatives imply an answer but
   do not explicitly answer frequency. Adjudicate that distinction before marking
   the request fully answered.
4. **Call clarity:** `p4-ru-003` has a plausible OTP-instruction clarification defect,
   but ASR uncertainty is an alternative explanation. Do not infer poor diction
   from corrupted text without audio.
5. **Closure:** short summaries versus mere courtesy need consistent treatment.
   Disconnect without evidence of an opportunity should remain uncertain; active
   agent closure supports an opportunity. `p1-en-009` is the only mismatch against
   the older sparse development labels: old N/A versus current needs_review.
   Neither label was changed during the run.

Nine numeric cases score 100 on their applicable criteria. This is not nine proven
perfect service interactions. For example, `p1-ru-025` has only 55 applicable
weight because the customer leaves before a substantive request. Coverage and
serious flags must accompany normalized totals.

## Evidence limits and next core work

The 14 existing partial development expectations match 13 predictions. They are
AI-authored provisional expectations, cover a tiny selected subset and contain no
complete reference vector. **13/14 is not a credible estimate of overall accuracy.**
The source review here was performed by the assistant after seeing model outputs;
it identifies candidates for adjudication, not independent expert labels.

Before UI polish, prioritize:

1. Model grade-changing factual dependencies and corrected/superseded claims.
   Test both valid recovery and genuinely harmful uncorrected advice.
2. Add only applicable references with explicit scope/date and provenance; leave
   private account state unresolved without real records. Measure how much
   determinate-score coverage improves without unsupported factual confidence.
3. Adjudicate overlap, implication-versus-answer, closing and noisy-call boundaries.
   Keep a frozen holdout rather than editing references to agree with this run.
4. Re-run the fixed failures and paired controls, then a new frozen full run.
   Compare failure rate, numeric coverage, justified deductions, repeatability and
   credible reference agreement separately. A mechanical pass alone is insufficient.

## Reproducible local artifacts

All raw source, outputs and manual source notes remain under ignored
`artifacts/organizer-65-v1/`:

- `protocol.json`, `first-pass.suite.jsonl`: pre-inference protocol and frozen inputs.
- `first-pass.json`, `continuation.json`, `repair-continuation.json`: original segments.
- `continuation-plan.json`, `repair-continuation.intent.json`: bounded recovery provenance.
- `merged.json`, `merged.suite.jsonl`: all 65 outcomes with complete paid history.
- `manual-review.json`: source review of all 65 transcripts, including high scores.
- `audit.json`: per-case index and deterministic validation/ledger reconciliation.
- `submission-preview.json`: organizer-format local DEV preview for team `polygon`.

The preview retains all 65 IDs: **34 `ok`, 31 `error`**. The appendix format has no
provisional status, so unresolved assessments are explicit errors rather than
invented final numbers. Internal assessments retain their usable criterion
judgments. This is a local preview; it is not a published submission or PROD run.

Recovery and audit tooling:

```powershell
uv run python -m scripts.continue_organizer_credit_run merge
uv run python -m scripts.audit_organizer_run
uv run python -m scripts.export_submission --source data/private/dev.json --report artifacts/organizer-65-v1/merged.json --checklist checklists/freedom-reviewed-015.json --split dev --output artifacts/organizer-65-v1/submission-preview.json
```

Merge refuses an existing output. Repair refuses an existing intent or result to
prevent hidden repeated calls. Audit and export are deterministic and make no API
calls. The run's original evaluator source hash is checked before recovery and
audit; core changes require a separate benchmark with its own provenance.

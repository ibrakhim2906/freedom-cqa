# Existing-results source audit — 2026-11-07

The audit reviewed all 65 organizer conversations / 1,268 messages without model
inference, new evaluation runs or score changes. All 60 chats and five calls have
individual source-review entries. It uses the frozen 65-case run, with the four
explicitly declared later failure rechecks as the latest available records.

These are mixed workflow versions, **not a fresh full benchmark**. The joined
index contains 36 numeric and 29 provisional assessments; it does not replace
the original full-run outcome of 34 numeric / 27 provisional / four failures.
No independent organizer accuracy, new product grade or repeatability is inferred.
Audio recordings were not listened to.

## What was checked

- Substantial customer requests versus the operator's actual answer or next step.
- Operator truth assertions versus the emitted claim audit and its exact scope.
- What customer confirmation establishes: control visibility, successful action,
  requested task completion or merely courtesy.
- Bot/customer/operator/system attribution and internal-call consultation.
- Independent deductions, actual corrections, residual consequences and closing.
- Which missing facts need a product source, a private record, audio, metadata,
  interpretation, or no additional evidence at all.

Source message IDs/roles were validated, all 65 selected successful assessments
were mechanically revalidated, and weighted totals were recalculated without
changing any result. Mechanical success is not proof of semantic correctness.

## Findings, without inflating the count

The private ledger contains 51 review observations:

| Disposition | Observations | Meaning |
| --- | ---: | --- |
| Confirmed audit/representation gap | 10 | Five are the same missing-date defect repeated across five calls; five concern assertions not separately represented in the claim trace. These are not ten proven wrong grades. |
| Semantic review candidate | 19 | Source-grounded questions needing adjudication; none is automatically a scoring error. |
| Supported behavior to preserve | 22 | Controls against removing legitimate deductions or creating unnecessary uncertainty. |

These observations come from assistant source review after seeing model outputs,
not a blinded expert assessment. Another agent's agreement is also not GT.

## Generalizable defects and boundaries

### 1. Supplied rules are sometimes mistaken for missing product knowledge

The original checklist, pages1/3, already establishes verification ordering for
protected conduct. RU009/KZ015/EN014 expose why an operational waiver assertion
must not make that direct grading rule uncertain. Actual private account state
can remain unknown while the source demonstrates premature claimed disclosure.

Likewise, a missing fee answer does not require a complete tariff book merely to
establish that the operator did not answer. The rubric permits a concrete next
step; failure to prove an investigation's eventual completion is not automatically
failure to offer one.

**Next implementation target:** explicit evidence classes and claim-to-rule
provenance, avoiding both universal verification demands and unsupported certainty.
This audit has not changed the existing rules or produced new grades.

### 2. Claim validity does not establish claim-inventory completeness

Five observations identify assertions not separately retained in the saved claim
trace:

| Source | Trace gap | Consequence |
| --- | --- | --- |
| RU027 m20 | Report period and its relationship to current-tariff advice are not separately represented | Temporal meaning needs its own evidence question; successful tariff-field navigation does not settle it |
| EN014 m11/m13 | Latest factual_claims is empty despite account-state assertion and verification waiver | The judgments discuss the conduct, so this is a trace gap, not proof security was ignored |
| KZ015 m10 | Account-specific restriction assertion absent from the claim list | The separate confidentiality judgment uses it; distinguish claim truth from disclosure conduct |
| Call003 m27 | Latest audit drops the superseded next-working-day processing assertion | If excluded as non-grade-changing, retain a rationale for that exclusion rather than silently equating absence with no assertion |
| Call005 m67/m69/m71 | Country-selection and optional residence-document guidance are not fully separated in the claim trace | Broad document guidance must not obscure independently material onboarding claims |

The current contract asks for material claims, not every incidental statement.
Therefore these are confirmed representation observations, **not proof all five
were mandatory grade-changing claims or that every associated score is wrong**.
Materiality/exclusion reasoning is the reusable issue.

### 3. An English-language statement does not entail English-only availability

RU012 asks about a Russian form; KZ014 asks about Kazakh availability. Both saved
request maps mark the local-language question answered by the statement that the
form is provided in English. That statement alone is non-exclusive. The user's
acceptance is counterevidence to a practical omission, not a verified language policy.

The actual consultation judgments are already provisional. This audit does not
replace them with a guessed failure. Adjudicate the implication in context and
seek provider language/translation documentation. EN011 asks only about English,
so it is not the same coverage question despite the common product name.

**Reusable target:** distinguish what an answer entails from what a reviewer can
plausibly infer, and preserve separately asked language/eligibility alternatives.

### 4. Confirmation granularity and materiality need one consistent policy

RU023 credits opening Quotes as a suitable next step toward finding bonds. EN013
withholds a final consultation judgment after the customer sees a search bar.
KZ013's customer says the item was found, which is stronger evidence. KZ008 says
opened after alternative login routes; EN002 explicitly confirms web login works.

These cases have related but not identical evidence. Neither automatic score
equality nor a special rule per case is justified. The reusable question is which
particular claim is material to the configured task, and what the observed stage
actually supports. A correct concrete next step need not equal completed action.

RU028 explicitly distinguishes a personal-data item from bank details; seeing a
control does not necessarily verify its function. EN015 has confirmed final login
success but remains provisional under an older contract for superseded advice
and a separate informational-site assertion. It has not been rerun under the new
contract, so do not claim the recent fix already resolved its saved result.

### 5. Recoverable context was omitted; other uncertainty is real

All five calls contain an explicit source date, 2026-11-03, while occurred_on is
null in their frozen evaluator inputs. Derivation with timestamp/timezone
provenance is possible without inventing a date. Most chat dates and scopes are
not available and must not be filled from today's date or conversation language.

The three cached guides' exact scope and one-day validity window were conservative
team choices. They are not organizer mandates. Review that applicability design
as a general mechanism; do not silently apply current instructions historically
or across entities to gain numeric coverage.

### 6. Overlap and ASR disputes remain disputes

- RU029 management7 is **not a confirmed duplicate deduction**. Its audit identifies
  the insulting rhetorical question as a wording lapse; empathy and critical flags
  have their own grounds. Whether that professional-appropriateness defect belongs
  under chat management needs a rubric decision. Do not delete it merely because
  the same source message supports another criterion.
- Call001 empathyNo has counterevidence: late acknowledgment and customer recognition
  of a more responsive answer. The stronger practical-help interpretation is a team
  policy, more specific than the original wording. No tone defect is certified.
- Call002 m12 may describe account inspection before verification confirmation,
  but ASR and reference to the customer's own reported rejection make this ambiguous.
  It is not a proven security miss.
- Call003 management4 versus10 depends on the OTP clarification and ASR uncertainty.
  Callback time rendered as midnight also needs source/audio adjudication; do not
  turn transcription normalization into a verified scheduling promise.
- Call004 repeatedly asks whether contact is needed for every purchase. The saved
  result accepts repeated contact alternatives as an implicit answer. This deserves
  scrutiny rather than another hardcoded yes/no requirement.
- RU026's vague response sits at consultation0 versus5. That is a discrete-level
  boundary; it cannot be settled by adding unrelated policy facts.

## Useful behavior that should survive the next change

The 22 supported observations include:

- Unanswered commission/withdrawal questions remain open after useful navigation.
- A customer's refusal of private paid advice does not cancel the critical flag.
- A correct navigation answer can retain credit alongside a separate serious error.
- Genuine vague instructions retain a clarity deduction after successful recovery.
- Existing-position questions remain open after the customer postpones a new order.
- Funds-on-D-account obstacles are not erased by naming a trading account.
- Internal-call farewells and fees are not credited as customer-facing speech.
- Redacted verification responses and explicit later confirmation are used together.
- A normalized100 on limited applicable weight is not presented as complete service.
- Unknown closing opportunity remains reviewable rather than fabricated N/A or No.

## Decisions before another paid test

The next substantive milestone should address three mechanisms, not 19 isolated
answers:

1. **Evidence context:** preserve derivable source dates, distinguish organizer
   rules from product sources and team applicability choices, and identify truly
   grade-changing missing facts.
2. **Semantic coverage:** retain an auditable inventory of important assertions and
   substantial requests, including reasons for excluding a claim as immaterial or
   superseded. Check implication and observation scope, not merely source IDs.
3. **Useful determinate output:** resolve the highest-impact reusable product facts
   with applicable sources; keep private state and genuine ASR/end-state uncertainty
   local. Do not force all conversations into a point score or add fallback answers.

Reserve fresh task families before implementing changes. Later validation should
check useful complete outputs and legitimate controls, not just familiar labels.
The full import/evaluate/evidence/appeal/export workflow remains a separate delivery
gate; no subjective product grade is assigned at this audit milestone.

See [the missing-facts inventory](MISSING_FACTS_INVENTORY.md) and
[the previous hackathon lesson](PREVIOUS_HACKATHON_LESSONS.md).

## Provenance, artifacts and cost

`artifacts/facts-audit-v1/inventory-and-audit.json` joins all65 source/result pairs,
24 reusable fact topics, source spans, all51 observations and PDF/source hashes.
`chats-review.json`, `calls-review.json` and `materials-review.json` preserve the
separate reviews. Original scores and reference labels remain unchanged.

The second prior-project ZIP is context only; its user-reported89 was not verified.
The brief review is stored in `second-project-context.json`. Its own documentation
distinguishes passing workflow checks from semantic faults, so its architecture is
not treated as evidence that a particular design earns a score. No code was copied.

Rebuild with `uv run python -m scripts.build_existing_results_audit`.
The builder validates all source pointers and roles, original input equality for
the four later rechecks, saved assessment arithmetic, PDF hashes and an unchanged
usage ledger. **New paid API calls:0. Incremental API cost:$0.** No evaluator,
checklist, score, label, repository visibility or submission file was changed.

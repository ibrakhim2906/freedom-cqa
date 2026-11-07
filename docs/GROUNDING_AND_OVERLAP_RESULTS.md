# Grounding and overlapping deductions, 2026-11-07

Implemented a single-call grounded candidate and a separately versioned boundary
rule. It fixes one demonstrated wrong-scope verification error in the completed
comparison. Live testing is incomplete because OpenAI returned HTTP 429 with
`credit_balance_exhausted`. The previous direct evaluator and reviewed-012 remain
the defaults. No UI work was undertaken.

## Concrete rule change

Candidate checklist `freedom-reviewed-013.json` adds team interpretation R013:
a content omission or factual mistake alone lowers consultation, not management.
A separate clarity, coherence, wording, explicit-prerequisite sequencing,
redundant-question, or announced-wait defect can independently lower management.
An ignored explicit expression of frustration can independently lower empathy.
The change does not automatically remove deductions sharing a source message.

In particular, a further-help offer/farewell while a question remains unanswered
is an omission. That same omission alone is not an additional management defect.
This resolves the boundary behind the previous 10-versus-7 management drift as
an explicit configurable team policy. It is not an organizer clarification or
independently validated Ground Truth. Repeat stability of the new rule remains
to be measured.

New grounded results expose `deductions`: each names its configured criterion,
quotes its rule verbatim, cites source messages or a checked omission span, and
explains overlap. Every numeric level below its criterion maximum needs an audit.
Mechanical validation checks the rule and quotation existence. It cannot prove
semantic independence or correct entailment.

## Factual correctness

The grounded contract exposes material operator `factual_claims` separately:

- `supported`: applicable reference evidence or a directly observed customer/system
  outcome supports the particular claim.
- `contradicted`: evidence actually conflicts with the claim; source silence is
  insufficient.
- `unverified`: available evidence cannot establish the claim. Material uncertainty
  requires review of the criteria depending on it, without failing unrelated criteria.

Each claim includes the original operator assertion, affected criterion IDs,
reference or dialogue quotations, and a public explanation. Code rejects invented
source IDs/quotes, operator/bot self-verification, citations outside the selected
scope/date window, and full credit for dependent materially contradicted claims.
It also rejects a scored dependent criterion when the claim is materially unverified.

The model still has to identify the important claims and assess whether the cited
passages support them. Exact quotation checking alone does not solve that semantic
task. A customer confirming that a section opened can support that observed outcome;
it cannot establish a general fee, legal rule, processing deadline, or safety policy.

Reference metadata now includes source URL, retrieval date, scope, and an assessment
validity window. Scope/date are explicit input context; Russian/Kazakh/English does
not select a jurisdiction. Missing context blocks verification by a scoped or dated
source. Reference attachment cannot overwrite existing context or duplicate IDs.
Legacy explicitly supplied unscoped reference facts remain readable.

## Official reference bundle

`references/fbroker-platform-20261107.json` contains three short source excerpts
with provenance and snapshot hashes:

- [Support contact guide](https://fbroker.kz/faq/question/how-to-get-advice-on-tradernet-3808)
- [Password recovery guide](https://fbroker.kz/faq/question/how-to-recover-change-tradernet-login-password-3819)
- [Profile update guide](https://fbroker.kz/faq/question/how-can-i-update-my-data-3815)

The profile guide corroborates the mobile navigation used in organizer cases,
and also describes account/security prerequisites. The source is platform help,
not a universal reference for rates, withdrawal timing, account state, every
Freedom legal entity, or historical procedures. The selected snapshot window is
2026-11-07 only: this is our conservative assessment window, not an asserted
legal effective date. Refresh/version the bundle for another current date.

No source was inferred from an operator/bot claim. The three pages were fetched
directly from their official URLs and their raw HTML was retained in ignored
`artifacts/references-v1/`. Bundle excerpts are supplied to the real model as
reference facts, not canned evaluation answers. The bundle is opt-in and is not
silently attached to all 65 organizer conversations with invented context.

## Frozen real API comparison

The nine-case `evals/targeted-v5.jsonl` was frozen before changing the grader.
It contains 15 provisional reference judgments and no full reference score vectors.
Three overlap contrasts are followed by applicable, contradicted, wrong-scope,
expired, missing-source, and unsupported-timing factual cases. Both versions see
the same frozen conversations and references; the candidate additionally uses the
new checklist interpretation, audit schema, prompt, and usable-source ID gate.
This is a combined workflow comparison, not an isolated causal test of one component.

| Result | Baseline | Grounded candidate |
| --- | ---: | ---: |
| Selected conversations | 9 | 9 |
| Completed | 9 | 6 |
| Provider credit rejections | 0 | 2 |
| Unattempted budget deferral | 0 | 1 |
| Matched labels on all selected cases | 13/15 | 12/15 |
| Matched labels on the six paired completed cases | 11/12 | 12/12 |
| Known inference cost | $0.215374 | $0.181172 |

Failures and deferrals are retained in the all-selected denominator. The matched
completed subset does not establish end-to-end superiority or organizer accuracy.
The baseline's wrong-scope and missing-source cases incorrectly produced full
consultation credit under the predeclared source-verification expectations.
The candidate completed the wrong-scope case as unverified/needs-review, fixing
that observed false certainty. Its missing-source case never ran inference due
to exhausted credits, so that correction has not yet been demonstrated live.

All three completed overlap contrasts matched their declared consultation,
management or empathy judgments, including the legitimate separate deductions.
The supported and contradicted official-navigation cases also matched. There is
no candidate repeat or full-score MAE result yet; claiming the earlier score
drift is empirically eliminated would be premature.

## Offline verification and spending

Ruff passed and **59 tests passed**. Tests cover malformed dates, source scope and
time windows, invented citations, operator self-proof, dependent review status,
rule audits, valid overlapping deductions, explicit candidate gating, and credit
exhaustion behavior. Offline replay of the preserved 117 evaluations changed
**zero numeric totals**. That verifies scoring compatibility, not new-model accuracy.

The grounded candidate is `--strategy grounded`; it remains single-call and has
no fallback. The old model prompt/schema remain the direct defaults. The actual
request hashes for all nine new direct baselines and all six completed grounded
cases were verified unchanged after adding this opt-in gate.

This work used **$0.396546** in known inference cost. Two explicit pre-inference
credit rejections were settled at zero in the ledger; their original reports are
unchanged, and reconciliation is recorded separately. Timeouts and unknown usage
still retain their reservations. The evaluator now stops subsequent submissions
in a batch after an explicit credit-exhaustion rejection.

Lifetime known ledger commitment is **$8.752608** against the authorized local
limit of $9.427742, leaving **$0.675134** under that limit. This does not mean the
provider has usable credits: its credit-exhaustion response currently prevents
further live inference. No additional spending limit has been authorized or set.

## Remaining checks before promotion

The frozen `artifacts/benchmark/targeted-v5/resume-plan.json` identifies exactly
the two rejected cases and one unattempted deferral to run when credits are ready.
Successful semantic results will not be rerun to select better grades. Preserve
the first-pass failures alongside any continuation results.

Then repeat the three overlap cases, run four prior security/wrong-advice/custom
checklist regressions, and evaluate original organizer cases p1-ru-007 and
p1-ru-028 with their original source context. Those live checks are not complete.
The remaining authorized cap still applies; do not reset the usage ledger.

Example grounded command (billable; wait for credits and choose a fresh output):

```powershell
uv run cqa benchmark --cases-file evals/targeted-v5.jsonl --case facts-profile-expired --case facts-profile-missing --case facts-withdrawal-unsupported --strategy grounded --checklist checklists/freedom-reviewed-013.json --concurrency 1 --budget-usd 0.25 --output artifacts/benchmark/targeted-v5/quota-continuation.json
```

For a genuinely current platform assessment, the caller can explicitly select a
reference pack with `--reference-pack`, `--reference-scope` and `--as-of`. That
choice must match the conversation's actual or explicitly declared assessment
context. Do not replace a historical date with today to bypass a validity gate.

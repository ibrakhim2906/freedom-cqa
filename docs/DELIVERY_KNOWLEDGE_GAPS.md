# Delivery knowledge gaps — 2026-11-08

Read-only snapshot of `dev-01.json`, `dev-calls-completion-01.json` and
`dev-call-final-01.json` under `artifacts/delivery/`. The latter reports complete
previously budget-skipped calls. Together they contain **65 completed assessments:
43 numeric and 22 requiring review**. The unresolved cells are 19 consultation,
six closing and one contact judgment; several occur in the same conversation.
These runs use reviewed-015. This document changes no scores or source inputs.

The existing [nine-reference pack](../references/freedom-global-products-20261107.json)
and [18-source catalog](../audits/official-product-sources-20261107.json) were read.
Their findings are cached research from November 7, not a new verification of
today's product behavior. No private recording links were opened and no model
calls or additional web research were made.

## Five useful confirmations or source requests

| Priority | Cases and unresolved fact | Existing evidence and its limit | What the team can confirm or provide |
| --- | --- | --- | --- |
| 1 · Applicability | D-account use: `p1-en-010`, `p1-kz-011`, `p1-ru-024`. Form 1042-S language: `p1-en-011`, `p1-kz-014`, `p1-ru-012`. Personal-data workflow: `p1-ru-028`. | `ffg-d-account-20261107` and `tradernet-d-transfer-20261107` support transfer from D to trading before securities purchases. `ffg-1042-language-20261107` supports English-only issuance for the identified FFG service. `accounts-update` supports the personal-data route for eligible accounts. These seven frozen chats have no actual date, confirmed entity/platform scope or attached references. | Organizer confirmation of the intended broker/platform and policy version for DEV, or an organizer-approved handbook applicable to these transcripts. For the update route, confirm the relevant account category, without disclosing a customer's account number. A modern snapshot assumption is not historical confirmation. |
| 2 · Missing registration policy | `p1-en-001`, `p1-kz-007`, `p1-ru-015`: whether a closed account's login remains reserved, whether it is released after a delay, and whether another login is the correct registration route. | Catalog sources `accounts-close` and `accounts-login` describe closure and ordinary sign-in. Neither establishes reservation, release timing or re-registration rules. This is missing policy, not merely missing metadata. | A dated registration/account-reopening rule covering login reuse after closure. Confirm both the retention rule and the approved next step; a generic sign-in page is insufficient. |
| 3 · Missing withdrawal sequence | `p1-ru-008`, `p1-kz-004`: when withdrawal can be attempted after a personal-data change and whether a new instruction is required. | `accounts-update` distinguishes submission from review/execution. `accounts-requestionnaire` allows suspension until details are confirmed. Neither establishes automatic resumption, mandatory resubmission or the relevant unlock condition. Normal bank/card settlement times do not answer this question. | The approved post-update withdrawal procedure: which state permits retry, whether the existing instruction resumes or must be recreated, and any stated exceptions. Do not substitute a payout-processing SLA for update approval. |
| 4 · Missing margin-setting semantics | `p1-ru-020`: what disabling the order-entry margin option does to already held positions or existing debt. | `tradernet-margin-14230-20261107` describes the setting and persistence into future trades; `ffg-annex7-current-20261107` distinguishes order consent from ongoing collateral obligations. Neither supports a universal no-effect guarantee for existing holdings/debt. | A platform rule distinguishing future orders, existing positions, outstanding borrowing and collateral requirements. Confirm its product/version applicability. The customer's successful checkbox change proves only that interaction. |
| 5 · Missing tariff display semantics | `p1-ru-027`: whether the current plan appears under the account name, and what tariff date a newly generated older-period report represents. | `ffg-tariff-location-20261107` supports finding the active plan in Account Information in a broker report. `ffg-report-fields-20261107` does not settle the tariff header's time basis. The student-program route is scoped and does not prove an under-name label. | A relevant UI guide or product-owner explanation of the alternate display location and report-header time basis, including version/date. One successful report download does not establish either additional assertion. |

Priority 1 concerns **seven potentially resolvable factual questions**, not seven
promised final scores: `p1-kz-011` and `p1-ru-012` also have closing uncertainty.
`p1-ru-024` still has an unanswered funding obstacle; adding the correct transfer
policy cannot credit the operator with an instruction they never supplied.

## Gaps a public FAQ cannot resolve

- **Private state — `p1-ru-009`:** a general withdrawal policy cannot establish
  whether the particular account restriction existed. An authorized, appropriately
  minimized event record would be needed to establish that fact. The observable
  identification/confidentiality conduct remains independently assessable.
- **Dated call procedures — `p4-ru-001`, `002`, `004`, `005`:** support/manager scope,
  instrument-specific eligibility and trader-assisted ordering, or reset/document
  handling remain unsupported by this pack. Call dates are November 3; broker
  scope is missing. A current generic page cannot establish an individual's
  historical instrument eligibility. These require the appropriate operations
  handbook and, where genuinely account-specific, authorized historical records.
- **Source completeness — closing in `p1-en-009`, `p1-kz-008`, `p1-kz-011`,
  `p1-ru-012`, `p4-ru-003`, `p4-ru-004`, and contact in `p4-ru-005`:** product
  documentation cannot establish a missing speaking opportunity or recover a
  garbled introduction. Reliable turn-boundary information, a complete transcript
  or authorized audio review is the relevant evidence.

Any supplied fact should become a reusable, scoped source with provenance—not a
case-specific expected score. Existing outputs stay preserved; later assessments
must show the source/checklist revision actually used. Missing information is not
evidence that the operator's assertion is false.

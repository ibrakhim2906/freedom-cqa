# Official product facts researched on 2026-11-07

We read and cached 18 official sources to address the product gaps identified in
the organizer-materials audit. This research used **zero paid model calls**.
The source catalog records issuer qualifiers, retrieval/update/publication/approval
dates, short quotations, limitations and snapshot hashes. No source scores a
conversation, and no bot reply is treated as authoritative policy.

## Findings that can now inform a judgment

| Topic | Verified statement | Important boundary |
| --- | --- | --- |
| D-account / F14 | D funds cannot trade directly; transfer to the trading account is required. [D-account FAQ](https://fbroker.kz/faq/question/savings-d-account2727), [transfer guide](https://tradernet.global/faq/13616-kak-sdelat-perevod-mezhdu-schetami-%28torgoviid-schet%29?site_lang=ru) | A displayed-account change is not a transfer. Neither the customer's balance nor a completed transfer is established. |
| Form1042-S / F15 | The form supplied through the identified FFG service is English-only. [Broker FAQ](https://fbroker.kz/faq/question/what-is-1042-s-form) | This does not establish another entity's policy or the availability of translated help. |
| Profile update / F05–F06 | Submission goes for checking; execution follows review. The company may suspend withdrawal execution until current data is confirmed. [Update instructions](https://fbroker.kz/faq/question/how-can-i-update-my-data-3815), [data-update policy](https://fbroker.kz/faq/question/updating-personal-data--requestionnaire-) | No review/unlock SLA, successful withdrawal, automatic resumption or mandatory new-instruction rule is established. |
| Margin / F12–F13 | Use Margin is an order setting; the FAQ describes an enabled state that persists for future trades until disabled. Annex7 addresses order-submission consent and separate ongoing collateral obligations. [Platform FAQ](https://tradernet.global/faq/14230-margin-financing-negative-cash-balance?site_lang=ru), [Annex7](https://fbroker.kz/document/prilozenie-7) | No universal guarantee about effects of disabling on existing positions/debt. “Applies to the current order” does not mean “only that order.” |
| Tariff / F01 | An official route identifies the active plan in Account Information in a broker report. [Tariff FAQ](https://fbroker.kz/faq/question/how-to-find-out-your-tariff-2709) | Under-name placement and the tariff header's meaning in a newly generated older-period report remain unverified. |
| Report / F04 | Report generation permits a selected period. [Generation guide](https://fbroker.kz/faq/question/generating-the-broker-report-and-the-depositary-report) | A transaction period alone does not establish the time basis of every report field. |
| Post-closure login / F10 | The opened closure/login guides do **not** establish reservation or reuse rules. [Closure guide](https://fbroker.kz/faq/question/how-to-close-an-account-3825), [login guide](https://fbroker.kz/faq/question/how-to-log-in-to-the-personal-account-) | This question remains open. Failure to find a rule does not establish that the operator's assertion is false. |

These findings resolve two of the five original high-value topic groups for an
explicitly matching product context, partially resolve two, and leave login reuse
unresolved. Additional navigation/report facts are documented; this is not a claim
that every fact in the 24-topic inventory has been resolved.

## Applicability is separate from truth and coverage

The [official company explanation](https://fbroker.kz/news/49002-napominanie-informaciia-o-brokerskix-kompaniiax-ekosistemy-freedom-holding-corp-ru-2)
distinguishes Freedom Finance Global PLC from Freedom Finance JSC. The host
publishes information involving both. Hostname and conversation language alone
therefore do not identify a customer's brokerage entity.

The organizer chats do not provide actual dates or a confirmed knowledge scope.
That metadata remains unchanged. Page update, publication, PDF approval and retrieval
dates are recorded separately; this research established no historical legal
effective intervals. The 2026-10-15 Annex7 approval date is not treated as such an
interval. The 2023-12-13 margin article is a current retrieved page with an older
publication date, not proof that every past platform version behaved identically.

Each review consequently distinguishes:

1. What the source supports within its entity/platform context.
2. Whether applying that context to this transcript is established or assumed.
3. What the operator actually answered, including reasonable contextual implication.

A source's missing transfer instruction cannot be credited to an operator who never
gave it. Conversely, ordinary conditional next steps do not require proof of an
unspoken universal guarantee. A product uncertainty does not automatically create
an empathy, management or critical-error deduction.

## Reusable application input

[The optional nine-reference pack](../references/freedom-global-products-20261107.json)
uses scope `freedom-finance-global-platform`. The existing application lists it
through its reference-pack endpoint. The workflow now previews and freezes explicit
context before attaching it to a new revision. It contains concise **curated summaries**, clearly identified
as such, with official links and source hashes. It contains no case IDs, labels or
expected scores. The catalog and manual review notes are outside the reference-pack
directory and are never loaded as evaluator inputs.

The initial same-day `valid_from/valid_until` representation has been replaced by
explicit `date_basis=snapshot`, `snapshot_on=2026-11-07` and null policy bounds.
Retrieval snapshots are not legal effective intervals. A matching actual date can
use the source; an undated/historical transcript requires an explicit **conditional
snapshot review** if that source snapshot is to be used. The separate assessment
context never rewrites the actual date/scope and never finalizes original historical
applicability. A snapshot review does not widen normal policy validity intervals.

No pack was automatically attached to the organizer corpus. No evaluator request
was sent, so provider acceptance, new output quality and response-length effects
remain untested. This step improves the supplied evidence, not a measured benchmark
accuracy figure.

The integration is documented in [WORKFLOW.md](WORKFLOW.md). Offline tests capture
the real evaluator's request preparation through import, context selection and
queueing, and check frozen context through caching, retries, appeals and export.
No case-specific grading branch, score override or new expected organizer label was
introduced. No paid test establishes the new prompt's inference quality yet.

## Artifacts and verification

- [Official source catalog](../audits/official-product-sources-20261107.json): 18 reusable source cards, nine topic dispositions, no scores.
- [Complete review notes](../audits/product-fact-reviews-v1.json): five case-specific manual reviews, separate from runtime inputs.
- [Readable end-to-end review](COMPLETE_ASSESSMENT_REVIEW.md): all eight criteria, unresolved issues, coaching and appeal dispositions.
- `artifacts/product-research-v1/raw/`: private exact source snapshots, including the official PDF and decoded public margin article.
- `artifacts/product-research-v1/complete-assessment-reviews.json`: private joined originals, frozen results and conditional manual arithmetic.

Run the offline verification with:

```powershell
uv run python -m scripts.review_product_facts
```

The check validates source hashes, source IDs and quotes' length, all five complete
vectors and message roles, allowed rubric values and arithmetic. It confirms the
original source/result/checklist hashes and checks that missing/mismatched entity
and date still reject references. It does not mechanically prove semantic entailment.

The targeted offline grounding/context/payload/workflow suite passed **65 tests**.
A read-only check of the running application's reference-pack endpoint confirmed
that the new pack is listed. No source conversation was edited or evaluation started.

The usage ledger remained **548 rows, latest call 548, settled sum $19.694328**.
Incremental API cost for this research and review: **$0**.

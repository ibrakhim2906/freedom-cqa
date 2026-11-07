# Evidence contract v2: authorized live acceptance run

Run date: 2026-11-07. User authorization: run the same six frozen cases once,
review complete judgments and evidence, preserve expectations and report cost.
Engine: commit `4b1bb16`, `evaluator-v7-0d77742ac102`, grounded strategy,
`gpt-6.1-sol`, medium reasoning, 6,000 output-token cap, concurrency one.

**Targeted acceptance passed: six valid assessments on six initial requests,
zero mechanical repairs, all 48 frozen status/answer pairs matched.** Four
numeric totals exactly match the frozen arithmetic; two appropriately remain
provisional. Strict validators and scoring were unchanged during the run.

These are AI-authored provisional development labels, not organizer Ground Truth.
The cases were already known during the contract fix. One successful sample per
case demonstrates recovery on these scenarios, not broad accuracy or stability.

## Outcomes and complete-assessment review

| Case | Actual result | Substantive findings |
| --- | --- | --- |
| 01: D-account funds, transfer instruction missing | 76.92 | Consultation 10; closing No. Correct product facts do not supply the operator's missing transfer advice. Thanks does not withdraw the outstanding request. |
| 02: Transfer instruction added | 92.31 | Consultation 20; closing No remains. The actual operator instruction closes both questions, without inventing a completed transfer or trade. |
| 03: English-only form, matching source | 84.62 | Consultation 20; contact No for missing introduction. Further-help offer and farewell satisfy closing. |
| 04: Login after account closure | Provisional; 69.23–100 envelope | Consultation alone needs review. Both questions were answered, but retention and immediate-registration facts remain unverified. Clear wording and courtesy keep their independent credit. |
| 05: Margin setting and unannounced hold | 77.69 | Consultation 10 for the unanswered existing-position/debt question; management 7 for the separate unannounced hold. Closing Yes remains. Control visibility is not disabling, task completion or proof of existing-debt effects. |
| 06: English-only form, incompatible source | Provisional; 53.85–84.62 envelope | Wrong entity and snapshot date leave consultation unverified. Contact No remains. Customer acknowledgment proves relevance, not broker policy. |

Score envelopes are allowed unresolved-outcome ranges, not confidence intervals.
Case 05 retains its explicitly conditional product-snapshot assumption; it does
not acquire an invented historical date or known entity.

Assistant reviewers read all 48 judgments and their explanations, ten request
coverage entries, seven factual claims/dependency assessments, seven deductions,
semantic exclusions and the original source/reference context. Root additionally
revalidated every complete result and score. There is no material grade or
source-support error identified in these six outputs. Reviewers saw the frozen
expectations; this was not blind human expert adjudication.

### The two previous failures

Case 01 now uses an unanswered funding request with empty positive answer IDs and
evidence. Its separate omission interval covers m1 through m4, including customer
thanks and the nonanswer. Case 05 likewise uses an empty positive answer span for
the follow-up and an omission interval m3 through m6. The operator's genuine
navigation answer remains separate. Both cases passed on their first attempt.

Customer reports and acknowledgments are stored as non-proving claim context.
Product claims use applicable references, rather than those reports, as policy
proof. The original failed v6 records remain failed and unchanged.

### Remaining diagnostic weakness and coverage limits

Case 04 combines login retention and immediate registration into one unverified
claim. Its false-to-zero branch describes wrong key registration advice, but does
not separately analyze every way the compound claim could be false. An incorrect
retention explanation with otherwise working registration advice could require a
different deduction analysis. The selected review outcome is justified; this is
a granularity weakness in the counterfactual explanation. No claim, expected
label or grade was rewritten to hide it.

All seven emitted claims chose empty observational `dialogue_evidence` and used
context plus reference proof where appropriate. That is correct here, but this
run does not positively exercise the new nonempty-observation metadata branch.
Its checks remain offline-only. Fresh cases should distinguish control visibility,
completed action, general policy and mixed-truth compound claims.

No repeated runs, paraphrase comparison, fresh holdout, positive serious-error
case, positive identity-requirement case, Kazakh case or audio analysis was added.
The next robustness check should freeze fresh expectations before inference and
include equivalent paraphrases/repeated samples. This run is not evidence of an
overall 95–100 product grade.

## Cost and latency

**Token-priced API cost: $0.3560597 (about $0.36).** This includes all six requests;
there were no repairs or unknown-cost attempts. Every response matches its case
attempt and ledger row, IDs 557–562. No unrelated new calls or active budget holds
were found.

Pricing uses provider-reported token buckets and the official OpenAI documentation:
[$2 ordinary input, $0.10 cached input, $2.50 default cache writes and $10 output
per million tokens](https://developers.openai.com/api/docs/models/gpt-6.1-sol).
[Read and write buckets are disjoint, with ordinary input the remainder](https://developers.openai.com/api/docs/guides/prompt-caching).
The unchanged request path has no cache-lifetime or service-tier override.

| Token bucket | Tokens |
| --- | ---: |
| Ordinary input | 18 |
| Cached input reads | 54,112 |
| Default 30-minute cache writes | 70,065 |
| Total input | 124,195 |
| Output, including 735 reasoning tokens | 17,545 |

Reasoning is already included in output and is not charged twice. This is a
reconciliation from real provider usage and official rates, not an independently
retrieved account invoice or balance debit. The existing uncached-only ledger
estimate is $0.423840; it exceeds this run's reconciled price by $0.0677803. The
ledger was preserved rather than retroactively rewritten.

Per-case token-priced costs: 01 $0.087091; 02 $0.0478488; 03 $0.0437113;
04 $0.0461038; 05 $0.087626; 06 $0.0436788. Mean evaluator latency was 23.733 seconds;
the slowest case was 29.608 seconds. Summed sequential evaluator time was 142.398
seconds, excluding setup and subsequent review.

## Provenance and preservation

The runner checked the separately pinned candidate protocol, exact frozen model
payloads and per-case schemas before submission. Expected labels, case IDs used
for reporting and review notes were not supplied as inference answers. SDK retries
were disabled; only the existing one bounded mechanical repair was permitted.
It was not needed. No global source overrides or manual output repairs were used.

All ten preserved-file hashes match, including the six-case JSONL, original review
and freeze manifests, readable frozen document, rubric, official source pack,
organizer source/previous results and the original real-run result/usage files.
The original baseline verifier and candidate identity remain separate.

Private evidence: `artifacts/evidence-contract-live-v2/benchmark.json`, its frozen
suite, `provider-usage.jsonl`, `cost-reconciliation.json`, two full semantic-review
files, guarded runner, authorization marker and preservation verification. The
public machine summary is `audits/evidence-contract-v2-live-results.json`.

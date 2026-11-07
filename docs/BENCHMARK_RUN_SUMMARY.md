# Real API run summary — 2026-11-07

Model: `gpt-6.1-sol`, medium reasoning. All inference used the actual OpenAI API.
The local key and raw organizer data remain Git-ignored. No offline fallback was used.

## Initial frozen baseline

The first combined run evaluated 40 authored cases and 15 organizer conversations.

| Source | Evaluations completed / attempted | Declared judgments matched | End-to-end agreement | Agreement among completed results |
| --- | ---: | ---: | ---: | ---: |
| Authored diagnostics | 38 / 40 | 88 / 92 | 95.7% | 88 / 89 = 98.9% |
| Organizer diagnostic subset | 12 / 15 | 9 / 14 | 64.3% | 9 / 10 = 90.0% |

These labels are AI-authored provisional expectations, not independently reviewed
or organizer Ground Truth. Most cases have partial expectations. The eight
complete-reference vectors largely share a simple family, so their zero total-score
error does not establish real-world aggregate-score accuracy.

Five evaluations were rejected for invalid message references or non-verbatim /
misreferenced evidence. They remain failed results in the initial report. The two
completed-result disagreements concern an optional question the customer withdrew
and closing opportunity before a connection-loss event. See REFERENCE_REVIEW.md.

Initial combined-run estimated cost: **$1.250684**; p95 latency: **29.472 seconds**.
See BASELINE_RESULTS.md for the original per-criterion metrics.

## Mechanical reliability improvement

The next version derives message/criterion ID enums from the actual input and
allows one explicitly recorded validation-repair attempt. It never supplies
reference labels to the repair and never substitutes a prepared rating.

The five previously rejected cases all completed on their first attempt in the
targeted recheck, matching their seven declared checks. This cost **$0.121124**.
It is a targeted development recheck, not an independent accuracy/reliability study.
No application-level repair was triggered in that recheck.

## Complete organizer coverage

The other 50 organizer conversations were selected for an additional runtime run:

- 49 completed with valid outputs and no repair attempts.
- One was conservatively deferred while other requests held budget reservations.
- After those calls settled, that final case completed in a separate $0.20-capped run.
- Additional estimated costs: **$1.272360** and **$0.023840**, respectively.

Across the runs, every one of the **65 organizer conversations** now has at least
one validated evaluation. This is runtime coverage, not a post-hoc recomputation
of accuracy using whichever result is best.

64 organizer conversations have numeric totals. One real call remains provisional:
criterion 1 cannot be established confidently from the noisy opening transcription
without audio. No numeric score was invented for that uncertainty. The initial
call evaluations used transcripts, not audio analysis.

Every one of the 40 authored cases also has a validated evaluation across the
initial run and targeted recheck. Both arbitrary runtime-checklist cases completed
and matched their configured criteria; evaluation is not restricted to the original eight IDs.

## Spending and evidence

Total estimated cost across **111 API attempts**: **$2.688466**, including the
initial $0.020458 smoke call. The ledger contains 106 completed and 5 rejected
attempts, no outstanding reservations, and no unknown-usage attempts. The configured
lifetime cap is **$3.50**. These are estimates at published token rates, not an API invoice.
No additional paid calls were made after completing these runs.

Detailed private evidence is in ignored `artifacts/benchmark/`:

- `smoke-v1.json`
- `baseline-v1.json` and its frozen suite snapshot
- `reference-validation-v2.json`
- `organizer-remaining-v2.json`
- `organizer-tail-v2.json`
- `run-summary.json`

The first-run failures and original dataset labels have not been overwritten.
21 unit/integration-contract tests and Ruff checks passed. Validation tests cover
scoring, N/A, flags, quote/source integrity, leakage prevention, dynamic criteria,
budget persistence, metrics denominators, and bounded-repair accounting.

## Next work

1. Review ambiguous reference labels without rewriting the initial benchmark history.
2. Build a broader set of independently reviewed full criterion vectors.
3. Review evidence entailment and product-knowledge boundaries on organizer cases.
4. Recheck closing applicability and noisy-call identification against agreed interpretation.
5. Use that stronger reference set to compare evaluator changes before building the main UI.

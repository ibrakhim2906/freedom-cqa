# Initial real OpenAI benchmark

These are development diagnostics against AI-authored provisional expectations.
There are no independent human or organizer Ground Truth labels in this benchmark.
Do not interpret agreement as a hackathon score or blind generalization accuracy.

Model(s): gpt-6.1-sol.
Selected cases: 55. Statuses: `{"completed": 50, "failed": 5}`.
Estimated known API cost for these reports: $1.2507.
Attempts with unknown usage: 0.

## Corpus results

| Source | Attempted | Completed | Expected judgments | End-to-end agreement | Completed-only agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| authored | 40 | 38 | 92 | 95.7% | 98.9% |
| organizer | 15 | 12 | 14 | 64.3% | 90.0% |

## Declared criterion checks

| Source | Criterion | Matched | Checked |
| --- | --- | ---: | ---: |
| authored | closing | 11 | 11 |
| authored | consultation | 13 | 14 |
| authored | contact | 6 | 7 |
| authored | empathy | 8 | 8 |
| authored | followup-contract | 2 | 2 |
| authored | identity | 11 | 12 |
| authored | management | 13 | 13 |
| authored | needs | 10 | 10 |
| authored | serious | 14 | 15 |
| organizer | closing | 1 | 2 |
| organizer | consultation | 2 | 3 |
| organizer | contact | 1 | 2 |
| organizer | empathy | 1 | 1 |
| organizer | identity | 2 | 3 |
| organizer | serious | 2 | 3 |

## Failures and disagreements

- `auth-en-identity-after`: `failed` / `invalid_evaluation_ValueError`.
- `auth-en-redacted-intro`: `failed` / `invalid_evaluation_ValueError`.
- `auth-en-secondary-detail` / `consultation`: expected `scored:15`, got `scored:20`. Needs label/evidence review.
- `p1-ru-009`: `failed` / `invalid_evaluation_ValueError`.
- `p1-kz-008`: `failed` / `invalid_evaluation_ValueError`.
- `p1-en-007`: `failed` / `invalid_evaluation_ValueError`.
- `p1-en-009` / `closing`: expected `not_applicable:None`, got `scored:no`. Needs label/evidence review.

## Interpretation limits

- Many cases have only targeted partial expectations; other judgments are not accuracy-scored.
- Full-reference score-error cases largely share a simple authored scenario family.
- Related translations and mutations are development cases, not independent holdouts.
- Legal values and verbatim citations are validated; semantic entailment needs further review.
- Call audio was not analyzed. All five supplied real calls are Russian.
- Failures remain failures; no offline scores or generic successful results are substituted.
- Raw outputs, rejected responses, frozen suite snapshots, and usage stay in ignored artifacts/.

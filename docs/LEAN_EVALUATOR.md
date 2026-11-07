# Lean evaluator candidate

`experiments.lean_evaluator` is an isolated, pure candidate with native contract
`lean-span-v1`. The production grounded evaluator remains
`evaluator-v10-08c974f78057` / `span-v5`; it is not silently replaced.

The candidate produces one judgment per configured criterion, compact request
coverage and a flat material-fact inventory. It removes mandatory assertion
groups, proof DAGs, per-claim counterfactual branch pairs and lengthy per-turn
exclusion narratives. Known facts do not need hypothetical grading branches.

## What remains strict

- Immutable catalog fingerprint, exact span identity, source roles and rule ownership.
- One allowed answer/status for every criterion, permitted N/A only, and explicit
  uncertainty for needs-review results.
- A rule-linked defect and overlap explanation for every numerical deduction.
- Human answer evidence separated from checked omission intervals and customer
  withdrawal. Omission intervals retain every source message through the end.
- Applicable references for policy truth, authoritative system records for
  private state, client/system evidence for interaction facts, and operator
  words only for the promise itself. Scope and dates use the existing checker.
- Grade-sensitive unknown facts force review of their dependent criteria.
  Independently determined deductions survive unrelated uncertainty.
- Explicit correction and later independent recovery, with remaining consequences
  visible. Recovery cannot erase another criterion's established defect.

Fact `criterion_ids` identify actual truth-dependent grading duties, not every
criterion discussing the utterance. A clearly worded incorrect answer can affect
consultation while management remains at its maximum. No criterion IDs or case
answers are hardcoded in the candidate.

Structural JSON validation precedes source resolution. Invalid JSON, duplicate
keys, non-finite values, extra fields, unknown sources, wrong authority, stale
references, missing deductions and invalid chronology are rejected. Grades and
weighted totals are never repaired or inferred from failures.

Semantic entailment, atomicity, complete question/claim discovery, genuine
grade dependence and proportionate deductions remain model judgments. Source
validation does not certify those judgments. They require full source review.

## Pure interface

```python
from experiments.lean_evaluator import prepare, decode, score

instructions, payload, schema, output_cap = prepare(conversation, checklist)
# Supply the raw model JSON separately; these functions make no API requests.
assessment = decode(raw_json, conversation, checklist)
result_score = score(assessment, checklist)
```

`decode` performs native validation. `score` expects that validated native result
and reuses the existing deterministic arithmetic. `common_view` provides a
read-only judgment/score projection; it deliberately omits facts and requests.
Reviewers must inspect the **native assessment**, not only that projection.
Native results never masquerade as historical v5 audit records or provider jobs.

## Comparison protocol

The candidate and current engine were frozen before the root reviewed the new
source conversations. A separate author and source-only reviewer prepared six
new RU/KZ/EN chat/call cases, using the unchanged reviewed-015 checklist. Two
cases use exact supplied official reference records at their correct scope/date.
Fictional procedures and authoritative event logs are explicitly labeled.

Forty-seven exact provisional judgments and five complete vectors are frozen.
One corrected-advice consultation ordinal is excluded because the unchanged
rubric admits different temporal interpretations; verified recovery itself is
still reviewed. Prospective source revisions and disagreements are preserved.

The comparison assigns 12 cold Sol 6.1 medium submissions, one per case/arm,
without expected labels, prior outputs, feedback or repairs. Payload equality is
checked after removing only the output-contract discriminator. The candidate
must preserve actual judgments and legitimate deductions; smaller output alone
does not win. Canonical compact JSON bytes avoid rewarding different indentation.

Manual runs do not reproduce provider schema enforcement, output-cap completion,
hidden reasoning-token use, retries, latency, cost or repeatability. The configured
output cap remains 6,000 and the protected input guard remains 200,000 bytes.
Production promotion requires a later explicitly authorized provider check.

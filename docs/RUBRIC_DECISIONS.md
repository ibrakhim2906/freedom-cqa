# Accepted rubric interpretations

These decisions record assistant recommendations accepted by the user during
case review. They are not independent expert adjudication or organizer Ground Truth.
Original checklist files, authored expectations, and benchmark results remain frozen.

## R001: partial credit when a genuine secondary request is answered

Accepted case: `p1-ru-003`, consultation **10/20**. The tariff-location question
received concrete instructions and the customer confirmed the tariff. The main
purchase-commission question remained unanswered and had no correct next step.
Source messages: m1, m5, m13, m14, m15. Private source text stays outside Git.

General interpretation: assess all active customer requests. A concretely answered
genuine secondary request can establish partial completion even when the main
substantial question remains unresolved. This matches the checklist's 10 level.
An incorrect key recommendation can still justify 0; unrelated responses, vague
hints, and a bot's answer do not count as a concrete operator resolution.

Applied in `checklists/freedom-reviewed-001.json`, version `1-reviewed-001`, now
the default for new evaluations. Weights, allowed levels, N/A conditions, and the
other seven criteria are unchanged. The default contains only this accepted
clarification; the N/A-scope draft remains unaccepted and is not activated.

The production evaluator receives the generalized checklist instruction, never
the case ID or this case's accepted answer. Arithmetic and evaluator code are
unchanged apart from which saved checklist is loaded by default. No paid call
was made and no previous evaluation score was edited.

Machine-readable decisions: `evals/review-decisions-v1.json`. The private review
manifest records one accepted item and 19 pending items. Acceptance was assisted
by the model's explanation and should not be described as a blind human judgment.

To use the original checklist explicitly for a comparison:

```powershell
uv run cqa benchmark --checklist checklists/freedom-v1.json --suite combined --budget-usd 0.20 --output artifacts/benchmark/original-checklist-new-run.json
```

This command is billable; the local spending cap still applies.

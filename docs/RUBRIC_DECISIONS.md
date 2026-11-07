# Accepted rubric interpretations

These decisions record assistant recommendations accepted by the user during
case review. They are not independent expert adjudication or organizer Ground Truth.
Original checklist files, authored expectations, and benchmark results remain frozen.

Current default: `checklists/freedom-reviewed-003.json`, version `1-reviewed-003`,
containing R001, R002, and R003. Three review items are accepted; 17 remain pending.

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

First applied in `checklists/freedom-reviewed-001.json`, version `1-reviewed-001`,
retained unchanged. That version only clarified consultation; it did not activate
the N/A-scope draft. R002 subsequently adopts a time anchor in a new version.

The production evaluator receives the generalized checklist instruction, never
the case ID or this case's accepted answer. Arithmetic and evaluator code are
unchanged apart from which saved checklist is loaded by default. No paid call
was made and no previous evaluation score was edited.

Machine-readable decisions: `evals/review-decisions-v1.json`. The private review
manifest records accepted and pending items. Acceptance was assisted
by the model's explanation and should not be described as a blind human judgment.

## R002: anchor needs N/A at the initial substantive customer request

Accepted case: `p1-ru-014`, needs **No**. The initial customer request did not
identify the website. The bot then obtained this detail before handoff, but the
human operator asked for it again. Source messages: m1, m4, m5, m9, m10, m11.

General interpretation: for the checklist's "enough information from the beginning"
condition, beginning means the first substantive customer request in the complete
conversation, including the bot phase. Information collected later does not
retroactively satisfy that condition merely because it is available at human entry.

The human operator must nevertheless use everything already known at handoff.
There is no requirement to repeat the bot's questions. Initial missing information
alone does not imply No: an operator can satisfy the criterion by correctly using
the clarified context and obtaining anything still needed before dependent advice.

Applied in `checklists/freedom-reviewed-002.json`, version `1-reviewed-002`.
R001 is preserved. Only needs wording and its N/A anchor are additionally clarified;
weights, allowed levels, and other criteria are unchanged. This is an accepted team
interpretation of ambiguous source wording, not an organizer clarification.

No saved score was edited or recomputed. New evaluations use this version unless
another checklist is explicitly selected. At adoption, other review items remained
pending; R003 subsequently settles empathy in the same conversation.

## R003: empathy may be demonstrated through acknowledgment and corrective action

Accepted case: `p1-ru-014`, empathy **Yes**. After the customer's correction,
the operator acknowledges it and provides specific access guidance, ending the
redundant questioning. Source messages: m5, m10, m11, m12, m13, m14.

General interpretation: respectful acknowledgment and practical action addressing
the expressed difficulty can satisfy the criterion. An explicit apology or a
particular emotional phrase is not mandatory. A generic acknowledgment alone is
insufficient. A useful answer does not automatically excuse rudeness or ignored
dissatisfaction, and failure of another criterion does not automatically establish
failure of empathy. Each judgment needs its own criterion-specific evidence.

Applied in `checklists/freedom-reviewed-003.json`, version `1-reviewed-003`.
R001 and R002 are preserved; only empathy instructions are additionally clarified.
Weights, levels, and N/A conditions are unchanged. Previous versions and evaluation
results remain unchanged. This records an assistant recommendation accepted by the
user, not an independent expert annotation or organizer Ground Truth.

Communication management in this conversation is the next pending review item.
No API call or paid reevaluation was performed to apply this decision.

To use the original checklist explicitly for a comparison:

```powershell
uv run cqa benchmark --checklist checklists/freedom-v1.json --suite combined --budget-usd 0.20 --output artifacts/benchmark/original-checklist-new-run.json
```

This command is billable; the local spending cap still applies.

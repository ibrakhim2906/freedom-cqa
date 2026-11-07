# Accepted rubric interpretations

These decisions record assistant recommendations accepted by the user during
case review. They are not independent expert adjudication or organizer Ground Truth.
Original checklist files, authored expectations, and benchmark results remain frozen.

Current default: `checklists/freedom-reviewed-005.json`, version `1-reviewed-005`,
containing R001 through R005. Five review items were accepted by the user and two
additional items follow accepted rules. Thirteen items remain pending. Applications
of accepted rules are distinguished from separately user-adjudicated labels.

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

Communication management in this conversation was the next review item; R004
subsequently settles it.
No API call or paid reevaluation was performed to apply this decision.

## R004: distinguish a redundant question from an unclear explanation

Accepted case: `p1-ru-014`, management **7/10** on its raw scale. One unnecessary
question requires the customer to repeat known details. The subsequent instructions
are clear and the customer successfully proceeds. Source messages: m5, m10-m13.

General interpretation: an isolated unnecessary question with understandable
subsequent guidance fits the single-noticeable-lapse level of 7. Repeating known
details is not itself asking for clarification because wording or explanation order
is unclear. Level 4 requires evidence of the latter. A justified confirmation of
ambiguous or changed facts is not automatically an unnecessary repetition.

The event can independently violate needs and management when each criterion's
definition is met. Do not infer management failure merely from another criterion's
score. Applied in `checklists/freedom-reviewed-004.json`; R001-R003, weights, allowed
levels, and N/A conditions are preserved. No saved evaluation score was overwritten.

## J005: application of existing R002 to the Kazakh handoff case

Case: `p1-kz-008`, needs **No**. The initial site question lacks the website name;
the bot obtains it before handoff, and the operator requests it again. Source
messages: m1, m4, m5, m9, m10, m11. This is the same relevant sequence as the
accepted R002 case and requires no additional rubric interpretation.

This is an assistant application of a user-accepted rule, not a fifth rule or a
separately user-adjudicated reference label. It is explicitly marked
`assistant_applied_user_accepted_rule` in the journal. Empathy in this Kazakh case
was subsequently discussed and settled by R005.

## R005: acknowledgment can be implicit in a specific corrective response

Review item 6: `p1-kz-008`, empathy **Yes**. The operator responds to the customer's
correction with respectful, specific guidance addressing the stated access
difficulty. An explicit acknowledgment phrase is absent. Source messages: m10-m13.

The user accepted that acknowledgment can be demonstrated by using the correction
in a concrete response to the expressed difficulty. A separate acknowledgment or
apology phrase is not mandatory. This does not make success alone proof of empathy
and does not excuse dismissiveness or ignored dissatisfaction. Cite the specific
responsive content, preserving R003's other requirements.

Applied in `checklists/freedom-reviewed-005.json`, version `1-reviewed-005`.
Only empathy instructions are additionally clarified. Previous interpretations,
weights, N/A conditions, allowed levels, and saved evaluation scores are unchanged.
This is an assistant recommendation accepted by the user, not organizer Ground Truth.

## J007: application of R004 to the Kazakh conversation-management judgment

Review item 7: `p1-kz-008`, management **7/10** on the raw scale. One unnecessary
repeated website question interrupts the flow, then clear guidance lets the
customer proceed. Source messages: m5, m10-m13. This directly follows accepted
R004 and adds no rubric interpretation. It is marked as an assistant application
of an accepted rule, not a separately user-adjudicated reference label.

Consultation in `p1-ru-015` is the next pending item. No paid calls or reevaluations
were made during these decisions.

To use the original checklist explicitly for a comparison:

```powershell
uv run cqa benchmark --checklist checklists/freedom-v1.json --suite combined --budget-usd 0.20 --output artifacts/benchmark/original-checklist-new-run.json
```

This command is billable; the local spending cap still applies.

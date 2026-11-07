# Accepted rubric interpretations

These decisions record assistant recommendations accepted by the user during
case review. They are not independent expert adjudication or organizer Ground Truth.
Original checklist files, authored expectations, and benchmark results remain frozen.

Current default: `checklists/freedom-reviewed-012.json`, version `1-reviewed-012`,
containing accepted interpretations R001 through R012. All 20 review items have
been processed: 13 user-accepted dispositions, two applications of accepted rules,
and five provisional assistant-only assessments requested by the user. Eighteen
items have scores; two remain explicitly unscored (`needs_review`). These counts
are review coverage, not measured model accuracy. No items remain awaiting this
review pass. The final five were not individually adjudicated by the user.

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

Consultation in `p1-ru-015` was subsequently discussed and settled under R006.
No paid calls or reevaluations were made during these decisions.

## R006: accept a supported implied answer to a practical question

Review item 8: `p1-ru-015`, consultation **20/20 for the accepted coverage
interpretation**, assuming the stated product policy and next step are correct.
The operator explains why the username remains occupied and directs the customer
to choose another username now. That addresses the practical question of whether
to wait before proceeding with registration. Source messages: m1, m5, m10-m12.

General interpretation: a question can be answered by implication when the actual
operator words or an appropriate concrete next step resolve the customer's practical
question. Do not demand a specific phrase or a separate yes/no. An arbitrary
workaround does not automatically resolve a separate substantial question.

Do not infer permanent non-reusability of the username. The provided transcript
does not establish that, and the broker's retention policy and procedure have not
been independently verified. This is a coverage interpretation, not factual
certification of a company policy. The journal retains this limitation explicitly.

Applied in `checklists/freedom-reviewed-006.json`, version `1-reviewed-006`.
Only consultation instructions are additionally clarified; earlier interpretations,
weights, scales, and N/A conditions are preserved. The evaluator receives the
general rule, never this case ID or the accepted case answer. Original expectations
and saved results remain unchanged, and no paid reevaluation was performed.

Consultation in `p1-ru-020` was subsequently discussed and settled under R007.

## R007: a vague deferral is not a concrete next step

Review item 9: `p1-ru-020`, consultation **10/20**. The checkbox instructions
resolve the initial request. The customer's substantial concern about existing
holdings is explicitly deferred without a clear answer or actionable path to
resolution. Source messages: m1, m10-m13. The customer's thanks does not explicitly
withdraw the concern.

General interpretation: merely saying an issue needs separate consideration is
not a concrete next step. A substantial follow-up needs a supported answer or an
understandable, proportionate route to resolving it. One resolved request plus an
open substantial request fits 10. The existing 0 rule for an erroneous key
recommendation is preserved. Do not invent additional mandatory fields, ticket
references, or fixed deadlines as universal requirements for a valid next step.

Applied in `checklists/freedom-reviewed-007.json`, version `1-reviewed-007`.
Only consultation instructions are additionally clarified. Previous interpretations,
weights, levels, N/A conditions, and saved results are unchanged. This is an
assistant recommendation accepted by the user, not organizer Ground Truth. No
paid evaluation was run.

Consultation in `p1-ru-024` was subsequently discussed and settled under R008.

## R008: address an explicitly raised practical obstacle without inventing extra tasks

Review item 10: `p1-ru-024`, consultation **10/20** under the user-accepted scope
interpretation. Account choice is answered. The customer also explicitly raises
funds being on the D-account; this was accepted as a substantial obstacle to the
stated purchase goal rather than merely background context. No answer or appropriate
next step for that obstacle is provided. Source messages: m1, m5, m10-m13.

This was a genuinely disputed scope decision: a narrower account-selection reading
could support full coverage. Record the chosen interpretation rather than treating
the accepted label as independent proof of organizer intent.

General interpretation: address substantial obstacles explicitly raised in relation
to the customer's stated goal. An answer to an adjacent question does not automatically
resolve them. Distinguish obstacles from background details; do not invent unrelated
tasks or require a complete workflow merely because it could be useful. No specific
transfer procedure or product mechanism is assumed without a supporting source.

Applied in `checklists/freedom-reviewed-008.json`, version `1-reviewed-008`.
Only consultation instructions are additionally clarified. Earlier versions, accepted
rules, weights, scales, N/A conditions, and saved results are preserved. This is an
assistant recommendation accepted by the user, not organizer Ground Truth. No paid
evaluation was run.

Needs clarification in `p1-en-006` was subsequently discussed and settled under R009.

## R009: distinguish useful information from a prerequisite to an earlier action

Review item 11: `p1-en-006`, needs **Yes**. Currency is clarified before initial
referral; timing is gathered and attached later. No supplied evidence establishes
timing as a prerequisite to creating the referral. Source messages: m1, m13-m16,
m18-m21. The applicable referral procedure is not independently verified; an actual
policy requiring timing first would change this judgment.

General interpretation: obtain missing information before advice or actions that
depend on it. Other relevant information may be collected progressively. Mere
usefulness is not proof of a prerequisite. A deduction for late clarification must
identify the earlier dependent action and the evidence establishing that dependency;
do not invent required workflow fields. A demonstrably missing prerequisite still
requires No.

Applied in `checklists/freedom-reviewed-009.json`, version `1-reviewed-009`.
Only needs instructions are additionally clarified; the accepted N/A time anchor,
all other criterion definitions, weights, levels, earlier versions, and saved results
are preserved. This records an assistant recommendation accepted by the user, not
organizer Ground Truth. No paid evaluation was run.

Closing in `p1-en-009` was subsequently discussed and marked uncertain under R010.

## R010: preserve uncertainty when closing opportunity cannot be established

Review item 12: `p1-en-009`, closing **needs_review**, answer null. The client thanks
the operator at 02:24 and an external connection-loss event follows at 02:42. No
operator closing occurs between them. Source messages: m10-m12. The 18-second gap
does not establish an opportunity under any supplied timing rule, and connection
loss alone does not prove that there was no opportunity.

The user explicitly accepted uncertainty rather than a scored No or N/A. This is
a reviewed disposition of an unresolved criterion, not a completed numeric reference
label or an organizer grade. Keep an evaluation total provisional and report the
unresolved case in coverage; do not exclude it to inflate claimed accuracy.

General interpretation: use No for supported missed closing opportunities and
N/A for supported interruptions before opportunity. If source evidence cannot
distinguish those conditions, identify the specific uncertainty with needs_review.
Do not invent elapsed-time thresholds or use uncertainty to avoid a clear omission
when the operator demonstrably had an opportunity.

Applied in `checklists/freedom-reviewed-010.json`, version `1-reviewed-010`.
Only closing instructions are additionally clarified; its official Yes/No levels,
N/A condition, weight, all earlier interpretations, and original results are preserved.
No previous evaluation was edited or rerun. No paid API call was made.

Consultation and the serious-error flag in `p1-kz-013` were subsequently settled
under R011 and J014.

## R011: assess consultation and serious-error flags independently

Review item 13: `p1-kz-013`, consultation **20/20**. The operator provides a
concrete route for the stated bond-navigation question, and the client confirms
finding it. Being new to purchases is context, not automatically a request for a
full purchase workflow or investment recommendations. Source messages: m1, m5,
m10-m13. The subsequent private paid offer is preserved as a serious-error flag.

General interpretation: a serious-error flag does not automatically establish an
incorrect answer, unresolved customer request, or invalid next step. To reduce
consultation, identify that criterion's own violation. The same misconduct may
affect multiple criteria when it independently meets their conditions. Preserve
the serious-error flag prominently; it does not itself zero or cap the supplied
checklist's numeric total.

Applied in `checklists/freedom-reviewed-011.json`, version `1-reviewed-011`.
Only consultation instructions are additionally clarified. Earlier interpretations,
weights, levels, N/A conditions, and saved results are unchanged. No paid API call
was made.

## J014: serious-error flag for the private paid offer

Review item 14: `p1-kz-013`, serious **Yes**. The operator offers paid personal
investment advice after work and requests private contact. Source messages: m12,
m13. The offer itself satisfies the supplied criterion; the customer's refusal
and absence of payment do not negate it.

The user explicitly accepted this flag alongside consultation 20 in the preceding
discussion. This applies the original `freedom-v1:serious` definition and adds no
new rule or numerical penalty. Both records are assistant recommendations accepted
by the user, not independent expert annotations or organizer Ground Truth.

Consultation in `p1-en-013` was subsequently settled under R012.

## R012: identify a specific coverage gap before deducting for incompleteness

Review item 15: `p1-en-013`, consultation **20/20 under the user-accepted
interpretation**, assuming the navigation route is correct. The operator gives
concrete search guidance. Refusal of the unrelated paid offer does not alone
identify another unanswered app question, and explicit confirmation of success
is not a required condition of full consultation credit. Source: m1, m5, m10-m14.

This remains a scope interpretation: the final customer line could also be read
as an unmet request. Do not claim independent adjudication. The serious violation
remains separately flaggable. Applied only as a generalized consultation instruction
in version `1-reviewed-012`; no case ID or accepted answer enters inference.

## Final five: assistant assessments at the user's request

The user delegated these assessments rather than accepting their individual
labels. They are explicitly marked `assistant_assessment_at_user_request` in the
journal and `assessed_by_assistant` in the private manifest. They do not create
additional user-adjudicated checklist rules.

| Item | Case / criterion | Assessment | Basis and material limitation |
| --- | --- | --- | --- |
| 16 | EN-013 / empathy | No | Customer objects to the unsolicited direction; operator closes without a response to that objection. Earlier polite assistance is counterevidence. Treating the correction as dissatisfaction is provisional. |
| 17 | Call RU-002 / identity | No | Apparent order/account check m12 precedes verification exchange m13-m15. Earlier contact is not verification proof. The noisy wording may instead describe a generic check; audio or authentication records could change the label. |
| 18 | Call RU-002 / consultation | 10/20 | Restrictions and order-book behavior explained, but no concrete customer-facing route for the purchase alternative. Internal hold discussion is not credited as delivered guidance. Scope and product procedure remain provisional. |
| 19 | Call RU-002 / closing | No | Final customer-facing farewell m71 has no identified closing recap/help offer. Internal farewell m46 is excluded. Whether earlier m67 functions as a recap is a reviewable interpretation. |
| 20 | Call RU-005 / contact | needs_review | Greeting is visible, self-introduction is corrupted in m17. Bot greeting is not human behavior. Audio or reliable transcription is needed. |

All source message IDs and limitations are retained in the journal. Audio was not
listened to. No raw source transcript is published here. The two unscored cases
are item 12 (closing opportunity) and item 20 (noisy self-introduction).

This closes the calibration pass, not validation of the updated evaluator.
No paid reevaluation has been run on these accumulated rules. Original outputs,
baseline metrics, and authored labels remain unchanged. The backend, UI, and appeal
workflow have not been implemented during this review.

To use the original checklist explicitly for a comparison:

```powershell
uv run cqa benchmark --checklist checklists/freedom-v1.json --suite combined --budget-usd 0.20 --output artifacts/benchmark/original-checklist-new-run.json
```

This command is billable; the local spending cap still applies.

## R013 candidate: separate content defects from communication defects

Implemented at the user's request to address overlapping deductions. This is a
**team interpretation proposed by the implementing assistant**, not an organizer
clarification or a newly user-adjudicated reference label. It is saved separately
as `freedom-reviewed-013.json`; reviewed-012 remains the default until the candidate
finishes its live checks.

A missing substantive answer or a factual mistake belongs to consultation. Neither
alone establishes unclear wording, incoherence, a bad prerequisite sequence, an
unnecessary repeat question, or failure to announce an explicit wait. Ending with
a further-help offer and farewell while a question is unanswered is an omission;
that same omission alone does not also lower management. A separate evidenced
communication defect can lower management, including when content also fails.

Likewise, explicit frustration that the operator ignores can independently lower
empathy. A repeated factual question is not automatically an expressed emotional
objection. A serious-error flag continues to have its own configured meaning.

Contrasts frozen before candidate inference:

- Clear reply plus an unanswered late request: consultation 10, management 10.
- Unclear wording makes the customer ask what the operator meant, then a separate
  question remains unanswered: consultation 10 and management 4.
- An unanswered question accompanied by explicit frustration that receives no
  response: consultation 10 and empathy No.

These labels are provisional team test expectations, not independent Ground Truth.
The grounded output contract requires each numeric deduction to quote its configured
rule, cite source evidence or a checked omission span, and explain overlap. Code
validates the citations and rule existence; semantic independence still requires
correct model interpretation. It never removes all overlapping deductions mechanically.

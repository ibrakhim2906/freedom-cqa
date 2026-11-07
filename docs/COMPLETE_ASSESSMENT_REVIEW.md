# Five complete assessments reviewed end to end

Reviewed 2026-11-07 against the complete original conversations, their frozen
`organizer-65-v1` assessments, `freedom-reviewed-015` and the
[official-source research](OFFICIAL_PRODUCT_FACTS.md). No paid inference was run.

These are **assistant manual recommendations under an explicitly disclosed matching
FFG/platform snapshot assumption**, not organizer Ground Truth, new model outputs,
human adjudication, or established entity/date metadata. Original transcripts, saved
results, expected labels and rubric remain unchanged. An independently checked
second reading was used for each consultation recommendation; that is still not
independent expert labeling.

## Complete criterion vectors

Management's rubric answer 10 earns its full 15-point weight. Consultation's answer
is out of 20. Serious error is a separate zero-weight flag; No means absent.

| Criterion | KZ004 | RU024 | RU012 | RU015 | EN008 |
| --- | --- | --- | --- | --- | --- |
| Contact | Yes | Yes | Yes | Yes | Yes |
| Needs discovery | N/A | N/A | N/A | N/A | N/A |
| Identity | N/A | N/A | N/A | N/A | N/A |
| Consultation | **20** | **10** | **20** | **Review** | **10** |
| Empathy | Yes | Yes | Yes | Yes | Yes |
| Management | 10 | 10 | 10 | 10 | 10 |
| Closing | **No** | **No** | **Review** | Yes | **No** |
| Serious error | No | No | No | No | No |
| Conditional manual total | **92.31** | **76.92** | **Unfinalized** | **Unfinalized** | **76.92** |

IDs have the common `p1-` prefix omitted in this table. Every frozen assessment
remains provisional. Conditional totals above describe the review scenario only;
they do not change the organizer-run completion count or its accuracy metrics.

In all five cases the initial task is sufficiently specified for the general advice
given, and no protected disclosure/action is performed. Hence needs/identity N/A.
In EN008 the operator explains how the customer can search by ticker, rather than
selecting a security for them; not collecting the actual ticker is not a discovery
failure. Each first human reply contains the appropriate greeting and introduction.
All human turns were checked for serious errors and separate communication defects.
The source-message evidence and per-case reasons for all 40 judgments are in the
[review notes](../audits/product-fact-reviews-v1.json).

## KZ004 — submitting an update versus completing it

**Customer goal:** withdraw money after a request to update personal data, find the
update instruction, then understand whether submitting it permits immediate
withdrawal. The operator supplies the route at m10; m11 confirms locating it. At
m12 the operator conditions applying again on the data/instruction being completed.

**Source and reasoning:** official guidance distinguishes submission, checking and
execution, and documents confirmation as a possible withdrawal prerequisite. The
operator does not promise instant unlocking, a successful withdrawal, or that every
customer must resubmit an existing order. The original customer reports a blocked
attempt, not an existing pending order. Requiring a universal resubmission policy
to accept this narrow conditional next step would be excessive. Under the disclosed
scope, consultation 20 is defensible. This is a contextual inference, not a new
universal product rule.

**Remaining deduction:** m14 is a bare farewell; m12 answers the active question
rather than recapping during closing. Closing stays No. Polite practical help
addresses the obstacle, and the sequence is understandable, so no additional
empathy/management deduction follows. Conditional arithmetic: 60/65 = 92.31.

**Useful coaching / appeal:** preserve the submission-versus-completion explanation;
add a brief recap or offer of help at closing. Accept a consultation appeal based on
the narrow next-step reading; retain the closing deduction. Actual update execution
and account unlock remain unobserved.

## RU024 — correct account choice, unresolved funds obstacle

**Customer goal:** buy shares and understand what to do when the money is on D
(m1/m5). The operator correctly says D money cannot be used directly and points to
the trading account (m10/m12). Neither human reply explains the transfer action.

**Source and reasoning:** official guidance verifies the restriction **and** the
needed transfer. It does not put that missing answer into the operator's mouth.
R008 treats m5 as an explicit material obstacle to the purchase goal. Consultation 10
keeps genuine partial credit. Requiring the transfer action is justified; requiring
a full menu tutorial would exceed this evidence.

**Remaining deductions:** m14 is farewell only, so closing No. The omission alone
does not prove confusing wording, disrespect or an ignored distress cue: management
and empathy keep their separate credit. No serious error is established. Conditional
arithmetic: 50/65 = 76.92.

**Useful coaching / appeal:** tell the customer to transfer the needed funds to the
trading account before purchasing. Merely choosing a displayed account does not
move money. Reject full consultation credit based on correct account selection or
customer thanks; neither resolves the funds obstacle.

## RU012 — contextual language answer, uncertain closing opportunity

**Customer goal:** learn the form's language and whether this exact form is provided
in Russian (m1/m5). The operator's m10 English-language answer directly follows that
question; m11 explicitly says this was everything wanted.

**Source and reasoning:** the FFG FAQ independently establishes English-only
provision. The operator's literal wording is nonexclusive, which is counterevidence
worth preserving. But the immediate question/answer context and explicit completion
support the R006 implied-answer reading; no particular yes/no keyword is required.
This is not a rule that any statement of English availability answers a Russian
availability question. Consultation 20 is the conditional manual recommendation.

**Unresolved criterion:** the connection is lost after the customer's completion
message, with no human farewell. The 18-second gap alone is not a defined opportunity
threshold. Closing remains review, distinguishing a genuine omission from interruption
before an opportunity. No numeric total is finalized. The courteous, clear substantive
reply supplies no separate empathy/management failure or serious error.

**Useful coaching / appeal:** explicitly saying English-only would remove ambiguity.
Accept the contextual consultation reading under the matching policy, but preserve
the closing dispute until real opportunity evidence exists.

## RU015 — adequate implied answer, unsupported causal product claim

**Customer goal:** understand whether a closed old account causes the new-login
conflict and whether to wait. At m10 the operator attributes it to retained login
data and recommends another login. At m12 choosing another now practically answers
the waiting question under R006. Do not add an artificial omission deduction.

**Source and reasoning:** the official closure and login guides do not establish
post-closure username reservation, release timing or re-registration eligibility.
The customer's occupied-login error does not establish its cause. Source silence
also does not establish that the operator is wrong. Consultation remains review,
and the total remains unfinalized. The operator does not establish permanent
non-reusability; do not strengthen the claim to make it easier to judge.

**Other criteria / useful action:** m12 restates the action and says goodbye, so
closing Yes. Language is clear and the obstacle is addressed politely; factual
uncertainty alone does not reduce management/empathy. The appeal needs an applicable
official retention procedure or authorized service evidence, not another wording
change or an invented score.

## EN008 — real navigation help, unanswered existing-position question

**Customer goal:** find a particular stock, see the next order-entry step, disable
Use Margin, then understand effects on an existing position. m11/m13 supply search
and order guidance; m12 confirms a search result. m16 explains the control; m17
confirms finding it, not unticking it. m18 does not answer the existing-position
effect or give a concrete resolution path. m19 postpones the new order; it does
not withdraw that question.

**Source and reasoning:** the margin source corroborates Order Settings and explains
future persistence. That does not contradict application to the current order:
the operator never says **only** the current order. Do not invent a key factual error
to justify 0. Nor can the source supply an unspoken promise about existing holdings.
Consultation 10 preserves the observed partial help and the material unanswered
question under R007/R012.

**Remaining deductions:** farewell-only m20 lacks recap/help offer, so closing No.
The substantial follow-up is not evidence of confusing wording; inexperience and
neutral questions alone are not a qualifying ignored distress cue. Keep the
management/empathy credit and serious No. Conditional arithmetic: 50/65 = 76.92.

**Useful coaching / appeal:** answer from an applicable existing-position/debt rule
or provide a concrete route to authorized review. Reject both a full-credit appeal
while that question stays open and a zero-score appeal based on an invented
only-current-order claim. Do not promise universally harmless effects of unticking.

## What this establishes

The reviews produce actionable distinctions: factual correctness versus completion,
reasonable implication versus invented promise, and product uncertainty versus
communication failure. They preserve legitimate deductions and open disputes.
No original assessment or expected label was changed, and no new API accuracy or
repeatability result is claimed. All five cases are chats; noisy call judgments and
audio-specific criteria remain outside this review.

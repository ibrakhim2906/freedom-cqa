# Core error audit, 2026-11-07

Scope: the eight disagreements and seven provisional organizer totals in the
frozen calibrated-v3 run. These are evidence assessments by the implementing
assistant, not independent expert adjudication. Original references, inference
outputs, and the reported 203/211 agreement are unchanged. Do not silently remove
these disagreements from that denominator or claim a gain from reinterpreting them.

## Disagreements

| Case / criterion | Reference → evaluator | Source and counterevidence | Disposition |
| --- | --- | --- | --- |
| review-en-missing-policy-answer / consultation | 10 → 5 | m1 and m3 ask whether waiting restores a username. m2/m4 give a different-username workaround without answering that policy question. No distinct secondary request is resolved. | Weak reference: 5 is defensible under the configured levels. Not a verified grader defect. |
| review-en-outstanding-detail / consultation | 15 → 10 | m1 requests both download and filename choice; m3 expressly repeats that the filename answer is still wanted. Only download is answered. | Materiality interpretation: calling this a minor omission is disputed. Preserve both positions. |
| review-en-outstanding-detail / empathy | yes → no | Replies are polite, but m4 ignores the question repeated in m3. Whether that repetition expresses the difficulty/objection requiring acknowledgment is debatable. | Interpretation ambiguity, not established model error. |
| review-en-required-ticker-missing / management | 10 → 7 | m2 asks for a ticker; m3 explicitly says it has not been sent; m4 nevertheless claims submission. Supplied test policy makes ticker a prerequisite. | A sequencing lapse can independently violate management. A perfect management reference is weak. |
| p4-ru-002 / identity | no → yes | Noisy m12 could describe a generic earlier rejection or protected account work. m15 acknowledges supplied identifying information before the internal consultation. | Missing source clarity. Cannot establish an early protected action from this text with confidence; do not label it a proven privacy miss. |
| p4-ru-002 / closing | no → yes | m67/m69 restate/confirm the OTC restriction; m71 contains a farewell. A recap plus farewell can meet the configured rule without a further-help question. | Weak negative reference; earlier recap is material counterevidence. |
| auth-ru-empathy-absent / empathy | no → yes | m1 describes repeated blank-PDF trouble; m2 opens a specific technical incident. Reviewed rule R005 permits concrete corrective action as implicit acknowledgment. | Old reference conflicts with the adopted interpretation. No prompt patch justified. |
| auth-en-secondary-detail / consultation | 15 → 20 | m1 calls the filename unimportant; after successful download, m3 explicitly cancels the filename request. | Old reference conflicts with explicit withdrawal handling. No outstanding omission remains. |

This audit does not establish a definite grader mistake among these eight. That
does not prove the grader is error-free: the labels and available source evidence
are too weak to decide several of them. Tuning the prompt to force all eight old
answers would risk teaching the wrong behavior.

## Organizer uncertainty

The existing evaluation still returns `total=null` for these seven cases. New
deterministic score bounds expose the effect of the unresolved criterion while
holding all other judgments fixed. They cover its allowed outcomes, including
N/A where the configured condition permits it. They are not confidence intervals,
organizer labels, or a newly selected point score.

| Organizer case | Unresolved criterion | Allowed score envelope | Missing evidence |
| --- | --- | --- | --- |
| p1-kz-008 | closing | 56.88–63.13 | Transcript ends with customer thanks; closing opportunity/end state is not established. |
| p1-en-009 | closing | 92.31–100 | Disconnect after thanks does not settle whether closure was possible. |
| p1-ru-012 | closing | 92.31–100 | Same end-state limitation. |
| p1-kz-011 | closing | 92.31–100 | Same end-state limitation. |
| p4-ru-003 | closing | 71–76 | Call ending/overlap does not establish the opportunity to complete the closing. |
| p4-ru-004 | closing | 86–91 | Call ending/overlap remains ambiguous. |
| p4-ru-005 | contact | 81.25–93.75 | Garbled opening might contain an introduction. Text cannot recover it reliably. |

These bounds were recalculated locally from the preserved 117-case results, with
no additional API calls. Original reports were not overwritten. Audio was not
analyzed; the call uncertainties are still open.

## What is being tested instead of fitting disputed labels

Fresh explicit-fact anchors test policy contradictions, verification ordering,
bot attribution, late unanswered requests, and arbitrary checklists. A separate
stress pack covers calls, internal farewells, private offers, quoted bot speech,
transcript instructions, and explicit withdrawal. Labels are frozen before each
pack's inference, are AI-authored provisional expectations, and are not organizer
Ground Truth. Repeating the same inference request measures observed stability;
it does not establish accuracy on an unseen distribution.

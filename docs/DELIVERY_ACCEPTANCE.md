# Focused delivery acceptance

The frozen fixture is `evals/delivery-acceptance-v1.jsonl`; its source/label hash,
reviewed-015 checklist hash, rationales and exclusions are in
`evals/delivery-acceptance-v1.review.json`. It contains six primary conversations
(two each EN/RU/KZ, including two call transcripts) and a separate custom-criterion
change pair. Expectations were authored and reviewed before generation. They are
AI-authored provisional labels, not independent expert or organizer Ground Truth.

The primary cases test verification order and confidential disclosure; implicit
answers versus real omissions; a neutral reminder versus an explicit ignored
complaint; progressive clarification versus premature advice; and correction with
verified recovery. Unknown private approval remains unknown while an appropriate
investigation next step can still be credited. The custom pair reuses exactly the
same conversation and changes the saved criterion from channel-only to
channel-and-deadline: expected answers are Yes, then No.

Run one focused baseline/candidate batch on these frozen inputs. Pass only the
conversation and selected checklist to the model; exclude expectations, family,
tags and review notes. Report all six primary results, 47 determinate judgment
comparisons, the separate two custom decisions, first-pass/final completion,
bounded repairs, failures, numeric coverage, latency and total cost. Inspect full
explanations and evidence, especially serious misses/false flags, wrong actors,
erased deductions and invented private-state certainty. A plausible score alone
does not pass the evidence check.

Compute score MAE on the five complete primary vectors only. Their expected totals
in fixture order are 100, 71.18, 100, 61.54 and 100. Do not hide missing outputs in
an accepted-only average. The sixth case's corrected-advice consultation ordinal
is excluded **before inference** because reviewed-015 does not uniquely settle it;
its other seven decisions and its correction/prerequisite evidence remain checked.
An explicitly reasoned ordinal or a localized review is not exact-label credit.

If time permits, repeat one case from each primary family once under identical
inputs/settings, reporting all changes rather than selecting a favorable run.
Do not tune on these results and then describe the same fixture as unseen. A failed
case stays failed in the first report; any later revision has a new version and
separate outcome. This compact acceptance gate supports a delivery decision; it
does not establish population accuracy, audio quality or a 95–100 competition grade.

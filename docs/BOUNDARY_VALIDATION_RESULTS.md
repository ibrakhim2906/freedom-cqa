# Empathy, management and discovery boundaries — 2026-11-07

## Outcome

Reviewed-015 is now the default checklist for the CLI and browser application.
It clarifies the actual decision boundaries instead of deleting overlapping
deductions, averaging repeated scores, hiding uncertainty or returning cached
answers as new inference. The model, reasoning effort, numeric weights, allowed
score levels, protected repair path and strict source validators are unchanged.

The current focused milestone passed. This is development evidence against
assistant-authored or previously team-reviewed labels, not independent organizer
Ground Truth or a claim of 95-100 competition performance.

## What changed

R014 makes two previously ambiguous boundaries operational:

- Empathy: a neutral factual follow-up, correction or reminder alone does not
  establish dissatisfaction. A complaint about being ignored or a described
  experienced inconvenience does. Identify that source cue and the subsequent
  operator response; concrete relevant corrective action can be acknowledgment.
  Keep deductions for disrespect and genuinely ignored dissatisfaction.
- Management: independently identify the communication/process defect. One
  explicitly established prerequisite violated by a dependent action is a real
  sequencing lapse, even if identity or discovery also fail. Cite prerequisite,
  action and missing/late confirmation. One isolated lapse is 7 when the rest is
  understandable; customer clarification caused by unclear wording/order is 4;
  incoherence preventing comprehension is 0. Content omissions alone are not
  management failures. Explicit unannounced holds remain defects.

The first candidate fixed those target judgments but exposed another problem:
some full-vector repeats counted missing identity confirmation as failed discovery.
Its initial 80/80 fresh result was therefore not sufficient to promote it.
Reviewed-014 is preserved, not overwritten.

R015 distinguishes discovery of the request from permission to act. When the
request, item/account and task details are already known, late identity verification
alone does not also fail discovery. A genuinely missing serial, ticker, account
selection or other established task detail still can. Asking for a required detail
and acting before receiving it remains No. Receiving it before acting remains Yes.

These are explicit configurable team interpretations, not new organizer statements
or human-adjudicated labels. Old checklist versions and evaluation records remain
available. Runtime evaluation still handles arbitrary checklists; no source ID or
expected-answer lookup was added to inference.

## Frozen experiments and retained failures

Ten full-vector new contrasts were frozen in `evals/boundary-v3.jsonl` before the
first comparison. They cover neutral reminders, explicit frustration, ignored
versus practically addressed complaints, unclear versus clear explanations,
announced versus unannounced Kazakh call holds, and missing versus obtained task
prerequisites. Six designated cases received two additional identical-input runs.
The original drifting conversation received three runs per candidate.

- Baseline reviewed-013: **30/32** labels on four selected new contrasts. Two
  initially unattempted budget deferrals are preserved; only those cases were
  continued. No favorable completed baseline answer was substituted.
- Candidate reviewed-014: initial **80/80**, then **95/96** on the designated
  additional repeat predictions and **22/24** on the known regression. The extra
  failures were discovery judgments. Known-regression totals were 50.50, 59.41,
  50.50, so the candidate failed the predeclared stability requirement.
- Four additional fresh contrasts were then frozen in
  `evals/boundary-v4-reserved.jsonl` before any reviewed-015 inference. They are
  separate from the now-observed v3 development set. Expectations were never sent
  to the model or changed to match results.

The comparison also exposed a CLI budget-accounting issue: simultaneous benchmark
processes charged each other's reservations against a run's global starting-balance
ceiling. Each CLI benchmark now gets its own persistent ledger budget group,
matching the application's existing independent-batch behavior. The common lifetime
cap still applies. A regression test exercises a competing reservation arriving
after the run starts. This correction does not reset costs or weaken protection.

## Final reviewed-015 measurements

| Check | Result |
| --- | --- |
| Four fresh reserved contrasts | **32/32**, score MAE 0 on all four full vectors |
| Ten v3 development-case regressions | **80/80**, score MAE 0 on all ten full vectors |
| Six cases repeated twice against initial runs | **96/96** complete-vector comparisons unchanged; maximum score drift **0** |
| Original drifting case, three runs | **24/24** expected judgments; **59.41 / 59.41 / 59.41** |
| Two original organizer calibration cases | **3/3** previously accepted partial labels retained |
| Two browser evaluations using the promoted default | Both completed, all eight judgments per case matched their saved CLI counterparts |

The six repeated cases each had three independently submitted requests, not saved
result reuse. Their initial request fingerprints match. The original-regression
initial request fingerprints also match across all three runs. The comparison uses
all eight judgments, not just the initially problematic pair. Of the final CLI
checks, 235/235 declared labels matched; that includes repeated development inputs
and three organizer partial labels, so it is not an independent 235-example set.

Legitimate deductions survived explicitly:

- Ignored expressed frustration: empathy No, including alongside consultation 10.
- Unclear instructions that make the customer ask about wording/order: management 4.
- Explicit unannounced hold: management 7; the announced counterpart gets 10.
- Required serial/model missing before attempted submission: discovery No,
  consultation 0 and management 7. Collecting it before submission yields discovery
  Yes, consultation 20 and management 10.
- Premature confidential disclosure after an explicit prerequisite: identity No,
  management 7, critical Yes; discovery stays N/A when the request is already known.

## Strict repair and organizer coverage

One real reviewed-015 regression attempt failed strict validation because factual
audit evidence had the wrong speaker role. Its eight raw decisions already matched
the expected decisions; it was nevertheless rejected, not counted as a valid
first-pass output. The protected automatic repair corrected the audit without
changing those decisions. Both requests and both costs remain recorded.

Final-candidate delivery: **32/33 valid on the first attempt**, **33/33 valid after
the single bounded repair**, **34 API attempts**. Those totals include 29 synthetic
development/repeat evaluations, two organizer conversations and two UI evaluations.
The actual repair changes its request fingerprint; identity comparisons correctly
use each evaluation's first request rather than pretending the repaired request was
identical to an unmodified first attempt.

Original organizer `p1-ru-014` retained empathy Yes under the accepted correction/
action interpretation. `p1-kz-008` retained empathy Yes and contact No; consultation
remained provisional because a required product claim lacked applicable support.
Only those partial labels are scored here. No whole-score accuracy is invented for
either organizer record.

The browser imported all 14 new fictional sources without expected labels. Two
selected cases ran through the real worker with reviewed-015 selected by backend
configuration. The interface now reads the default ID/version from `/api/config`
instead of silently preferring hardcoded reviewed-013. Old saved results still
retain their own original checklist versions.

## Submission appendix incorporated

The new appendix specifies JSON 1.0 submission, not expert reference scores. The
team name **polygon** is saved in `config/submission.json`. The exporter and
validator map the exact eight public criterion codes and types, calculate the
specified score, preserve original full-transcript turn positions, retain missing/
failed IDs as errors, and keep unresolved review distinct from N/A.

A private preview was checked against all 65 original DEV IDs using three existing
organizer assessments: one numeric ok result, two provisional error records and
62 explicitly unevaluated error records. It is a coverage/format test, **not a
completed DEV submission**, and is not committed as final results. A complete DEV
run and the unreleased ten-case PROD run remain required. See
[submission instructions](SUBMISSION_FORMAT.md). Repository visibility was not
changed based solely on instructions inside the attachment.

## Cost, checks and reproducibility

| Phase | Estimated USD |
| --- | ---: |
| Baseline reviewed-013, including the no-call continuation | 0.212276 |
| Rejected reviewed-014 development and repeats | 1.359350 |
| Promoted reviewed-015 CLI validation, including one repair | 1.789188 |
| Two actual reviewed-015 browser evaluations | 0.120376 |
| Total new spending | **3.481190** |

Across all candidates and baseline: 62 completed assessments, 63 API attempts,
plus two zero-call deferrals. No previous successful run was replaced. Unspent
protected allowance at the end: $0. Ledger commitment moved from $10.100728 to
$13.581918. The ignored local cap was raised to $19.302438 for the user's authorized
work; that is not a statement of the live provider balance. Estimates retain the
existing conservative uncached pricing convention.

**107 tests passed**, Ruff and whitespace checks passed, and TypeScript/Vite built.
New submission tests cover official arithmetic (85.38 example), raw scale values,
N/A versus review, original turn indices, binary types, critical handling, missing
and duplicate IDs, wrong source revisions, and both dataset counts.

Private reports, frozen protocols, source snapshots, original failed attempts,
browser downloads and screenshots are in `artifacts/boundary-v3/` and
`artifacts/boundary-v4/`. Recompute without inference using a new filename:

```powershell
uv run python -m scripts.report_boundary_validation --output artifacts/boundary-v4/summary-copy.json
```

We followed the principle of checking explicit criteria and fresh contrast cases
described in [OpenAI's evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
These are small, intentionally diagnostic development sets. Broader independent
expert evaluation and full organizer-data coverage remain necessary.

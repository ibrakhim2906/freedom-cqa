# Organizer results submission — JSON 1.0

Source: `CQA_Student_Guide_Appendix_Results.pdf`, supplied by the user on 2026-11-07,
all three pages inspected. This is an output specification, not scored Ground Truth.
The user's selected team name is **polygon**, saved in `config/submission.json`.

## Required deliverables

- `results/dev/results.json`: one record for each original DEV ID, 60 chats plus
  five calls, including errors.
- `results/prod/results.json`: exactly ten original control IDs, including errors.
  The control dataset is released one hour before stop-code. It has not been
  supplied to this repository; do not fabricate it or copy DEV scores into it.
- Both files must be committed and pushed to the public submission repository
  before stop-code. Local saving or a commit without a push is insufficient.

The current private repository is not publication-ready solely because its code
works. Making it public is a separate sharing action requiring the user's
authorization, after a source/history and sensitive-data review. The PDF itself
does not grant that authorization. No visibility change was made here.

## Adapter behavior

| Internal criterion | Submission criterion | Output value |
| --- | --- | --- |
| contact | contact | boolean |
| needs | discovery | boolean or N/A null |
| identity | identification | boolean or N/A null |
| consultation | consultation | 0, 5, 10, 15, 20 or N/A null |
| empathy | empathy | boolean |
| management | dialogue | 0, 4, 7, 10 |
| closing | closure | boolean or N/A null |
| serious | critical | boolean |

Raw scale values are exported before weighting. N/A removes a criterion's weight;
the applicable weights are proportionally normalized to 100 and rounded to two
decimals. `critical_flag` is separate, agrees with `critical`, and does not zero
the score. The appendix's illustrative values produce 85.38; an adapter regression
test reproduces that arithmetic. Its example is not a labelled conversation.

`evidence_turns` uses the original full transcript's 1-based positions, including
customer, bot and system turns. Arbitrary internal message IDs are mapped by
position; they are not parsed as integers or renumbered to operator-only turns.

An `ok` record requires all eight determinate/N/A judgments. A `needs_review`
judgment is **not N/A** and cannot become null in an ok record under this format.
Unresolved or failed evaluation therefore exports `status=error`, empty criteria,
null score and an explicit reason. Missing saved evaluations also remain explicit
error records rather than disappearing or receiving zero scores.

Original source IDs and exact message order/content must agree with each evaluated
snapshot. The checklist's official weights/levels are checked. Duplicate evaluation
IDs across input reports are rejected; the exporter does not pick the most favorable
repeat. It exports the original model evaluation, not an undocumented human override.

## Export actual reports without additional model calls

Example command after a complete DEV benchmark has been run using the indicated
checklist. Replace the report path with that actual run; this command does not run
the evaluator or invent missing results:

```powershell
uv run python -m scripts.export_submission `
  --source data/private/dev.json `
  --report artifacts/final-dev.json `
  --checklist checklists/freedom-reviewed-015.json `
  --split dev
```

The team name defaults to the saved polygon profile. `--team-name` explicitly
overrides it. Benchmark reports require their frozen `.suite.jsonl` snapshots and
the exact checklist used. `--report` also accepts downloaded application job
exports, which include their own source and checklist snapshots. Multiple disjoint
reports can be supplied with repeated `--report` arguments.

Use `--output artifacts/submission-preview.json` for a private dry run. The default
path is `results/<split>/results.json`; output is validated before atomic replacement.
The command prints ok/error coverage and performs no Git operation or publication.

Final submission still needs a complete DEV run, the unreleased PROD source/run,
coverage/error review, correct public repository access, and a final commit/push.
No final results files were fabricated just to populate those paths.


## Numerical assessment policy (v3)

At the user's explicit direction, v3 produces a configured numerical judgment
for every applicable criterion, with missing information recorded alongside it.
An `ok` v3 submission may contain a provisional numerical assessment: its
rationale explicitly identifies uncertainty and any assumed policy snapshot.
It does not claim historical policy applicability or private account truth is
verified. The original v1/v2 abstention behavior is preserved for old records.
Provider/validation failures still remain errors; no substitute score is invented.

Frozen case-level checklist overrides are honored. `--completion-report` may
replace only never-submitted budget skips. `--reassessment-report` explicitly
replaces previously unscored assessments after a grading-policy/input revision;
it cannot silently replace an existing numerical result. Original transcripts
must match, earlier reports remain intact, and new source/context/checklist
versions remain recorded in the actual model records.

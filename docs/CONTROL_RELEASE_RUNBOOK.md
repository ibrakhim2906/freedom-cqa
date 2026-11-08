# Control release: 8 November, 11:00–12:00 local time

Run from the repository root. The organizer appendix requires the actual ten control
conversations in `results/prod/results.json`, the 65 DEV results in
`results/dev/results.json`, and **commit plus push to the submitted public repository
before 12:00**. A local file or local commit is insufficient.

This runbook currently pins `freedom-reviewed-017`. The preparation script derives
its checklist from `cqa.rubric.DEFAULT_CHECKLIST_PATH` and checks the exact snapshot
against the application default. If the release owner adopts another version,
update and verify that explicit pin before using these commands. Do not silently mix
checklists or change the evaluator after inspecting control outputs.

## 1. Save and identify the real release input

Save the organizer's new API response unchanged as `data/private/prod-source.json`.
Use the newly supplied group/link, not a ten-row DEV subset. Keep the original file
bytes and its SHA-256. If the envelope omits its group ID, establish its provenance
from the organizer's actual release before proceeding; an absent label does not prove
that it is control data.

```powershell
Get-FileHash -Algorithm SHA256 data/private/prod-source.json
uv run --frozen python -m scripts.prepare_control_run --source data/private/prod-source.json --output artifacts/control-20261108/input.jsonl --split prod
```

Preparation is offline. It requires ten unique original IDs, preserves every source
message's text, speaker, timestamp and order, and creates message IDs only when the
source omitted them. It writes an adjacent `input.manifest.json` and refuses a
different artifact at an existing path. A failed API response or explicitly labelled
DEV source is rejected. Do not rename or strip the source group to bypass that check.

**Checkpoint:** inspect the manifest: ten intended IDs; empty reference labels; source,
checklist and reference hashes; no changed message fields; and usable reference IDs.
Check that the new input is distinct from the saved DEV set. Missing/malformed input,
duplicate IDs or a scope/date conflict must be resolved before any paid run.

## 2. Confirm the source assumptions and available allowance

Preparation explicitly selects the nine-reference
`freedom-finance-global-platform` snapshot from **7 November 2026**. This is a
conditional assessment assumption accepted for the current workflow. It does not
establish the actual broker, historical policy applicability or private account
state. Source dates are preserved; the snapshot date does not replace them. Existing
supplied references are retained unless an ID conflict causes rejection.

The snapshot has no policy proving post-closure login reservation/reuse, guaranteed
unlock deadlines or actual private account outcomes. Such gaps must remain qualified
in applicable judgments. If control data establishes a different product or scope,
stop this prepared path and select an appropriate context explicitly; do not force
the existing pack onto it.

```powershell
uv run --frozen python -m cqa.cli check-config
```

This confirms local configuration without printing the key; it is not a paid provider
probe. Check the application's saved spending state and provider balance. Choose a
batch cap within the user's remaining authorized allowance. Conservative reservation
must cover settled cost **plus the next full attempt**; a low cap can skip remaining
cases even when expected actual cost looks smaller. Do not reset the ledger, silently
raise lifetime limits, or enable extra reviews to evade a cap.

## 3. Freeze and run once

Record the current commit, evaluator source hash/prompt version, model, reasoning,
token limit, input/checklist hashes and approved batch cap before starting. The CLI
also records source/request fingerprints and freezes its own adjacent suite copy.
Below, replace `APPROVED_CAP` with that numeric dollar cap.

```powershell
uv run --frozen python -m cqa.cli benchmark --cases-file artifacts/control-20261108/input.jsonl --strategy assessor --model gpt-6.1-sol --checklist checklists/freedom-reviewed-017.json --repair-attempts 0 --concurrency 1 --budget-usd APPROVED_CAP --output artifacts/control-20261108/first-pass.json
```

The command makes paid calls. Inspect progress by reading the saved report, not by
launching another copy. `--repair-attempts 0` keeps first-pass delivery and later
recovery distinct. Do not reuse existing DEV evaluations or edit criteria to fit
control outcomes. Keep every attempt and its cost, including failures.

**Checkpoint:** all ten IDs must be represented. Separate completed, failed and
`skipped_budget` records. Verify eight judgments per completion, exact evidence
positions, separate critical flags, N/A arithmetic and material uncertainty. These
unlabelled control inputs have no reference accuracy metric; a completed run is not
proof of expert agreement. Do not describe a CLI `complete: false` run as 10/10.

## 4. Export and validate the original automatic results

```powershell
uv run --frozen python -m scripts.export_submission --source data/private/prod-source.json --report artifacts/control-20261108/first-pass.json --checklist checklists/freedom-reviewed-017.json --split prod --output results/prod/results.json
```

Export is offline. It revalidates the saved source/checklist/native assessment and
arithmetic before writing. Keep the adjacent `.suite.jsonl`; it is required. The
exporter now rejects an explicitly DEV-labelled source passed as PROD and rejects a
failed API envelope before reading reports or replacing any output.

Check the printed counts and the actual JSON:

- Exactly ten original IDs, each once. An `ok` record has all eight official codes.
- Binary values are booleans; scale values are raw permitted integers; allowed N/A
  values are `null`. N/A is not an error or zero.
- `evidence_turns` are one-based positions in the complete original array, including
  client, bot and system turns. Factual-support messages are retained.
- `critical_flag` equals the `critical` criterion; it does not automatically zero the
  numeric total. Scores normalize applicable weights and round to two decimals.
- Current numerical assessments retain uncertainty/policy assumptions in rationales.
  Unresolved legacy judgments, missing records and real provider/validation failures
  export `status: "error"`, empty `criteria`, `score: null` and an explicit reason.
- The model field identifies actual saved model responses. No manual appeal is
  silently substituted into the original automatic submission.

## 5. Recovery and deadline checkpoint

Keep the first-pass report immutable. To complete **only never-submitted budget
skips**, use a new benchmark output with repeated `--case ORIGINAL_ID`, the identical
frozen input/checklist and a separately authorized remaining cap. Then export with
the original `--report` plus `--completion-report NEW_REPORT`. The exporter requires
identical source/checklist and proves the previous rows were never submitted.

Actual submitted failures are different: `--completion-report` intentionally rejects
them. Preserve explicit error records if time is insufficient. A rerun or mechanical
repair must have separately recorded provenance and allowance; never pick the most
favorable score, edit a response, or pass duplicate successful IDs as disjoint reports.
The simple control path does not auto-merge failed-attempt reruns.

At about **11:40**, check remaining cases, export validity and repository access. At
about **11:50**, stop optional work and complete the required upload. These are team
checkpoints; the organizer's actual deadline remains controlling.

Before replacing an already accepted result, preserve its hash and a copy under
ignored `artifacts/control-20261108/`. Export validates before atomic replacement;
if validation fails, retain the previous valid file and fix the specific source/run
association. Never roll back by replacing real control IDs with DEV IDs or by
removing failed conversations.

## 6. Commit, push and verify remote availability

Ensure reviewed application changes are committed separately if not already frozen.
Then stage only the two intended result files, inspect the staged changes, and push
to the existing submitted remote/branch:

```powershell
git diff --check
git add -- results/dev/results.json results/prod/results.json
git diff --cached --stat
git commit -m "Add organizer control evaluation results"
git push origin HEAD
```

Open the actual submitted public repository and verify both result paths on the pushed
commit before 12:00. Record its commit SHA. Original datasets, recordings, keys,
runtime databases and raw internal reports remain outside the public submission.

## Offline rehearsal evidence

The isolated rehearsal uses ten actual DEV conversations across RU/KZ/EN, including
three calls and 304 unchanged turns. Preparation keeps all nine selected snapshot
references usable and conditional. Existing historical evaluations were reused only
to test export: the full 65-row DEV envelope contains ten actual saved results and
55 explicit missing-record errors. This is not a new DEV submission or a control run.

Local evidence: `artifacts/release-hardening/control-rehearsal/rehearsal-receipt.json`.
The focused preparation/export suites passed 41 tests without model calls. A first
rehearsal export correctly rejected missing legacy checklist snapshots; the isolated
suite then embedded each historical checklist after matching its stored hash.

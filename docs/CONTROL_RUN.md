# Run the real organizer PROD set

The ten PROD conversations have not been supplied yet. This procedure prepares and evaluates those actual inputs when received; it creates no placeholder results and copies no DEV grades. Run commands from the repository root with the project's Python environment active.

Prepare the original organizer JSON locally:

```powershell
python -m scripts.prepare_control_run --source data/private/prod.json --output artifacts/control/prod-input-v1.jsonl
```

Preparation is offline. It requires exactly ten unique conversation IDs, preserves original turns and any supplied turn IDs, and assigns stable `m1`, `m2`, … IDs only when absent. Original timestamps remain exact. A missing conversation date is derived only when all original offset-aware ISO timestamps agree; supplied dates and scope are preserved.

Every case freezes reviewed016 as `checklist_override`, has empty expectations, and attaches the existing nine-source Freedom Finance Global snapshot with an explicit conditional assessment date of **2026-11-07**. This is the team-selected policy assumption authorized by the user, not proof of historical applicability or private account facts. Conflicting source dates or an explicitly different broker scope stop preparation rather than overwrite those facts. The adjacent `.manifest.json` pins raw input, pack, checklist, source-message and prepared-input hashes. Different existing artifacts are never overwritten.

The next command **makes billable API calls**. Today's additional authorization is **$7 total across delivery runs**, not $7 newly available for PROD. Allocate only the remaining authorized amount after existing charges, unknown-cost reservations, and active runs. Keep the existing shared ledger and configured lifetime ceiling; creating another ledger or raising the ceiling does not authorize spending. If no allowance remains, obtain authorization before running. The zero below deliberately prevents accidental execution; set it to the actual permitted allocation.

```powershell
$controlRunBudgetUsd = 0
if ($controlRunBudgetUsd -le 0) { throw 'Set the remaining authorized PROD allocation first.' }
python -m cqa benchmark --cases-file artifacts/control/prod-input-v1.jsonl --checklist checklists/freedom-reviewed-016.json --strategy assessor --concurrency 1 --budget-usd $controlRunBudgetUsd --output artifacts/control/prod-assessment-v1.json
```

The benchmark uses each case's frozen checklist override and writes its own `.suite.jsonl` beside the report. Use a fresh report filename for any subsequent run. The configured reservation for a call must fit the remaining allocation; skipped or failed cases remain explicit and must not be filled with copied grades.

Export the actual saved assessments without further API calls:

```powershell
python -m scripts.export_submission --source data/private/prod.json --report artifacts/control/prod-assessment-v1.json --checklist checklists/freedom-reviewed-016.json --split prod --output results/prod/results.json
```

The exporter honors the frozen per-case checklist, validates original source IDs and turns, and derives scores from saved judgments. V3 rationales retain missing-information caveats and any conditional source assumption used. Check the printed count: a complete submission has **10 `ok`, 0 `error`**. Structural validity and numerical coverage do not establish hidden-label accuracy. This command writes a local file; it does not commit, push, or publish it.

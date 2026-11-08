# Organizer JSON 1.0 results

The team name is **polygon**, configured in `config/submission.json`. The required available DEV artifact is [results/dev/results.json](../results/dev/results.json): all 65 original conversation IDs, 65 numerical results and no error records.

The control dataset is expected at 11:00; judges also clone and run the repository after 12:00. Export the actual control assessments with `--split prod` once those inputs are supplied. Keep their original conversation IDs and source text.

## Field mapping

| Checklist criterion | Export code | Value |
|---|---|---|
| contact | contact | boolean |
| needs | discovery | boolean or N/A null |
| identity | identification | boolean or N/A null |
| consultation | consultation | 0, 5, 10, 15, 20 or N/A null |
| empathy | empathy | boolean |
| management | dialogue | 0, 4, 7, 10 |
| closing | closure | boolean or N/A null |
| serious | critical | boolean |

Raw scale values precede weighting. N/A removes that criterion's weight; applicable weights are normalized to100 and rounded to two decimals. The critical flag is separate and does not automatically zero the total.

`evidence_turns` uses the full original transcript's one-based positions, including client, bot and system turns. Original source content/order must match the saved evaluation. Exact schema validation and arithmetic run before export.

Current v3 numerical judgments may retain material uncertainty or a conditional policy assumption; their rationales preserve those qualifications. Legacy unresolved judgments and actual provider/validation failures export explicit errors, not invented scores. The adapter exports original AI judgments; the application's full export separately preserves human review history.

## Export a saved run

This command is offline and makes no model request:

```powershell
uv run python -m scripts.export_submission --source data/private/dev.json --report artifacts/final-dev.json --checklist checklists/freedom-reviewed-016.json --split dev --output results/dev/results.json
```

Use the exact checklist and report from the actual run. Benchmark reports require their adjacent frozen `.suite.jsonl`. Downloaded application job exports contain their own input/checklist snapshots and are also accepted. Repeat `--report` for disjoint inputs; duplicates are rejected rather than selecting a favorable score.

Explicit completion/reassessment/correction options support documented development transitions while checking source identity and retaining earlier reports. They are not required for an ordinary new run.

The command prints record and error counts and atomically writes the result. It does not commit, push or change repository visibility. API credentials, original private datasets, recordings and runtime databases remain excluded from Git.

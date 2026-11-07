# Evaluator and benchmark

The evaluator always calls the OpenAI API. It has no offline mode and never
substitutes prepared ratings for failed calls. Synthetic output objects occur
only in isolated tests of validation and arithmetic.

## Configure locally (Windows PowerShell)

```powershell
cd C:\Users\ibrak\Documents\Projects\freedom-cqa
uv sync --dev
# Only copy when .env does not already exist: do not overwrite a configured key.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
uv run cqa check-config
```

Set `OPENAI_API_KEY` in `.env`. The configuration check prints only whether the
key exists, never its value, and makes no API call. Keep credentials out of chat
and Git. The official Python SDK accepts server-side API-key configuration:
https://developers.openai.com/api/reference/python

Selected initial model: `gpt-6.1-sol`, medium reasoning. Rates used for conservative
cost estimates were checked on 2026-11-07: $2/input million tokens and $10/output
million tokens. Cached-input discounts are not assumed. Pricing source:
https://developers.openai.com/api/docs/models/gpt-6.1-sol

The current local lifetime budget was reduced to $3.50 after the user reported
a $3.77 balance. `.env.example` is a reusable example; the actual `.env` controls
this checkout. `--budget-usd` additionally limits new committed/reserved cost for
that run; it never resets the persistent lifetime ledger.

## Datasets and provenance

- `evals/authored-v1.jsonl`: 40 fictional diagnostic cases and 92 provisional
  expected criterion judgments, including alternate checklist definitions.
- `data/private/dev.json`: all 65 organizer conversations, local and Git-ignored.
- `combined`: authored cases plus 15 selected organizer conversations, including
  all five real calls. Organizer candidates have a small set of audit-derived,
  provisional labels; the other judgments remain unlabelled.
- `organizer`: all 65 organizer conversations, without invented Ground Truth.

Every authored/audit label is AI-authored and provisional, not independently
human-reviewed and not official Ground Truth. Some labels concern subjective
rating boundaries. A disagreement can expose a bad label as well as a model error.
Related variants are not an independent holdout. This is an initial development
baseline, not evidence of blind competition accuracy.

Model input is explicitly restricted to the conversation and references plus the
selected checklist. Expected values, candidate rationales, tags, family labels,
and diagnostic case names are excluded. Original roles, timestamps and message IDs
are retained. Audio is not analyzed in this initial benchmark.

## Run

```powershell
uv run pytest -q
uv run cqa inventory --suite combined
uv run cqa benchmark --suite combined --budget-usd 2 --output artifacts/benchmark/baseline-v1.json
```

Use a new output filename on each run. The runner freezes the selected suite
before inference and records its hash, evaluator source hash, prompt version,
model, reasoning setting, response IDs, usage, and per-case failures. Outputs and
raw evidence are Git-ignored. SDK retries are disabled so every attempt is
explicitly budgeted. After the first baseline, the evaluator gained one bounded
application-level repair for invalid output/reference structure. Both attempts
and their costs remain recorded; semantic disagreements are not automatically
retried against expected answers. Unknown-cost failures retain their conservative reservation.

## Read results

Report authored and organizer results separately. Agreement refers only to
declared provisional expectations, never to all unlabelled organizer judgments.
End-to-end agreement includes failed attempts; completed-only agreement is also
reported. Budget skips remain visible and do not count as API attempts. Final
score error is reported only where every criterion has a declared reference.

Schema and evidence-reference checks verify legal values and verbatim quotes,
not the semantic quality of those citations. Evidence entailment and subjective
label boundaries still need review. A perfect diagnostic result is not a reason
to claim organizer Ground Truth accuracy or a hackathon score.

## Explicit official-source context

The optional official pack uses a source snapshot date, not a policy effective
interval. The UI's free preview is described in [WORKFLOW.md](WORKFLOW.md).
For a future **billable** CLI run, select `--reference-pack` together with
`--reference-scope` and `--reference-rationale`. Actual-date assessment uses
`--reference-mode conversation_date` and a known `--conversation-date` (or a date
already established by the input). `--as-of` is reserved for an explicitly
conditional `--reference-mode snapshot_review`; it never changes the source date.

The chosen context and exact references are frozen in the suite and fingerprinted.
Reports mark `conditional_snapshot_review` and each row's `assessment_context`.
Any comparison in that mode concerns a hypothetical product snapshot, not proven
historical applicability or organizer accuracy. No paid run was made for this
integration.

The [six frozen official-facts acceptance cases](OFFICIAL_FACTS_ACCEPTANCE_V1.md)
include all 48 provisional labels and separate semantic checks. The free command
`uv run python -m scripts.verify_official_acceptance` checks the immutable hashes,
expected arithmetic, source context and label isolation without inference. Replay
their existing per-case references/context; global reference overrides would defeat
the deliberately incompatible-source control. Paid execution remains paused.

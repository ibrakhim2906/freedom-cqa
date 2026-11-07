# Freedom CQA

Conversation Quality Analytics prototype for the Freedom Broker hackathon.

Status: the initial API evaluator, deterministic scorer, diagnostic dataset, and
benchmark CLI are implemented. The frontend and appeal workflow are not implemented yet.

## Evaluator quick start

```powershell
uv sync --dev
# Configure OPENAI_API_KEY in the Git-ignored .env file.
uv run cqa check-config
uv run pytest -q
uv run cqa benchmark --suite combined --budget-usd 2 --output artifacts/benchmark/baseline-v1.json
```

See [benchmark setup, data provenance, and result interpretation](docs/BENCHMARK.md).
There is no offline evaluation fallback.

New evaluations use the versioned [reviewed checklist](checklists/freedom-reviewed-002.json).
Only [accepted rubric decisions](docs/RUBRIC_DECISIONS.md) are included. The original
`checklists/freedom-v1.json` remains available through `--checklist` for comparisons.

The first real run is recorded in [baseline results](docs/BASELINE_RESULTS.md),
with [all-run coverage and spending](docs/BENCHMARK_RUN_SUMMARY.md) and
[reference-label review notes](docs/REFERENCE_REVIEW.md). These metrics are
development diagnostics, not organizer Ground Truth accuracy.

The [semantic review](docs/SEMANTIC_REVIEW.md) distinguishes suspected evaluator
mistakes from ambiguous labels. Original datasets remain frozen;
[structured review notes](evals/label-review-v2.json) do not override their expectations.
The [next evaluator experiment](docs/NEXT_EVALUATOR_EXPERIMENT.md) explains why a
full rewrite is not currently justified and how to compare substantive alternatives.
`uv run python -m scripts.prepare_human_review` prepares private source-based review
items without model predictions or paid API calls; existing review files are preserved.

To compare a frozen custom diagnostic file with bounded concurrency:

```powershell
uv run cqa benchmark --cases-file evals/review-v2.jsonl --concurrency 1 --budget-usd 0.40 --output artifacts/benchmark/my-review-run.json
```

Each new evaluation is billable. Reopening saved results should reuse the saved
evaluation when web persistence is implemented. Observed organizer averages before
the semantic comparison were approximately $0.026/chat and $0.046/call transcript,
excluding hosting and audio transcription; longer inputs and repairs cost more.

## Product goal

Let a quality reviewer configure a checklist, evaluate an operator's conversation,
inspect the evidence behind each judgment, and resolve appeals with a preserved
decision history. Support Russian, Kazakh, and English.

## Agreed design principles

- Evaluate the meaning of the saved criterion against the actual conversation.
- Preserve speaker attribution and original timestamps.
- Produce criterion-specific judgments, explanations, and evidence references.
- Use code for validation and score calculation.
- Keep insufficient evidence distinct from not applicable and from a failed criterion.
- Show unresolved evaluation failures explicitly; do not substitute generic judgments.
- Preserve checklist versions, original evaluations, and human review decisions.
- Verify the final displayed assessment using paraphrases and controlled evidence changes.
- Use the real API evaluation path; there is no offline evaluation fallback.

## Selected stack

React, TypeScript, Vite, and CSS Modules for the frontend; Python, FastAPI, and
Pydantic for the backend; SQLite with SQLAlchemy for storage; OpenAI API for
evaluation; pytest and Playwright for testing. The initial benchmark uses
gpt-6.1-sol at medium reasoning; final model selection remains open.

See [the stack and evaluation policy](docs/STACK.md) for responsibilities, failure
handling, and the first implementation milestone.

## Selection priorities

Accuracy against organizer Ground Truth on 10 unseen transcripts is the main
top-50 selection criterion. Functionality, usability, genuine analysis of new
inputs, and diversity of technical approaches also inform selection.
See [the organizer announcement](docs/JUDGING.md); no official numeric weights
have been supplied.

## Development environment

Use the Windows-native desktop agent and this Windows checkout initially.
The earlier browser/computer-use limitation with a WSL-hosted project has not
been verified as resolved in this session. WSL is available for targeted commands
if useful. The selected stack and unresolved implementation choices are recorded
in [the stack document](docs/STACK.md).

## Materials and open questions

- The student guide and Freedom introduction have been reviewed.
- Access to the DEV API was verified: 65 conversations were returned.
- The official eight-criterion checklist has been supplied and reviewed.
- All 65 DEV transcripts have been inspected; see [the data audit](docs/DATA_AUDIT.md).
- See [the evaluation design for discussion](docs/EVALUATION_DESIGN.md), including
  the organizer's chat/call clarification and our own test-dataset strategy.
- Sample rubrics discussed in chat are illustrative, not official scoring rules.
- Keep dataset records, call recordings, signed API URLs, and credentials outside Git.
- The guide requests a public repository for submission; this repository starts private.

## Progress

See [the progress checklist](docs/PROGRESS.md). Use small commits for reviewable
milestones. The CLI runs the evaluator; the web application is not scaffolded yet.

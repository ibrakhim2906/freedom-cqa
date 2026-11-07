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
evaluation; pytest and Playwright for testing. The exact model remains to be selected.

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

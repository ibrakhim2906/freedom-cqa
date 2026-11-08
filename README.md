# Freedom CQA

A conversation-quality review workspace for Freedom Broker. Evaluate operator
conversations, inspect source evidence, review disputed grades, and compare results
after changing the checklist. Supports Russian, Kazakh and English chats and
supplied call transcripts.

## Setup

Use **Python 3.12 or newer**, **uv**, **Node.js 24**, and **pnpm 11.25.0**.
The repository includes `uv.lock` and `frontend/pnpm-lock.yaml`; the launchers
install locked dependencies, build the frontend, and start one local server.
Run the commands below from the cloned repository root.

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` in that local file.
The key stays on the backend. The UI can start without a key; a valid key and
provider credit are required when you choose **Evaluate**.

**Windows — PowerShell**

```powershell
Copy-Item .env.example .env
# Edit .env and set OPENAI_API_KEY.
./scripts/start-local.ps1
```

If your PowerShell policy prevents running a local script, use these same steps
manually:

```powershell
uv sync --locked --no-dev
Push-Location frontend
pnpm install --frozen-lockfile
pnpm run build
Pop-Location
uv run --locked --no-dev cqa-serve
```

**Linux — shell**

```sh
cp .env.example .env
# Edit .env and set OPENAI_API_KEY.
sh scripts/start-local.sh
```

Open **http://127.0.0.1:8000**. Stop the server with **Ctrl+C**.
For another port, use `./scripts/start-local.ps1 -Port 8001` on Windows or
`sh scripts/start-local.sh 8001` on Linux.

A fresh checkout starts with an empty workspace and the supplied
**reviewed-016 checklist**. It creates local databases under ignored
`data/runtime/`; private datasets, prior runtime databases and generated artifacts
are not needed to start it.

The default model is `gpt-6.1-sol` with medium reasoning and the compact
`rubric-assessor-v3` evaluator. `.env.example` documents the model, timeout and
spending settings in one place. `CQA_MAX_SPEND_USD` limits cumulative estimated
API spending in this checkout; the UI also requires a budget for each batch.
Restart the server after changing `.env`.

## Evaluate and review

1. **Import** your JSON or JSONL conversations. Canonical conversations and organizer
   `data.records` files are supported. Roles, timestamps and source text are preserved.
2. **Choose a checklist** or save a new version with different criteria, instructions,
   weights, levels or N/A conditions.
3. **Evaluate** selected conversations and follow saved progress. Every new evaluation
   uses the actual model API. Standard mode normally makes one assessment call;
   **Independent review** adds a blind assessment and, when needed, adjudication.
   Repairs and review calls count toward the batch budget.
4. **Inspect** criterion grades, exact source evidence, weighted contributions,
   uncertainty and serious-error flags. Evidence links highlight the original text.
5. **Appeal** a criterion and record a review decision with its reasoning. The original
   AI result remains preserved and the effective score is recalculated.
6. **Compare or export** assessments, including results from changed checklists.

The queue supports search and language/channel filters. Call recording links are
preserved; direct audio files can play in the workspace. Model assessments use the
supplied transcript and do not claim to evaluate pronunciation or diction from audio.
Opening saved results, inspecting evidence and resolving appeals make no model calls.

## How the assessment works

The assessor reads the complete conversation and configured rubric, reconciles
customer requests, then returns decisions with source selections and explanations.
Code resolves quotations against immutable source text, validates the result, and
computes weighted scores and N/A normalization. Serious-error flags stay separate
from the numeric score.

Every applicable criterion receives a configured grade. Missing information remains
visible beside that grade; an uncertain estimate is not presented as verified fact.
The system distinguishes an appropriate next step from completed backend work and
preserves the actual result of an unsuccessful or incomplete evaluation.

## Results and documentation

- [Performance and limitations](docs/PERFORMANCE.md): measured quality checks,
  latency, cost and remaining risks.
- [DEV results](results/dev/results.json): organizer-format result file.
- [Workflow guide](docs/WORKFLOW.md): supported imports, reference context, evidence,
  appeals and persistence.
- [Submission format](docs/SUBMISSION_FORMAT.md): result fields and scoring conventions.
- [Technical stack](docs/STACK.md): application components and API choices.

The reported development checks are not organizer Ground Truth accuracy or a
promised competition score. Judges can run the application on fresh inputs and
change the checklist through the same workflow.

## Implementation

React + TypeScript + CSS Modules; FastAPI + Pydantic; SQLite/SQLAlchemy; bounded
model calls and persistent spending accounting. The local application uses
self-identified reviewers and one server process.

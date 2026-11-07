# Local evaluation and appeal workflow

The React/TypeScript workspace and FastAPI application now implement the full
local path: import → select checklist → queue real evaluation → inspect evidence
→ submit appeal → accept/reject → recalculate a human-reviewed score → export.
The interface is deliberately functional; visual polish remains separate work.

## Run locally on Windows

Tested with Python 3.13, uv, Node 24 and pnpm 11. Lockfiles are committed.
Keep `OPENAI_API_KEY` in the ignored root `.env`, as before. It is read only by
the server, never included in frontend code or configuration responses.

From the repository root:

```powershell
./scripts/start-local.ps1
```

Or build and start manually:

```powershell
uv sync --dev
cd frontend
pnpm install --frozen-lockfile
pnpm run build
cd ..
uv run cqa-serve
```

Open **http://127.0.0.1:8000**. The server serves both `/api` and the compiled
frontend. Stop it with Ctrl+C. For frontend development, keep the backend on
8000 and run `pnpm dev` in `frontend/`; its `/api` proxy targets that server.
No publication, cloud deployment, or browser-stored API key is required.

## Import and source revisions

Use **Import conversations** to upload a `.json`/`.jsonl` file or paste JSON.
Accepted shapes:

- One canonical conversation (`id`, `channel`, `language`, `messages`).
- An array of canonical conversations.
- Organizer DEV `data.records`, using `conversation_id` and `transcript`.
- Diagnostic JSONL records containing a `conversation`; expected labels and tags
  are excluded from the stored inference input.

Roles and original timestamps are preserved. Missing organizer message IDs receive
stable m1/m2/... IDs. Imports are validated before persistence; an invalid batch
does not leave partially imported conversations. Identical revisions are reused.
Changed source content creates a new immutable revision, including when its
external conversation ID is unchanged. **Edit / import new revision** opens the
canonical JSON for revision, without changing earlier evaluations.

Original recording URLs are retained as external links. Some organizer links are
preview/share pages; audio playback, transcription and timestamp-aligned seeking
are not implemented. Calls are evaluated from their transcripts and explicitly
labelled as not audio-analyzed.

## Checklists and reference context

The default is reviewed-013 and the grounded single-call evaluator. The checklist
editor supports arbitrary criteria, instructions, kinds, weights, N/A conditions,
call guidance, and allowed levels/fractions. Saving an existing ID/version with
changed content is rejected; **Edit as new version** creates another version.
Every evaluation is bound to the saved version, not an unsaved editor draft.

Under a conversation's **Reference context**, an explicit matching platform scope
and known date can attach the versioned official reference bundle. This creates
a new source revision. It cannot overwrite existing scope/date or silently make
historical sources current. References can also be supplied in imported canonical
JSON. Quotes from the evaluator open the original message or reference text.

## Evaluations, progress and spending

Select conversations, a saved checklist, and a per-batch USD budget. **Evaluate**
queues real OpenAI calls through the same tested evaluator used by the benchmark.
The local worker processes calls sequentially. Job states and batches persist in
`data/runtime/app.sqlite3`; cost reservations stay in the existing
`data/runtime/usage.sqlite3`. Both databases are ignored by Git.

The usage ledger now enforces both independent batch budgets and the configured
lifetime cap. Concurrent batch accounting cannot spend another batch's allowance.
Each evaluation stage atomically protects the first request plus one bounded
mechanical repair before submitting either. The default batch allowance is $1.00;
this is an authorization ceiling, not an expected evaluation charge. Insufficient
allowance fails before a paid first request, with required/available amounts.
Unused protected allowance is released on completion, error or cancellation. On
application restart, unspent holds for interrupted batches are released, while
submitted calls with unknown usage retain their full conservative reservation.
Unrelated CLI holds are not released by application recovery.
Unknown usage retains its full reservation. Provider credit exhaustion stops
further queued submissions; no replacement scores are generated. A conservative
maximum-token reservation can reject a job even if its eventual typical cost
would be smaller. Such a rejection is visible and not billable.

Completed or active jobs with identical source revision, checklist, model/runtime
configuration, prompt/schema and core version are reused. Opening/reopening a
saved result is free. **Run again (billable)** and **Retry (billable)** explicitly
create a new attempt, retaining the old result. Request IDs prevent duplicate
submissions; source/checklist changes cannot reuse a mismatched result.

On restart, queued work resumes. An interrupted in-flight call is marked
interrupted and is never automatically reissued: it may already have been billed.
The local prototype requires one server process; do not use multiple Uvicorn
workers against this queue. This is not an external distributed task service.

The displayed local spending cap is different from the OpenAI account balance.
Neither a top-up nor opening the UI silently increases that cap. The current
project authorization remains in force. A person choosing to authorize further
usage can update `CQA_MAX_SPEND_USD` in their local `.env` and restart the server;
never reset the ledger to bypass a cap.

## Evidence and appeals

Criterion cards display the actual model explanation, evidence, counterevidence,
checked spans, deduction-rule audit and factual-check provenance. Clicking an
evidence quote highlights its original message. Unresolved results remain
provisional with score bounds. Serious flags remain separate from the numeric score.

**Appeal this judgment** records a criterion, author, rationale and supporting
source message IDs. A completed evaluation is required. A reviewer can reject
the appeal or accept a full replacement judgment using the configured levels.
The review can include additional applicable reference evidence.

The decision records reviewer, rationale, source references, before/after judgment
and review revision. The server validates the replacement and recalculates the
weighted total, N/A normalization, provisional state, bounds and flags in code.
The original AI record is never overwritten. AI audits remain labelled as the
original model's findings; human revisions are not misrepresented as model output.
Stale reviewer submissions are rejected with a conflict, requiring a reload.

**Export** includes the original source/checklist snapshots, model record, effective
judgments/score, appeal submissions and reviewer decisions. Loading an existing
result and resolving an appeal do not call OpenAI.

Reviewer/author names are recorded self-identifications in this local prototype.
There is no authenticated multiuser role system. The server binds to loopback,
restricts host/origin handling and is intended for local use; remote deployment
would need authentication and durable single-owner/worker coordination.

## Verification performed

The subsequent [reliability review](RELIABILITY_V2_RESULTS.md) replaces the
old repair-budget behavior. It records fresh tests, the original audit failure's
successful reevaluation, and a remaining semantic repeat-consistency weakness.

- **77 pytest tests passed**, including workflow/API tests for immutable imports,
  checklist versions, cache reuse, errors/retries, review conflicts, human score
  recalculation, restart handling and batch/lifetime budget enforcement.
- Ruff passed. TypeScript and the Vite production build passed. Frontend lint has
  non-failing React development-style warnings; they are not a claim of runtime failure.
- **Two Playwright browser tests passed against the real local server.** Synthetic
  providers are available only by explicit test injection in isolated Python tests,
  never as a runtime configuration or fallback.
- The browser imported a new current-context conversation with no reference,
  obtained a genuine OpenAI response and a provisional consultation, navigated
  its message evidence, submitted an appeal and accepted it using the matching
  official guide. The final score became 100 while the original stayed provisional.
  This is a fictional workflow scenario, not a new Ground Truth annotation.
- A completely new one-criterion checklist was created through the UI and used
  in a second real evaluation, confirming that the UI does not hardcode eight criteria.
- Both saved evaluations and the human decision survived an actual server restart.
  Replaying the walkthrough reused saved results and spent **$0**.
- A budget-preflight rejection was exercised in the browser. It displayed a failed
  evaluation, no substitute score, an explicit retry action and the preserved old result.
- **All 65 original organizer records imported successfully** into the local app.
  They were not unnecessarily reevaluated as part of this workflow test.

The two real application evaluations used **$0.033656** in conservative estimated
API cost. Lifetime commitment afterward is $9.199752 against $9.427742, leaving
$0.227990 under the current authorized local limit. No extra credits or larger
limit were assumed from the account balance.

Private run evidence is saved under `artifacts/workflow-validation/`, including
source-evidence and reviewed-result screenshots, browser-state IDs, report, and budget-failure
report. These artifacts contain test/source data and are not committed.

## Run checks

```powershell
uv run pytest -q
uv run ruff check .
cd frontend
pnpm run build
pnpm exec playwright test
```

The last command skips paid browser tests by default. To deliberately run them
against the local server, set `CQA_LIVE_E2E=1` for that process. It reuses its saved
state file after a browser failure to avoid blindly submitting another model call.
Removing that state creates fresh live work and may incur charges.

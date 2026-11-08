# Local evaluation and appeal workflow

The React/TypeScript workspace and FastAPI application now implement the full
local path: import → select checklist → queue real evaluation → inspect evidence
→ submit appeal → accept/reject → recalculate a human-reviewed score → export.
The interface provides a searchable review queue, transcript/evidence workspace,
version comparison, checklist editor and separate appeal and reviewer actions.

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

The queue groups revisions by original conversation ID and shows the newest source
revision by default. Expand history to open an older source and its saved result.
Counts distinguish conversations from revisions. Status, grade, provisional
warnings and open appeals come from the latest actual assessment of that exact
revision; a new transcript does not inherit an older transcript's grade. A newer
failed attempt remains visible rather than borrowing an earlier successful score.

Original recording URLs are retained when creating an edited revision. Direct
audio-file URLs can play in the workspace; preview/share links open the external
player. Automatic transcription and timestamp-aligned seeking are not implemented.
Calls are evaluated from their transcripts and labelled as not audio-analyzed.

## Checklists and reference context

The delivery default is reviewed-016 and the compact rubric-assessor-v3 evaluator
with one protected mechanical repair. Independent review is an optional additional
blind assessment of every criterion, followed by adjudication for disagreements.
The checklist
editor supports arbitrary criteria, instructions, kinds, weights, N/A conditions,
call guidance, and allowed levels/fractions. Saving an existing ID/version with
changed content is rejected; **Edit as new version** creates another version.
Every evaluation is bound to the saved version, not an unsaved editor draft.

Under a conversation's **Reference context**, choose the official pack, assessment
basis and a rationale, then **Preview applicability (no API evaluation)**. The
preview shows original date/provenance, selected product context and each usable or
excluded source. **Apply as new revision** requires a current usable preview; the
previous source and its saved assessments remain unchanged. Batch selection moves
to the new revision so it uses the newly attached facts.

There are two distinct bases:

- **Actual conversation date:** confirm the matching product scope and supply the
  actual date if it is not already known. Complete offset-aware ISO timestamps can
  establish a date; MM:SS, language and today's date cannot. Existing dates/scopes
  and source timestamp conflicts cannot be overwritten by this selection.
- **Conditional snapshot review:** explicitly select the assumed product and the
  source snapshot's date, with a rationale. The actual conversation date and scope
  remain untouched, including unknowns. Every resulting assessment is marked
  conditional in the UI, saved record, human decisions and full export. This does
  not establish historical applicability.

The nine official product references encode `date_basis=snapshot` and
`snapshot_on=2026-11-07`, with no asserted policy validity interval. They can support
the matching actual date or an explicit review against that snapshot. A snapshot
assumption never extends a normal policy validity window. Wrong/missing context
keeps sources unusable; no fallback date or entity is invented. See
[official facts](OFFICIAL_PRODUCT_FACTS.md) for source limitations.

The selected mode, rationale, scope, assessment date, pack ID/hash and exact source
texts are frozen in the conversation input and included in its fingerprint. **Evaluate
this revision** uses these facts in the real assessment request, while retrying an old
job retains the old input. Quotes open the operator message or supplied reference;
reference knowledge is never credited as an answer the operator gave. The same
applicability helper drives preview, model payload, strict claim validation and
appeal source selection. Unusable appeal sources are disabled with reasons.
Older records without captured context show a separately labeled reconstructed
inspection view; it is not presented as evidence sent to their original model.

References/context can also be supplied in canonical JSON imports. Full review
exports preserve conditional context. Under the user's numerical-grading policy,
the organizer JSON1.0 adapter exports v3 numerical judgments with their uncertainty
and conditional assumptions in the rationale. It does not label those assumptions
as historically verified. Legacy v1/v2 unresolved judgments still export as errors.

Offline integration validation on 2026-11-07: **252 tests passed**, including
capture of the real evaluator's request preparation and strict deduction fixtures;
frontend build/Ruff passed. Nine browser checks used intercepted API routes. A live
free preview on localhost exposed all nine official references without modifying
the selected source or starting an evaluation. All 65 saved organizer assessments
were revalidated without score changes. No paid inference was run; the real usage
ledger remained 548 rows and $19.694328 settled, for **$0 incremental API cost**.
These checks establish wiring and deterministic validation, not new model accuracy.

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
evidence quote highlights its original text. Current v3 decisions retain numerical
grades alongside material uncertainty and review recommendations. Historical
unscored results remain unscored. Bounds show possible rubric outcomes, not a
probability interval. Serious flags remain separate from the numeric score.

New [v2 evidence records](EVIDENCE_CONTRACT_V2.md) distinguish operator answer
proof from the full source interval checked for an omission. Request cards show
both separately. Claim cards separately show observation scope, the narrow
supported proposition and non-proving customer/system context. Historical results
remain readable under their original contract; opening them does not generate
missing metadata or rerun the evaluator.

The historical [v3 source/proof workflow](SOURCE_SPANS_AND_ATOMIC_PROOFS.md) resolves
model-selected spans from saved sources. New records support exact-position
highlighting, including repeated quotes and Unicode. Fact cards expose required
premises, separately assessed statement parts and other fixed facts. Context is
shown separately from proof. Historical records retain their original audit and
citation behavior; human revisions do not inherit fabricated AI span provenance.
The current compact rubric assessor also resolves immutable source selections in
code, without requiring the historical global claim/proof structure.

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

Replacement evidence must be selected explicitly; disputed citations are not
copied automatically. A numerical change preserves the current uncertainty by
default. The reviewer may edit the remaining information gap, or explicitly mark
it resolved with a separate explanation. Merely changing a grade cannot silently
remove a material factual caveat.

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

# Freedom CQA

A conversation-quality review workspace for Freedom Broker: evaluate an operator,
inspect the evidence, resolve an appeal, and compare results after a checklist change.
Supports Russian, Kazakh and English chats and supplied call transcripts.

## Run

Python 3.12+, Node.js and pnpm are required. From the repository root:

```powershell
Copy-Item .env.example .env
# Set OPENAI_API_KEY locally in .env. Never commit the key.
./scripts/start-local.ps1
```

Open http://127.0.0.1:8000. No account registration is required for the local demo.
The server serves the compiled React application and API together.

Set `CQA_MAX_SPEND_USD` to your authorized cumulative local spending limit.
`CQA_STRATEGY=assessor` selects the compact evaluator. The interface offers
**Independent review** for additional source-based checking within the selected
batch budget. Every new evaluation uses the actual model API; there is no offline
score fallback. Opening a saved result or resolving an appeal does not call a model.

## Review workflow

1. **Import** organizer JSON, canonical JSON or JSONL. Original roles and timestamps
   are preserved; changed conversations become new saved revisions.
2. **Choose a checklist** or save a new version with edited criteria, weights,
   permitted levels and N/A conditions. New criteria enter actual model requests.
3. **Evaluate** the selected conversations. Follow persisted progress and explicit
   failures. Standard and Independent review are separate, budgeted choices.
4. **Inspect** criterion decisions, weighted points, material uncertainty, source
   evidence and serious-error flags. Evidence clicks highlight original text.
5. **Appeal** a criterion and record the reviewer's decision and reason. Original
   AI findings remain intact; the effective score is recalculated in code.
6. **Compare** saved assessments to see actual score, decision, source and checklist
   changes. Export the complete review history or organizer-format results.

The queue supports search and language/channel filters. Calls retain recording
links; direct audio-file URLs can play in the workspace. Current model assessments
use transcripts and do not claim to assess diction or pronunciation from audio.

## Evaluator

The compact `rubric-assessor-v3` core reads the complete source and configured
rubric. It returns criterion decisions, explanations, immutable evidence selections,
request coverage and material missing information. Code resolves exact quotations,
derives deduction records, validates sources and computes the final score.

It distinguishes an appropriate proposed next step from completed backend work.
Unknown facts are not treated as verified or automatically converted to failures.
Each applicable criterion receives the model's most defensible configured grade.
Missing information remains visible as a review recommendation beside the numeric
score. No zero, midpoint or maximum is inserted as a fallback. Historical v1/v2
records preserve their original abstention semantics.

Independent review makes a blind source-based assessment of every configured
criterion, including confident full-credit decisions. Disagreements can go to source-based adjudication; every attempt and its
cost remain recorded. An unavailable review does not erase a valid primary result
or masquerade as a completed review. Agreement between model passes is not proof
of correctness.

Historical engines and results remain preserved under their original contracts.
See [delivery results](docs/DELIVERY_RESULTS.md) for observed behavior and limits.

## Model and measured cost

The delivery uses **OpenAI `gpt-6.1-sol`**, medium reasoning, on the standard service
tier. Across the initial 65 DEV assessments, all 70 paid attempts (including
mechanical repairs) cost an estimated **$3.21**, or **$0.049 per conversation**.
The later 22 difficult reassessments, including corrections and failed attempts,
averaged **$0.081 per conversation**. These are observed local token-based estimates,
not a fixed price or provider invoice; transcript length and output size vary.

Standard mode normally makes one assessment call. Independent review adds a
blind assessment and, on disagreement, an adjudication; each stage can require
one bounded mechanical repair. The application records the combined cost of all
attempts and enforces the selected batch budget and existing cumulative cap.
Saved-result inspection, source navigation and human appeals incur no model call.

## Actual checks

The new compact core completed eight live development evaluations on the first
attempt, matching all 49 predeclared determinate decisions. These cover six
RU/KZ/EN scenarios and a two-version custom criterion. One correction-policy ordinal
was excluded before inference because the supplied rule is ambiguous.

Two additional independently reviewed runs confirmed the selected consequential
criteria. These small assistant-authored cases also helped diagnose the earlier candidate;
they are regression evidence, not
organizer Ground Truth accuracy or a promised competition score.

A focused integration check covers imports, job persistence, appeals, the compact
assessor and submission validation. The frontend build and desktop/mobile browser
walkthrough pass. The final DEV file contains **65/65 numerical assessments, 65 ok and 0 errors**.
It preserves 43 prior numerical results and uses 22 v3 reassessments under the
explicit team-selected policy snapshot. Earlier outputs and failed attempts
remain preserved. Numerical coverage does not establish expert accuracy. A known
unsupported prerequisite deduction was corrected by a general rule change and one
predeclared reassessment; its earlier result and review request remain in history.

A separate fresh eight-case challenge delivered seven first-pass valid results
and 24/25 frozen expected decisions. The remaining model output was rejected for
citing an unsuccessful response under an unanswered request; a general
representation fix now validates that exact saved output without changing its
grades. The first-run failure remains recorded. One matching Kazakh label is
linguistically ambiguous, so these are provisional AI-authored checks. A new
three-level criterion pair changed the same conversation from **100 to 50**;
the actual explanations, evidence and scores were preserved in the UI and export.

## CLI and submission

```powershell
uv run cqa benchmark --cases-file evals/delivery-acceptance-v1.jsonl --strategy assessor --budget-usd 1.50 --output artifacts/my-check.json
uv run cqa benchmark --suite organizer --strategy assessor --budget-usd 3.50 --output artifacts/my-dev-run.json
```

Organizer DEV input belongs in ignored `data/private/dev.json`. Credentials,
private conversations, recordings and runtime databases are excluded from Git.
Each benchmark saves its exact input snapshot and original failures. Never reuse
an output filename to overwrite a prior result.

[Control-run instructions](docs/CONTROL_RUN.md) prepare the actual ten unseen
inputs when received; no PROD results have been fabricated.

[Submission format](docs/SUBMISSION_FORMAT.md) documents the required JSON1.0 files,
original turn numbering, weights and errors. [Workflow details](docs/WORKFLOW.md)
cover persistence, evidence and human review. [Delivery plan](docs/DELIVERY_1150_PLAN.md)
records the 11:50 deadline and work allocation.

## Architecture

React + TypeScript + CSS Modules; FastAPI + Pydantic; SQLite/SQLAlchemy; real model
API calls with bounded repair and persistent spending accounting. Scoring and
N/A normalization are deterministic. The local worker uses one server process.
The local demonstration has self-identified reviewers, not authenticated roles.

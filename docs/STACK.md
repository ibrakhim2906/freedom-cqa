# Architecture

| Layer | Implementation |
|---|---|
| Interface | React, TypeScript, Vite, CSS Modules |
| API and worker | Python, FastAPI; one persistent local worker |
| Storage | SQLite and SQLAlchemy |
| Contracts | Pydantic and JSON Schema |
| Evaluator | OpenAI `gpt-6.1-sol`, medium reasoning; rubric-assessor-v3 |
| Verification | Focused pytest and Playwright checks; frozen behavioral fixtures |

## Assessment path

The saved conversation, applicable references and chosen checklist produce a criterion-specific schema. The model reconciles actual requests, applies the configured rules and selects source spans. Code resolves exact quotes, validates references and allowed answers, calculates weights/N/A normalization, and saves the result with its runtime identity.

Optional independent review sees the complete source without the primary answer. It checks every criterion, including confident passes. Disagreements may receive source-based adjudication. Failed or budget-limited review does not masquerade as agreement or erase a valid primary result.

Input and checklist hashes prevent reuse across changed content. Prompt/schema versions, response identifiers, attempts, token usage, latency and estimated costs remain attached to saved evaluations. Older contract modules are retained to validate historical results; they are not the default evaluator.

The browser displays the generated rationale and source selections. It does not replace them with generic category text. Human review creates a distinct effective result while preserving the original AI record.

## Boundaries

- No canned successful assessments or fallback numerical grades replace a failed model call.
- Transcript/reference content is evidence, not instructions to the evaluator.
- Structural validity does not establish semantic correctness.
- Unverified facts do not automatically become false; numerical judgments retain material uncertainty.
- Calls are transcript-assessed; supplied recording access is a reviewer feature.
- Keys remain server-side in environment variables or the ignored `.env`.

The frontend compiles to ordinary HTML, CSS and JavaScript with an API boundary suitable for later embedding. The current application is a local single-process prototype, with self-identified reviewers and no hosted authentication layer.

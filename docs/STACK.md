# Technology stack and evaluation policy

Status: selected during project discussion on 2026-11-07. Implementation has not
started. Exact dependency versions will be pinned when the project is scaffolded.

## Selected stack

| Layer | Choice | Responsibility |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite | Checklist editor, transcript viewer, evidence navigation, evaluation results, and appeals. |
| Styling | CSS Modules | Component-scoped styles for the review workspace. |
| Backend | Python, FastAPI | Conversation import, evaluation jobs, score calculation, persistence, and review endpoints. |
| Data contracts | Pydantic | Validate checklist definitions, evaluation output, evidence references, and API payloads. |
| Storage | SQLite, SQLAlchemy | Store conversations, immutable checklist versions, evaluation attempts/results, and appeal decisions. |
| AI provider | OpenAI API through a small provider adapter | Generate substantive criterion judgments and conversation-specific explanations with evidence references. |
| Testing | pytest and Playwright | Scoring and API checks, evaluation behavior checks, and complete browser workflows. |
| Initial environment | Windows-native development | Keep the checkout and runtime on Windows while verifying local browser/computer-use access. |

The frontend builds to HTML, CSS, and JavaScript. Keep its API boundary explicit
and its structure suitable for later adaptation to a Dynamics 365 HTML component.

Use one repository with separate frontend and backend directories. Initially,
target a single application service that serves the compiled frontend and API,
with persistent storage for SQLite. Local development can run separate frontend
and backend processes.

## AI integration

- Send the selected, versioned checklist and actual conversation to the evaluator.
- Preserve speaker roles and original timestamps; give messages stable IDs.
- Use Structured Outputs for machine-readable criterion results.
- Preserve model-produced explanations in the displayed result; do not replace
  them with canned text based on a category or score.
- Validate allowed values, required fields, and evidence references in code.
  Passing these checks does not establish semantic correctness.
- Calculate weights, N/A redistribution, rounding, and any serious-error effects
  in code according to the official checklist once supplied.
- Start with one model call per conversation covering the checklist. Add targeted
  verification only if development measurements show improved evaluation quality.
- Record model identity, checklist/prompt versions, token usage, latency, and
  estimated cost for each attempt.

The exact OpenAI model is not selected. Compare available candidates using varied
Russian, Kazakh, and English development cases and human-reviewed criterion labels.
Audio evaluation will be designed once the actual checklist establishes which
criteria require recordings. Transcripts alone cannot establish diction or intonation.

## Required runtime behavior: no offline evaluation fallback

This is an explicit user requirement.

- API errors produce a visible failed evaluation with retry available.
- Malformed output or invalid evidence references are rejected. A bounded retry
  can be attempted; unresolved failures remain visible for human review.
- If the available conversation/reference material cannot establish a criterion,
  mark it unresolved and keep the total provisional. Distinguish this from an
  observed omission, an actual failed criterion, and a justified N/A decision.
- Do not substitute predefined ratings, generic explanations, keyword-based
  judgments, offline model results, or prepared demo results for a failed API call.
- Display saved evaluations with their original provenance, timestamp, and
  checklist version. Do not present them as fresh evaluations of changed inputs.
- Synthetic responses are permitted in isolated automated tests only. They must
  never be presented by the application as genuine evaluations.

## First implementation milestone

Open one conversation, evaluate one editable criterion through the real API,
inspect its explanation and evidence, change the criterion, and reevaluate.
Check paraphrases, speaker attribution changes, evidence removal, and irrelevant
changes against the final displayed judgment. Expand to the complete checklist
after this behavior is established.

The main selection priority is accuracy on unseen transcripts against organizer
Ground Truth; see [the organizer's selection criteria](JUDGING.md).

## Open implementation choices

- Exact OpenAI model, API access, and an explicit development spend limit.
- Official operator checklist, reference procedures, and audio-dependent criteria.
- Dependency versions, deployment target, and persistent-volume configuration.
- Browser/computer-use verification in the actual Windows setup.

Credentials stay in backend environment variables or a Git-ignored local `.env`.
Do not place API keys in frontend code, tracked files, test fixtures, or logs.

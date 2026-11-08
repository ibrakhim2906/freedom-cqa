# Evaluation and review workflow

Start the application using the [README](../README.md). The browser interface and API are served together on localhost; no account registration is required.

## Import and assess

1. Import organizer JSON (`data.records`), canonical conversation JSON, or JSONL. Original speaker roles and timestamps are preserved.
2. Select the saved checklist. To change a criterion, edit its wording, answer type, weight, levels or N/A condition and save a **new version**.
3. Select conversations and a batch budget. Standard runs one assessment; Independent review adds a blind review of all criteria and adjudication for disagreements.
4. Open the result to inspect criterion answers, weighted contributions, explanations, evidence and material uncertainty.

The default checklist is reviewed016 and the evaluator is `assessor`. Changed source content becomes a new immutable revision. The queue shows the newest revision for each conversation; expand history to inspect older sources and their actual saved results. A new or failed revision never borrows another revision's grade.

## Evidence and recordings

Evidence links highlight exact original text, including repeated quotations. Omission decisions identify the interval checked. N/A has its own explanation and redistributes applicable weights; the serious-error flag remains separate from the total.

Call recordings open their supplied player; direct audio-file URLs may play inline. A recording link can be recovered from an original revision only when conversation ID, channel, language and every source message match, and the matching URL is unambiguous. The origin revision remains identifiable. Existing saved inputs are not rewritten.

Model evaluations use the supplied transcripts. They do not claim to assess pronunciation or intonation from unavailable audio.

## Knowledge context and numerical uncertainty

Optional reference packs are scoped and dated. Preview applicability before attaching a pack as a new source revision. An explicitly selected snapshot is an assumption, not proof that its rules applied historically.

Every applicable criterion in the current assessor receives a supported allowed answer. Missing information remains visible beside the numerical grade. Bounds show possible configured outcomes, not a confidence interval. Older unscored assessments preserve their historical status.

## Appeal and review

1. Appeal a criterion with a comment and relevant source messages.
2. The reviewer confirms or replaces the judgment and records a reason.
3. Replacement evidence must be selected explicitly; disputed evidence is not copied automatically.
4. Existing uncertainty is retained by default. Clearing it requires an explicit decision and explanation of what resolved it.
5. The application recalculates the score while preserving the original AI assessment and the review history.

Reviewer names are self-identifications in this local prototype, not authenticated roles. Stale concurrent decisions are rejected rather than overwriting a newer review.

## Compare, export and reopen

Compare saved results across source or checklist revisions. Changes to source, context and criteria are identified separately. Full export includes original source/checklist snapshots, model output, effective reviewed judgments and appeal history. The organizer adapter exports the original AI assessment under the required fixed schema; see [submission format](SUBMISSION_FORMAT.md).

Saved-result inspection and human reviews do not call the model. Jobs, sources and appeals persist in `data/runtime/app.sqlite3`; usage accounting persists in `data/runtime/usage.sqlite3`. Failures remain visible and have an explicit retry action. An interrupted request with unknown billing retains its reservation.

Use one backend process for this local worker. The spending cap is separate from the provider's account balance; reopening the app does not reset either.

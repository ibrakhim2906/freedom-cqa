# Release configuration and evidence

A release names one default evaluator configuration and one exact checklist
snapshot. A translated or reorganized checklist is a new model input even when
its weights and allowed answer values remain identical. Keep the previous
validated version available until a proposed replacement has its own recorded
comparison. Passing arithmetic or display tests alone does not establish
behavioral equivalence.

The current release candidate uses `freedom-reviewed-017`, selected once through
`cqa.rubric.DEFAULT_CHECKLIST_PATH`. Its comparison against 016 completed all ten
diagnostic cases: 79 unambiguous judgments matched, all 80 operational
answer/status/uncertainty flags and all totals matched the 016 run, and the
ambiguous closing remained explicitly qualified. Source decoding and score
replay passed for all ten. This reused panel is promotion evidence, not new
held-out accuracy. Additional boundary verification remains part of the final
release decision. Version 016 remains available explicitly for historical
reproduction or rollback; do not reinterpret its saved results as 017 results.

## Promote a candidate

1. Record the commit, evaluator/prompt version, model, reasoning effort, retry
   policy, checklist ID/version and content fingerprint. Link the measured run
   and disclose ambiguous/excluded judgments. Keep older measurement claims
   attached to their original configuration.
2. Use the same chosen default in the API bootstrap and `/api/config`, the CLI,
   prepared walkthrough and control-input preparation. The control manifest
   must name the exact checklist embedded in every prepared case. Do not infer
   a release from the newest filename or highest version number.
3. Run `python -m pytest -q tests/test_release_configuration.py`. It checks API
   and CLI content equality, the walkthrough's actual saved checklist, control
   manifest/embedded snapshots, and preservation of an explicitly selected older
   or newer saved version. All checks use temporary workspaces and no model calls.
4. Verify the final built browser application against the running API after the
   agreed restart. Inspect its selected checklist before starting a new run.
   A current API default does not prove that an already open page or an existing
   job uses that version. Check the returned job's `checklist.content`,
   `checklist.content_hash`, `runtime` and original `record`.
5. Keep saved snapshots and original assessments intact. Existing jobs retain
   their selected checklist version; an explicit rerun creates a new assessment.
   A default promotion must not relabel an old result, rewrite a checklist at an
   existing ID/version, or report a prepared walkthrough as a fresh model result.
6. Verify a clean clone of the submitted GitHub repository at the agreed commit.
   Follow the documented source setup, install the locked dependencies and build
   the frontend, then confirm the API default in that isolated checkout. The
   committed source must include the chosen checklist and older versions needed
   for historical reproduction. Do not copy local runtime data or credentials
   into the clone. This release uses source setup; an archive is not required.

## Distinguish defaults, selection and history

The API advertises a default logical checklist ID and version. Browser selection
is separate: the current application holds `checklistId` in page state and
resolves the main checklist through the advertised version when refreshing its
catalogue. Persisted checklist rows, including later drafts, must not silently
promote themselves merely because their save date is newer.

Evaluation requests identify a saved checklist document by its exact ID. The job
and full export expose that selected snapshot and the runtime configuration used
for the request. Inspect these artifacts when checking what was actually run;
the current default or a dropdown label cannot establish a historical job's
configuration. A prepared example has its own explicit `prepared_demo` runtime
and makes no model request.

## Uncertainty and reference claims

The current v3 assessment contract selects the best-supported configured answer
for an applicable criterion and preserves material uncertainty in its explanation
and review warnings. A missing closing opportunity is not proof of N/A. Historical
`needs_review` records and their original null answers remain readable; they must
not be silently rewritten to match current behavior. Describe this distinction
when presenting older checklist wording that requests an unselected answer.

Small authored comparisons and identical repeats support a bounded release
decision. They do not establish organizer Ground Truth agreement, guarantee the
same outputs on new conversations, or justify transferring one configuration's
accuracy claim to a different checklist without measurement.

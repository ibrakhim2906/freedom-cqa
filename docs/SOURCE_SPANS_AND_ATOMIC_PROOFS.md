# Source spans and atomic proofs — v3

The grounded workflow now uses a separate `span-v3` provider contract and
`coverage-v3` semantic audit. It addresses the failures in
[the fresh repeated-run experiment](FRESH_REPEAT_V1_RESULTS.md). The rubric,
scoring arithmetic and frozen expectations are unchanged. This implementation
has not been exercised through paid inference; the last measured first-pass
validity remains 18/24 under v7, not a new v8 result.

## Exact source selections

The model selects immutable span IDs for dialogue, reference and criterion-rule
citations. It never generates citation text or character offsets. Each catalog
contains every full original source field and deterministic optional fragments.
Whole sources are retained even when the optional fragment budget is exhausted.
IDs are partitioned by source kind and role; rules retain their owning criterion.

The model's complete output must validate against its exact source-bound schema
before any ID is resolved. Unknown IDs, wrong roles/kinds/criteria, stale source
fingerprints, extra quote text, duplicate JSON fields and nonstandard JSON values
are rejected. The resolver obtains text only from the explicitly selected source.
It does not search for a plausible quote, fix spelling or select substitute proof.

Every persisted quoted slot records its selected span ID. Navigation metadata
retains the source identity, field and exact Unicode code-point range. Validation
checks every slot and range against the immutable catalog, including distinct
occurrences of identical text. Proof unions use source identity and position,
rather than treating identical strings as the same event.

The interface follows those selections when highlighting dialogue and reference
text. It handles Unicode, multiple ranges and repeated phrases. Invalid explicit
metadata withholds highlighting and displays an error; it never silently chooses
the first matching phrase. Historical quote-only records retain their original
navigation behavior without invented v3 provenance.

The input is also a source-linked view. Original text fields point to a catalog
source whose text parts concatenate to the exact original field, character for
character. This exposes text once instead of duplicating full sources and fragment
quotes. Original conversation/checklist objects and saved files are not modified.
Roles, timestamps, scope, source dates and applicability remain at their original
source locations. The catalog binds the complete source/checklist revision.

## One observation proposition

An atom's `claim` is its single canonical proposition. An observation explicitly
targets that claim and declares its scope. There is no second model-generated
`supported_proposition` to paraphrase and compare by string equality. The persisted
compatibility field is an explicit reference alias; it does not infer a proposition
or assert that a contradicted claim is true.

All proving source selections occur once, in proof premises or canonical claim
dependencies. The application mechanically exposes their exact leaf union in
the saved dialogue/reference/rule evidence view. It does not invent sources,
decide truth, alter grades or turn context into proof. Observation scope remains
explicit; it cannot be inferred from selected source roles.

General policy, grading-rule and commitment atoms do not take customer observation
proof. Related interaction reports remain context or form genuinely necessary,
separately scoped premises. A commitment proves only the stated promise, not its
completion. Private/system proof cannot acquire essential client evidence through
a transitive dependency. Existing reference scope/date checks remain enforced.

Forbidden collections are literal `null` in the provider contract. For example,
unanswered questions cannot supply positive answer evidence and next-step support
cannot open an unresolved-aspects array. After full schema validation, those
explicit declarations project to empty collections in the historical display
shape. Missing fields and nonempty forbidden lists are still rejected. This
removes the exact empty-array form implicated in the previous whitespace stall;
it does not prove that the provider can never stall or truncate.

## Separately assessed facts and complete proof dependencies

Operator assertion groups link separately assessed atomic claims. An atomic group
contains one claim; an `all_of` group contains multiple claims. Each claim keeps
its own truth, source support, correction lifecycle and criterion impacts. A
group cannot carry a shared false-to-zero grade branch that hides which constituent
fact is false. Its conjunction truth is derived from the individual statuses,
not supplied as a replacement for their assessments.

Each impact names every other atom touching that criterion as a fixed fact.
Changing a false incidental statement must not automatically make a correct key
recommendation wrong. An independently wrong key recommendation can still cause
both branches of a separate route claim to score zero. The model must explain
the configured rule and the actual consequence; no numeric policy was added.

Proofs explicitly require all declared premises. A direct source premise can
reference the canonical claim without repeating its text. Conjunctive premises
state their separate necessary propositions. A dependency names another canonical
claim and its required known truth state. Missing, unknown, cyclic or contradictory
dependencies cannot establish a known conclusion. Flat source views must exactly
preserve the transitive selected leaf union. A source placed only in context
cannot satisfy a required premise.

This permits an earlier customer state and a later no-change record to be explicit
parts of one inference. Declaring the whole proof system-only while it depends
on the customer state is rejected. Original wrong advice and its supported
correction remain separate in the audit, and independent contact, hold, closing
and other legitimate deductions remain required.

Structural validation cannot determine whether a free-text proposition secretly
contains an undeclared conjunction, whether a selected source entails it, or
whether a counterfactual explanation is semantically correct. The model must
perform that analysis; complete-assessment review and new inference tests remain
necessary. This contract makes declared omissions and dependencies inspectable
and enforceable; it is not an entailment oracle or a new accuracy measurement.

## Compatibility and candidate verification

Actual grounded evaluation and workflow cache keys use the new contract. Malformed
v3 output never falls back to v2, and new metadata cannot be hidden under an old
audit version. Historical v1/v2 results remain under their original validation
semantics; raw records, old failures and all frozen labels are preserved. The
original AI audit remains immutable after a human appeal; reviewed judgments are
validated and scored separately, with human provenance.

The original freeze verifiers still pin their old engines. They have not been
weakened or re-frozen. The separate free command is:

```powershell
uv run python -m scripts.verify_source_span_candidate
```

It checks old raw hashes, payloads and expected arithmetic, prepares all 79 existing
conversations with the current contract, checks schema/protected input bounds,
and revalidates historical scores without regrading. It constructs no client and
does not write the usage ledger. `--record` writes only a new ignored candidate
protocol; `--check-protocol` checks that exact identity. A future paid run requires
a separately recorded execution protocol.

The provider schema uses the documented [Structured Outputs subset](https://developers.openai.com/api/docs/guides/structured-outputs).
Identical schema shapes are shared without changing accepted values. The existing
200,000-byte conservative context guard, protected bounded repair and output-token
cap remain unchanged. Runtime JSON schema validation is a project dependency,
including installations without development packages.

### Completed offline checks

- 560 Python tests passed. Ruff, the production frontend build and the offline
  dependency-lock check passed. Frontend lint retains six existing React warnings;
  the Python suite reports one existing Starlette deprecation warning.
- 18 fully intercepted browser checks passed, including equal text at different
  positions, Unicode offsets, multi-span selections, hidden dependency navigation
  and rejection of invalid explicit provenance. Browser checks made no application
  writes and did not evaluate conversations.
- All 79 existing input/schema pairs fit the unchanged context guard, including
  the protected repair allowance. The maximum conservative bound is 197,287 bytes.
  Schema maxima are 84,456 bytes, 700 properties, 702 enum values and eight nested
  containers. No source field was truncated to achieve these bounds.
- 110 frozen expected judgments and 12 complete expected vectors are unchanged.
  All 97 accepted historical assessments revalidate with their original scores.
  Four historical failures and the original budget skip remain in their receipts.
- The recorded candidate is `evaluator-v8-ebe6d961965c`. The local ignored protocol
  is `artifacts/source-spans-v3/candidate-protocol.json`; it pins engine files,
  prepared schemas, preserved receipts and the unchanged ledger checkpoint.
- Zero paid requests were made: **$0 incremental API cost**. Provider acceptance,
  judgment quality, repeatability, latency and token cost for v8 remain unmeasured.

These checks establish implementation integrity and compatibility. They do not
raise the last measured product grade or turn authored expectations into expert
Ground Truth. The next inference experiment must preserve the expectations and
evaluate complete judgments, evidence and legitimate deductions, as well as
first-pass validity and repeated-run behavior.

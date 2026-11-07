# Evidence contract v2

The current grounded evaluator uses `coverage-v2` and prompt version
`evaluator-v7-0d77742ac102`. This changes how the model must declare support; it
does not change the checklist, scoring arithmetic or frozen expected judgments.

## Unanswered and partially answered requests

`support.evidence` is positive answer proof. For answered, partial and next-step
requests it must quote an actual operator answer linked in `answer_message_ids`.
Customer acknowledgments and operator nonanswers cannot replace that proof.

An unanswered request must have `basis=none`, empty positive evidence and answer
IDs, and named unresolved aspects. Both partial and unanswered requests require
`support.omission`:

- `start_message_id`: the earliest linked customer request.
- `end_message_id`: the final original source turn.
- `context_evidence`: optional verbatim contextual quotes within that inclusive
  span, from any actual source role.

Two endpoints declare the complete opportunity span without repeating hundreds
of message IDs on long calls. Context quotes explain the omission; they do not
become answer proof. The interval is a review declaration, not an automatic
semantic proof that every question was unanswered. Partial requests still need
real positive answer evidence and a description of what remains unresolved.
Answered, next-step and withdrawn requests require `omission=null`. Withdrawal
requires actual customer withdrawal evidence and no claimed operator answer.

## Claim context and observations

Every new factual claim explicitly supplies `context_evidence`. These client or
system quotes provide non-proving context. They never establish policy, private
account truth or task completion.

Nonempty `dialogue_evidence` declares observation evidence. It requires a
non-`none` `observation_scope` and a nonempty `supported_proposition`, including
when an applicable policy reference is the primary proof. A visible control is
different from a completed action or general product policy. `system_record`
observations require system messages; a customer report is not a system record.
Existing applicable-reference and private-record requirements remain enforced.

With no observation, `dialogue_evidence=[]` and `observation_scope=none` are
required. A supported workflow commitment can still declare its commitment
proposition without independent observation, under the existing commitment rule.
The UI displays context, observation scope and proposition separately, and lets
reviewers highlight the entire omission interval in the source transcript.

## Strict generation and historical compatibility

The provider schema uses status-specific answer branches and separate observation
branches. Role-partitioned source-ID references avoid multiplying large enums
through every branch. Runtime validation additionally checks exact quotes,
linked IDs, interval ordering and applicable policy sources.

The grounded decoder requires keyed inline judgments, explicit fields throughout
the new output, the v2 audit and claim dependency assessments. It does not fill
missing metadata, scrub invalid quotes, manufacture omission support, change
grades or remove deductions. Historical defaults exist only for reading old
saved records. Old records retain their original contract and version.

## Offline verification and its limits

The two previously rejected repair outputs remain rejected. Separate test-only
encodings express the same proposed judgments and deductions using the explicit
new contract. They validate, but are not new API responses, accepted historical
results or evidence of improved live accuracy. Negative tests reject wrong
speaker roles, false quotes, incomplete spans, missing metadata, context used as
verification, customer reports labeled as system records and omitted new fields.
Additional tests use a different checklist and late requests, preserving
independent closing deductions and unanswered-question deductions.

The six frozen cases, all 48 provisional expected judgments, their review and
freeze manifests, original rubric and source pack remain unchanged. The original
`scripts.verify_official_acceptance` deliberately pins the old engine as well as
its inputs; it must not be loosened or re-frozen to bless a new engine. Use the
separate free candidate check:

```powershell
uv run python -m scripts.verify_evidence_contract_candidate
```

It verifies the frozen input hashes and arithmetic, prepares the new schemas,
checks the explicit test encodings and revalidates accepted historical results
without changing failed statuses. A candidate protocol can be written to a new
ignored artifact path with `--record`, then checked with `--check-protocol`.
It records a separate prompt/schema/source identity and constructs no API client.

This change has not been tested through paid inference. Offline schema checks,
saved-record validation and mocked UI checks establish structural behavior, not
provider acceptance, semantic completeness, live model stability or organizer
Ground Truth accuracy. The prior real run remains four valid outputs and two
failures until an explicitly authorized new run measures otherwise.

Verification for this change: 340 pytest tests passed; Ruff and the frontend
production build passed. Frontend lint has existing non-failing React warnings.
Seven mocked browser checks passed with all API routes intercepted. All 71 current
schemas (six frozen cases plus 65 organizer conversations) pass local schema
checks, with maxima of 62,394 bytes, 596 object properties, 468 enum values and
eight container levels. This is not a provider acceptance test.

All 65 saved organizer evaluations, using the previously declared four later
rechecks, validate with exactly unchanged scores: 36 numeric and 29 provisional.
Those mixed historical v3/v4 records predate semantic audits; this establishes
compatibility, not v2 inference quality. The four accepted frozen-suite results
also revalidate unchanged. All ten preserved file hashes match and the usage
ledger remains at 556 rows: zero additional calls and $0 incremental API cost.
Private evidence is under `artifacts/evidence-contract-v2/`.

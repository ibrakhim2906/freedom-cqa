# Source contract v5: proof scope and explicit review links

The grounded evaluator uses `span-v5` and `coverage-v5`. This version addresses
two findings from the [preceding manual review](MANUAL_DIAGNOSTICS_V3.md): a
negative proof broader than its premises, and a long-call failure caused by
repeating source review declarations in several places.

## Proof scope

The instructions require a negative proof to cover the entire original
assertion's time, action and route. A later no-action interval does not disprove
an earlier completion. A failed route does not disprove success through another
route. A broader negative conclusion needs both an initial-state premise and
the complete later no-change premise. Explicit earlier success must survive.

If those premises are unavailable, the broader assertion stays visible and
unverified. The evaluator must not silently replace it with a narrower assertion
that is easier to refute. Uncertainty remains local: a separately false companion
claim and an independently established process defect retain their deductions.

This is a semantic instruction, not a deterministic entailment check. Strict
source validation proves where a quotation came from, not whether the selected
premises justify the conclusion. Full assessment review remains necessary.

## Review links

Provider judgments now declare `additional_checked_message_ids` for extra,
unquoted review scope. The old judgment-level `checked_message_ids` field is
forbidden in new responses. Explicit source relations already present elsewhere
are projected into the saved judgment's review list:

- Judgment evidence and counterevidence.
- Criterion-bound deductions and their checked intervals.
- Criterion-bound semantic exclusions.
- Linked canonical claims, proof dependencies, context, corrections and impacts.

The saved list is exactly the chronological union of those declarations and
the additional IDs. An immutable source selection supplies its original message
ID; neither wording nor a desired score determines the relationship. Request
coverage alone has no criterion binding and is not assigned to a guessed criterion.
The complete semantic-audit review list and deduction/impact checked lists retain
their original explicit meaning.

Projection changes only the review list. It creates no evidence, factual status,
answer or score. The persisted audit records the additional declarations and the
versioned projection marker. Revalidation recomputes the exact union and rejects
missing or changed provenance, unknown IDs, invalid links and altered saved lists.
The existing exclusion-to-review validation guard still runs.

## Compatibility and diagnostic protocol

The current decoder accepts only v5. Explicit v3 and v4 readers preserve their
historical authored review declarations and rejection rules. Old failures are
not repaired by reading them through the new contract. Historical schema and
payload hashes, accepted scores, original labels and freeze files are checked by
the new offline verifier:

```powershell
uv run python -m scripts.verify_source_contract_v5_candidate
```

Old candidate verifiers remain version pinned. They are not changed to approve
the new engine. The protected input guard remains 200,000 bytes including repair
allowance; the configured output cap remains 6,000 tokens.

Verification passes 703 Python tests, Ruff and all 82 prepared input checks.
The largest protected input is 194,078 bytes. All 79 historical v3/v4 schema
and payload pairs retain their hashes; 97 accepted historical API scores,
110 original provisional labels, 12 complete expected vectors and ten previous
manual receipts retain their values and accepted/rejected status. The three
new controls separately freeze six judgments and three complete vectors.

The manual rerun retains C/D/E and their unchanged expected judgments and
interpretation caveats. Three additional fictional note-saving contrasts freeze
their inputs, custom checklist and provisional expectations before inference.
Only the initial-state record differs across those controls: earlier success,
complete non-completion, or both completions with the prerequisite satisfied.
Atomic truth must change correctly even where two whole-conversation totals
are both zero. These are targeted development diagnostics, not an untouched
holdout or organizer Ground Truth.

Execution agents use explicitly requested Sol 6.1 with medium reasoning, one
packet and one immutable submission each. They receive no expectations, previous
outputs or validator feedback. These chat diagnostics do not reproduce API
constrained decoding, output-cap completion, latency, token costs or repeatability.
Results are reported separately after strict validation and semantic review.

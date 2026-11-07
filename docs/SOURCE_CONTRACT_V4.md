# Source contract v4: canonical group sources and observation/proof coupling

The grounded evaluator now uses `span-v4`, `coverage-v4`, and prompt
`evaluator-v9-67ef9cb4abdf`. This changes the provider contract and audit guidance;
the checklist, allowed grades, scoring arithmetic and frozen expectations are
unchanged. The [previous manual diagnostic](MANUAL_DIAGNOSTICS_V2.md) exposed the
specific failures addressed here.

## Group citations are a projection of canonical atom selections

The provider declares `group_id`, `composition` and `claim_ids`. It selects
operator evidence once, on each atomic factual claim. A second provider-selected
group citation list is forbidden by the v4 schema.

After validating the entire wire object, the decoder checks unique IDs,
reciprocal single membership, complete claim coverage and the required atomic/
conjunction cardinalities. It then derives each persisted group's source view
from the exact selected span-ID union of its members, in first-seen order.
No text search, source expansion, quote correction, inferred group membership or
grade change occurs. Identical text at different offsets remains different.

The persisted v4 audit has `projection=derived-groups-v4`. Validation requires
that marker and the exact selected member union. Dropped, extra, duplicated or
broadened selections are rejected even when a broader source contains the same
words. Version-marker changes cannot silently downgrade this check.

## Observations require proving sources

The schema expresses correlated proof/observation branches. An unverified claim
with `proof=null` must also declare `observation=null`. An observed claim requires
an appropriate non-null proof. Direct observed source premises require permitted
independent dialogue evidence; system-only observations retain system-only source
constraints. Policy/rule claims and commitments cannot take an unrelated customer
observation as their proof.

Dependencies may inherit the necessary proving dialogue rather than repeat it.
The schema therefore permits dependency-only proofs, while the runtime checks
the actual transitive leaf union, known dependency statuses and acyclic graph.
No proving leaves means no observation. Context never supplies a missing proof,
and neither metadata nor factual truth is inferred to make a response pass.

Explicit `null` collections for sources that do not exist are normalized only
after full wire validation. A regression covers conversations with no operator,
where both factual claims and groups must be null in the provider output.

## Sequencing uses the existing audit

The prompt requires an independent review of each material sequence using the
existing proof, deduction evidence, checked span and overlap explanation. No
second sequencing object duplicates the same facts.

The analysis must identify the configured prerequisite and its source, the
dependent action or explicit completion assurance, and the chronological evidence
of the prerequisite's state. It distinguishes a premature assurance against
reported pending prerequisites from an actual backend sequencing violation.
Customer reports can establish conversational state without becoming authoritative
private records. Conversely, a pending label, missing confirmation or possible
UI lag alone does not prove actual backend misconduct. The stated grading rule
determines whether the prerequisite itself or its confirmation is required.

An independently justified deduction is retained even when another defect keeps
the numeric level unchanged. Incomplete conditions must be explained locally;
they cannot become a blanket reason to suppress a process finding or invent
an unobserved private outcome.

## Historical results and bounds

The current decoder accepts only v4. The explicit `decode_span_evaluation_v3`
historical reader retains v3's original group-containment rules and observation
guards. All 79 historical v3 schema/payload pairs match their previous hashes;
97 accepted API scores and three accepted manual scores remain unchanged.
The three rejected manual submissions, including the incomplete paste, remain
rejected. They are not repaired or promoted by the new contract.

All 110 original frozen judgments and 12 complete expected vectors remain intact.
The same C/D/E manual expectations and pre-result interpretation caveat are reused
byte-for-byte. E's consultation ordinal remains unscored, and C's legitimate
interpretation disagreements remain visible rather than being relabeled.

Schema factoring shortens internal definition names only in v4; it does not
change accepted source IDs, configured criterion names or field values. The
largest organizer schema decreases from 84,456 to 77,212 bytes. All 79 prepared
requests fit the unchanged 200,000-byte protected-context guard; the maximum is
191,620 bytes. The output cap stays 6,000 tokens. Offline bounds do not establish
that generation will finish within that cap.

The schema uses the supported [Structured Outputs subset](https://developers.openai.com/api/docs/guides/structured-outputs).
Provider acceptance and runtime reliability have not been measured through API
inference. JSON Schema validity does not establish semantic entailment.

## Verification

637 Python tests pass, with one existing Starlette deprecation warning. Ruff and
diff checks pass. The free candidate check is:

```powershell
uv run python -m scripts.verify_source_contract_v4_candidate
```

Its separate protocol pins current engine identity, bounds and unchanged historical
receipts. Old freeze verifiers are not weakened or re-frozen for the new engine.
The usage ledger remains at its pre-run checkpoint; no API client is constructed
by the verification script.

The manual rerun uses three isolated agents explicitly requested as
`gpt-6.1-sol`, medium reasoning, with no expected labels, previous outputs or
validator feedback before submission. JSON serialization tools are allowed.
These conditions do not reproduce API constrained decoding, output limits,
latency or costs. Previous manual agents inherited different settings, so the
before/after observations are not a controlled same-model experiment.

The rerun outcomes are recorded separately after strict validation and complete
semantic review; they do not automatically raise the product grade.

# V4 contract manual rerun — Sol 6.1 medium

Date: 2026-11-07. Prompt: `evaluator-v9-67ef9cb4abdf`; provider transport
`span-v4`, semantic audit `coverage-v4`. The implementation is described in
[SOURCE_CONTRACT_V4.md](SOURCE_CONTRACT_V4.md).

All three execution agents, the independent semantic reviewer and the separately
recorded repair agent were explicitly requested as `gpt-6.1-sol` with medium
reasoning. These are tool-assisted chat diagnostics, not OpenAI API requests.
They do not reproduce provider constrained decoding, the 6,000-token output cap,
API latency, token costs or repeated-run behavior. Earlier execution agents
inherited different settings; the comparison is not a controlled same-model test.

## Frozen inputs and expectations

The same C/D/E inputs, checklist and expected judgments from the
[previous diagnostic](MANUAL_DIAGNOSTICS_V2.md) were reused without alteration.
The expected-file SHA-256 remains
`e16b09eab3ec7639f960e2f01dff2dbd799646605a2f04ce0d0e00caeb3a5abe`.
The pre-result interpretation caveat for C is also preserved. E's consultation
ordinal is still unscored. No new Ground Truth is claimed.

Each initial agent received one complete packet, no expectations/previous output,
and no validation feedback before submission. Each submitted one immutable file.
JSON serialization tools were permitted. Runtime code and schema stayed fixed
during execution; rejected outputs were neither edited nor promoted.

## Outcomes

| Case | Initial strict validation | Judgment comparison | Semantic review |
| --- | --- | --- | --- |
| C: organizer call | Rejected by an existing exclusion/review-link guard | No initial accepted credit | Group-source failure is gone. Source review bookkeeping still failed. |
| D: active wrong advice | Passed | 8/8 original provisional labels | No material issue found; sequencing audit now retains the independent assurance defect. |
| E: false completion | Passed | 7/7 scored labels; consultation ordinal unscored | Correct false-download inference and independent deductions, with an opening-claim scope qualification. |

**Two of three initial outputs pass strict validation.** This is a count of three
manual submissions, not a production reliability estimate. Compared with the
previous diagnostic, the two targeted contract failures do not recur. That does
not imply all possible contract failures or reasoning errors are resolved.

### C: a retained first failure and separately recorded repair

Several substantive semantic exclusions linked to judgments that did not include
the selected source in their checked/evidence span. The existing guard rejects
the response. It is not waived and the raw first attempt remains failed.

After that failure, one **post-hoc** cold repair was separately recorded. It uses
the runtime `repair_feedback` function and original source/schema, with 22,235
bytes of feedback under the unchanged 24,000-byte allowance. The prior candidate
is truncated and explicitly untrusted. No extra source hints, expected grades or
reference labels were supplied. No additional repair attempt was made.

The repair passes strict validation. All eight status/answer judgments are
unchanged. The model regenerates review links and separates four original
assertions into six atoms; this is not a local edit to its JSON. The final result
remains provisional for consultation and closing, with no fabricated total.
Its identity Yes differs from the assistant-only frozen needs_review recommendation;
that alternative was explicitly identified before any new output. The reference
is not relabeled to turn this into a match. Management 4 also retains the pre-run
ASR/wording-causation caveat; matching that number does not certify it as expert GT.

This repair demonstrates a manual recovery using bounded runtime feedback. It
does not convert the initial result into a first-pass success or establish that
an API repair would finish within the output cap.

### D: legitimate overlapping process evidence is retained

Consultation remains 0 for the active wrong immediate/no-review/confirmed advice.
The supported route survives, and the actual private execution state remains
unverified. Management remains 7 for the unannounced hold.

The revised audit additionally cites the reference prerequisite, reported pending
state and explicit completed-execution assurance. It describes an assurance
against the reported state, not a proven backend action out of order. Both process
findings remain visible even though another level-7 defect keeps the numeric result
unchanged. It does not infer a new identity requirement or empathy complaint.
An independent response review without reference labels found no material issue.

### E: proof metadata is coherent; one inference needs narrower scope

The known false download claim retains both essential premises: the customer's
earlier no-download state and the subsequent no-client-action interval through
the assurance. The combined proof is interaction evidence, not system-only truth.
The hold and claimed-action prerequisite sequence retain independent management
findings. No original ambiguity is resolved by assigning a convenient gold number.

The response also marks the broader claim that the sample was opened during the
session as contradicted. Its proof explicitly concludes that opening did not occur
through the instructed workflow after the reported state, but does not separately
rule out an earlier opening. An independent reviewer identified this scope mismatch.
The atom should be narrowed to what its proof establishes, or the broader status
should remain uncertain unless an additional initial-state premise is established.

This qualification does not remove the independently proved false download or
the legitimate process deductions. It prevents treating valid JSON and matching
criterion labels as complete factual-audit correctness.

## Engineering verification and limits

- 637 tests pass; Ruff and diff checks pass. One existing Starlette deprecation
  warning remains.
- All 79 prepared requests fit unchanged input/repair bounds; the maximum is
  191,620 bytes. All historical v3 schema/payload hashes match their prior values.
- 110 original frozen labels, 12 complete expected vectors, 97 accepted API scores
  and the six previous manual receipts retain their original status and values.
- All initial and repaired responses, validation errors, frozen protocols and
  source hashes are preserved privately. No manual result is inserted as an API
  record or substituted into the production application.
- The usage ledger remains 591 rows and $23.141316 cumulative settled cost, the
  exact pre-run checkpoint. **Incremental API cost: $0.** This is not an account
  balance.

The code fixes remove redundant source bookkeeping and a provably invalid
observation/proof combination; the sequencing guidance improves D's actual audit.
Remaining work is explicit: long-call review-link fragility, negative-proof scope,
proportionate handling of missing facts and production generation feasibility.
These diagnostics do not establish a 95–100 product grade or replace historical
API measurements.

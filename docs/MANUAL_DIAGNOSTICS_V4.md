# V5 contract diagnostics — Sol 6.1 medium

Prompt: `evaluator-v10-08c974f78057`; transport `span-v5`; audit `coverage-v5`.
Implementation: [source contract v5](SOURCE_CONTRACT_V5.md).
Structured results: [preserved audit](../audits/manual-diagnostics-v4-results.json).

Six isolated execution agents and two independent semantic reviewers were
explicitly requested as `gpt-6.1-sol`, medium reasoning, without inherited chat
history. Each executor received one packet, no expected labels or old outputs,
and submitted once without validation feedback. No repairs were made. Reviewers
received the full source, checklist and decoded response without expected labels.
Root adjudication preserves their findings and reference disagreements.

These tool-assisted chat generations are not API benchmarks. They do not reproduce
provider constrained decoding, the configured 6,000-token output cap, API latency,
token costs or repeatability. All outputs and failures remain immutable private
artifacts; none is inserted into the application as a provider result.

## Frozen design and outcomes

C/D/E retain the exact original inputs and expectations, including the unscored
consultation ordinal in E and C's pre-recorded identity/ASR interpretation caveats.
The original expected-file SHA-256 remains
`e16b09eab3ec7639f960e2f01dff2dbd799646605a2f04ce0d0e00caeb3a5abe`.

F/G/H are three newly frozen fictional note-saving controls. Only the initial
system-history text differs. Their custom checklist, six expected judgments,
three complete vectors and source reviews were frozen before inference. They
are targeted calibration, not an untouched holdout or organizer Ground Truth.

| Case | First strict validation | Reference comparison | Complete-assessment disposition |
| --- | --- | --- | --- |
| C: organizer call | Passed | 7/8 provisional labels | Review-link failure is gone; a reasoned identity disagreement and original interpretation caveats remain. |
| D: active wrong advice | Passed | 8/8 | Wrong advice and independent process findings retained; no material semantic issue found. |
| E: false completion | Passed | 7/7 scored labels | Broader opening is now unverified; additional actor/event and route qualifications remain. |
| F: earlier save, false backup | Rejected | No accepted comparison or score | Correct source reasoning does not override incompatible observation metadata. |
| G: neither action completed | Passed | 2/2; total 0 | Actual deductions correct; prerequisite counterfactual has a semantic defect. |
| H: both actions completed | Passed | 2/2; total 100 | Prior successes and fulfilled prerequisite retained; no deductions. |

**Five of six first submissions pass strict validation.** The original C/D/E
subset improves from two of three first passes to three of three. These small
counts do not establish production reliability. There are 26 matching provisional
judgments across 27 accepted comparisons, with two additional frozen F judgments
receiving no accepted credit. This is not an accuracy estimate: references are
assistant-authored, C has a retained disagreement, and semantic defects can
survive matching scores.

## What improved

C no longer has to repeat the same source-to-criterion review link in several
places. The application projects the exact declared source union; it creates no
evidence or grade. The existing review-link guard still runs. Earlier rejected
responses stay rejected under their explicit historical reader.

E keeps the original whole-session opening assertion visible and unverified.
Its later no-action interval is no longer used to disprove an earlier or
alternate-route opening. The independent unannounced-hold deduction remains 7.
The original consultation ambiguity is not filled with a convenient score.

The controls distinguish atomic truth despite two expected totals of zero:

| Control | Original save | Backup | Operational result |
| --- | --- | --- | --- |
| F | Supported by earlier shortcut success | Contradicted by initial history plus complete later interval | Strictly rejected; no score |
| G | Contradicted over all routes and the complete session | Contradicted | Accepted 0 |
| H | Supported by earlier shortcut success | Supported by earlier completion | Accepted 100 |

F's semantic pattern is informative but receives no accepted success credit.
H also preserves the earlier folder selection: a redundant later instruction
does not manufacture a pending-prerequisite violation.

## Remaining failures and qualifications

F exposes a wire/runtime contract mismatch. Its original-save completion is
declared `general_fact`, verification scope `interaction`, observation scope
`system_record`. The wire schema permits that combination, but the existing
dialogue-observation guard rejects it. The error is preserved verbatim:
`Dialogue observations cannot alone verify general product/policy truth`.
Neither JSON editing nor relaxed validation is used to accept the result.

G's `folder_step` canonically says selecting a folder is required, but its false
counterfactual is explained as though only the recommendation's correctness
changed. If that prerequisite proposition is false, the assurance-sequencing
violation does not follow merely from pending folder selection. The actual
reference establishes the requirement, so both actual No judgments remain valid.
The correct total does not make the dependency explanation correct.

E still has two source-interpretation qualifications. A record of no later
**client action** is not literally an exhaustive record of all download events.
The download contradiction assumes a client-triggered workflow; that bridge is
not separately established. Likewise, click-before-open is a prerequisite of
the instructed route, not necessarily every possible session opening. The
review does not assert that an automatic download or alternate opening occurred.
It preserves the source limit, consultation uncertainty and independent hold
deduction. Frozen expectations are not rewritten to make this a match.

C's identity Yes follows a pre-recorded reasonable alternative to the frozen
needs_review interpretation. Management 4 also retains the ASR/wording-causation
caveat. Independent source review finds the actual code clarification persuasive,
but this does not turn an ambiguous assistant reference into expert Ground Truth.

## Verification and cost

703 Python tests pass with one existing Starlette deprecation warning. Ruff and
diff checks pass. The offline candidate check reproduces 82 protected requests;
the maximum is 194,078 of 200,000 bytes. All 79 historical v3/v4 schema/payload
pairs, 97 accepted API scores, original 110 labels/12 complete vectors and ten
previous manual receipts retain their values and accepted/rejected status.

The local backend was restarted with current code. Read-only root/config checks
return HTTP 200; the application retains nine completed and four failed jobs,
with none queued/running. Manual outputs are not application evaluation jobs.

**Incremental API calls: 0. Incremental API cost: $0.** The ledger stays at 591
rows, maximum ID 591 and $23.141316 cumulative settled usage; that is not an
account balance. No product-grade increase or 95–100 claim is justified by this
run. The changes solve specific failures while exposing remaining generation
and reasoning weaknesses.

# Organizer call and negative paired cases — manual diagnostics

Date: 2026-11-07. Engine: `edac8fc`, prompt
`evaluator-v8-ebe6d961965c`, source transport `span-v3`.

This is an isolated chat-agent diagnostic, not an OpenAI API benchmark. The agents
received the complete current evaluator instructions, input and source-bound
schema. They received no expected judgments, previous predictions or other packet
contents. JSON serialization tools were permitted; provider constrained decoding,
the production output cap, API settings, latency and token cost were not reproduced.
The inherited chat model/settings are not verified API metadata.

## Frozen protocol and sources

The private protocol, packet hashes and expectations were saved before any new
response was available. Original rubric, datasets, expected labels and evaluator
code remain unchanged. Each agent writes one response; strict local decoding and
validation happen afterward, with no validator feedback before submission.

- **C:** One organizer call, 78 messages. New source-only assistant review and root
  adjudication supply provisional expectations, including unresolved states.
  These are not organizer Ground Truth or independent expert labels.
- **D:** The original frozen uncorrected-advice case, paired with previously
  manually assessed B. Only message m6 changes. All eight original expected
  decisions are retained.
- **E:** The original frozen false-completion case, paired with previously
  manually assessed A. Only message m3 changes. Seven original decisions remain
  scored; the consultation ordinal remains prospectively unscored.

All other source fields within each pair match exactly. These are development
cases, not a new unseen holdout. A used reported high reasoning and B reported
medium in an external chat; the present agents have inherited chat settings, so
the pairs do not establish a controlled same-settings experiment.

Before seeing any response, a separate caveat recorded reasonable alternative
interpretations for C's identity, consultation and management decisions. A numeric
label disagreement is not automatically an evaluator error. No expectation was
changed to fit the returned output.

## Results

| Packet | Strict local validation | Accepted label comparison | Full-assessment finding |
| --- | --- | --- | --- |
| C | Rejected | No accepted credit | A selected callback occurrence lies outside its declared assertion group. |
| D | Passed | 8/8 original provisional decisions | Correct active-error response; additional sequencing analysis remains qualified. |
| E | Rejected | No accepted credit; original consultation ordinal stays unscored | An unverified claim declares an observation despite having no proof. |

All three original responses and receipts are preserved privately. One passes
strict validation and two are rejected; the valid result also has a qualified
semantic finding. This is a count of three manual submissions, not an API failure
rate. No rejected proposal receives a score or retroactive first-pass credit.

### C: duplicated source bookkeeping remains fragile

Claim c7 selects m76 (`d_o_24`) while its assertion group g4 covers m71/m73.
The exact-occurrence check correctly rejects it. The same source membership is
declared at both atom and group levels, creating another model consistency task.
A future contract could explicitly derive the group source view from its declared
member atoms, while retaining exact source identity, roles, group membership and
composition checks. That would require a separately versioned candidate and new
execution; it would not rehabilitate this rejected v3 response.

The unaccepted proposal recognizes an investigation/callback promise, separates
private order assertions from evidence of backend completion, and retains an
unresolved ending. Its needs N/A and identity Yes differ from the provisional
frozen recommendations. Those are source/rubric adjudication questions, not proven
accuracy errors. Management 4 also requires care: a customer's clarification does
not alone prove poor wording when the preceding code request is intelligible and
audio is unavailable.

### D: the active wrong recommendation fails, while valid facts survive

Consultation is 0, compared with 20 in the previously returned corrected-advice B.
The other seven judgments remain unchanged. The supported route and submission
facts survive; independently false immediate/no-review/confirmed advice remains
active. Customer non-use does not repair it. The operator conversation score is
46.92, not a product grade.

The exact private backend execution state remains unverified, which is correct.
However, the management explanation uses that limitation to dismiss additional
sequencing analysis. A narrower premature-assurance finding can compare the
reference prerequisite, explicitly claimed completion and reported pending state
without certifying private backend truth. The response does not clearly adjudicate
that distinction. The independent unannounced hold still warrants management 7,
so the correct grade can conceal an incomplete audit. Do not report D as flawless.

### E: observation metadata remains insufficiently coupled to proof

The opening claim is unverified and has no proving premises, but declares an
action-completed observation. The decoder rejects this combination. Context-only
citations do not establish the observation. The current wire schema permitted
the combination; it should express the observation/proof dependency directly,
while retaining the decoder guard. No proof or observation was inferred locally.

The unaccepted proposal nevertheless retains the essential two-part proof that
the download did not complete: the earlier negative customer state plus the later
no-action interval. It separates download from opening and retains both the hold
and the independently claimed-action sequencing defect. It proposes unresolved
consultation because of additional route uncertainty while preserving the known
false completion. Those semantic findings do not rehabilitate the invalid output.
The original ordinal ambiguity remains unchanged.

## Next implementation priorities

1. Remove duplicated group-source declarations from a newly versioned provider
   contract and explicitly derive their persisted view from declared atomic source
   selections. Retain exact source, role, membership and composition validation.
2. Couple observation and proof variants in the provider schema; keep the runtime
   rejection of unsupported observations. Do not create proof from context.
3. Clarify the distinction between private backend truth and a process assurance
   made against reported pending prerequisites. Preserve genuine independent
   deductions without upgrading client reports into authoritative private records.

No evaluator change was made during this experiment. Each implementation change
requires its own candidate identity and new execution. C/D/E receipts, old API
benchmarks, original expectations and the pre-result interpretation caveat remain.

## Interpretation

These checks expose concrete remaining contract and reasoning weaknesses without
paid inference. They do not measure production accuracy, API acceptance, runtime
completion, repeatability or Ground Truth agreement. Historical API benchmarks
and their failures remain unchanged. No overall product-grade increase is earned
from these diagnostics alone.

All material stays under the original grading rules; there are no case-ID runtime
conditions, score substitutions, quote cleanup or weakened validation. The usage
ledger remains 591 rows with $23.141316 cumulative settled cost, exactly matching
the pre-run checkpoint. **Incremental API cost: $0.** This ledger total is not an
account balance. No API calls or application/ledger writes were made.

# Lessons from the previous hackathon

This is a source review of the supplied previous-project archive and its saved
behavioral probe. No new experiment, live model call or API spending was performed.
It explains a reproduced failure mechanism, not the previous contest's actual
hidden-test accuracy or judges' reasoning.

## What the saved probe established

`probe_generic_replies.py` used fictional inputs and a **mocked provider**. It set
`Provider.available` to true and replaced `generate` with a local function returning
fixed `ModelAnswer` objects. The saved report explicitly says
`live_model_used: false` and `private_handout_used: false`.

Two different questions received different model acknowledgments but the same
final response: a greeting followed by a generic administrator-confirmation
message. Both outcomes retained `mode: llm`, an accepted composition status and
all seven declared routing/language/priority/handoff/guide checks passing.

That does not mean an actual model failed to understand those questions. The
probe demonstrated that application composition could discard the distinguishing
content after the mocked model had supplied it.

The archive contains the relevant paths:

| Source | Mechanism |
| --- | --- |
| `copilot/service.py:406-419` | Render a policy template first; the personalized path validates a model acknowledgment and renders again, recording an accepted composition. |
| `copilot/replies.py:473-476` | When the topic is a question with no knowledge or rule sources, deliberately remove the acknowledgment. |
| `copilot/replies.py:500-503` | Use the generic topic copy when no supported answer is available. |
| `copilot/service.py:423-448` | A separate generation strategy can use model draft text, but rejects certain unsupported drafts and keeps the controlled replacement. The probe did not exercise a live version of this strategy. |
| `copilot/service.py:88-131,450-453` | A historical administrator-reply index can replace the composed draft. In the saved fictional exact-match probe, the final response asked the user to clarify an already clear question. Similarity/support 1.0 did not establish answer usefulness. |
| `scripts/benchmark_live.py:33-47,57-58` | The default `live_model` check tests the trace's mode string; language, routing and priority checks assess their declared fields. Content checks run only when the case supplies `contains`/`not_contains`, and those are literal checks rather than semantic evaluation. |

The benchmark itself says absence of a check is not a quality claim. The trap was
interpreting success on its declared checks as evidence that the final answer
resolved the user's actual request. The mocked probe also shows why `mode: llm`
alone cannot certify a live call.

## The analogous risk in this project

Freedom CQA's model results are not replaced through that previous-project template
path. However, the same measurement mistake remains possible:

- Valid JSON, real source IDs and verbatim quotes can accompany an irrelevant
  explanation or an omitted customer request.
- A factual-claim audit validates claims the model emits; it does not establish
  that all material operator assertions were extracted.
- Repeated agreement can mean a stable misinterpretation. Agreement with our own
  provisional synthetic labels does not establish agreement with expert judgments.
- Returning `needs_review` everywhere can avoid unsupported claims while leaving
  the product unable to deliver useful assessments. Conversely, forcing numbers
  for missing facts can create false certainty.
- A growing collection of case-specific exceptions can improve familiar examples
  while failing when wording, speaker, order or the configured criterion changes.

The current audit therefore separates reusable facts and evidence requirements
from per-case diagnostic observations. It does not create a lookup from conversation
IDs to scores, promote operator/bot assertions into policy, or rewrite old outputs.

## Reusable safeguards and release gates

1. **Assess the final useful output.** Review every substantial request, relevant
   operator answer/next step and potentially grade-changing assertion against the
   complete source. Citation existence is a necessary check, not the semantic gate.
2. **Separate types of evidence.** Keep official checklist rules, applicable product
   references, observed customer outcomes, private account state, team interpretations
   and provisional labels distinct. A repeated corpus answer is not a policy source.
3. **Keep uncertainty local.** Explain the missing fact and which allowed outcome
   it could change. Retain independent violations. A correction needs evidence and
   does not erase remaining harm or a configured historical-error requirement.
4. **Use consequential contrasts.** When source evidence, verification order,
   unresolved requests or criterion meaning changes, the appropriate judgment must
   respond. Irrelevant rewording should not create arbitrary deductions. Keep both
   violation and legitimate-conduct controls; do not test only expected failures.
5. **Measure separately.** Report validation failures, determinate-score coverage,
   unresolved evidence, criterion agreement, full-vector score error and repeated-run
   changes. Do not turn selected completed-only agreement into an overall accuracy
   claim. Preserve failed first outcomes and all paid attempts.
6. **Demonstrate the actual workflow.** A fresh imported conversation and an edited
   custom criterion must reach the real evaluator; evidence navigation, appeal,
   saved history and recalculation must work on that result. A prepared fixture or
   model-mode label cannot substitute for this demonstration.

Before spending on another benchmark, use the missing-facts inventory and source
audit to identify what evidence or generalized decision rule would actually change.
Then reserve a small unseen set for checking those changes. The organizer deadline
calls for a working, reviewable product; it does not make an unsupported 95-100
quality claim defensible.

The saved probe and previous archive remain outside the current repository. These
references identify source-file locations within that archive and intentionally
omit private handout content, service endpoints and credentials.

## Second participation: context only

The additionally supplied `hack-82e6beb1-proof-by-intimidation-main.zip` was inspected
read-only: its README and three relevant workflow/evaluation files. The user's
reported89/100 was not independently verified and is not attributed to a particular
architecture. The bounded inspection, file hashes and limits are recorded privately
in `artifacts/facts-audit-v1/second-project-context.json`.

That project's useful context is a coherent business workflow, a distinction
between contract checks and semantic quality, and requirements linked to source
material. Its own validation notes also retain harder semantic faults alongside
passing workflow checks. This reinforces the measurement lesson rather than
proving that adopting its design would produce the same contest result.

Its fixed rubric, multiple AI stages and optional offline mode are not transferred
to Freedom CQA's configurable, no-fallback evaluator. No code or scoring logic was
copied from either previous participation.

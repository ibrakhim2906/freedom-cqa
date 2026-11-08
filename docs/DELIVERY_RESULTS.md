# Delivery implementation and observed results

## Current user-selected grading policy

The user explicitly required a numerical grade for every assessed conversation
and authorized the team to select the reference context. The v3 core selects
actual rubric levels from the complete source; uncertainty remains attached to
those decisions. It never fills missing scores with a zero, midpoint or maximum.
The 22 earlier unscored inputs were reassessed using the explicit assumed
Freedom Finance Global platform snapshot of 2026-11-07 and reviewed016. Original
source dates/scope/messages stay unchanged. The previous 43 numerical outputs
and all historical reports remain preserved. An additional $2 was explicitly
authorized, increasing the total additional cap to $7. The targeted reassessment
has its own $2 ceiling. Final DEV output: **65 ok, 0 errors, all 65 numerical**. The original 43 numerical
results remain on reviewed015/v2 ; 22 reassessments use reviewed016/v3.

The observations below describe their actual contract and phase; older abstention
results are historical, not the behavior of the new numerical policy.


8 November 2026. This report concerns the new delivery branch, not an official
organizer score. Earlier runs remain unchanged in their original artifacts.

## Implemented

- Compact rubric-first assessor with exact source selections and code-derived
  quotations, deductions and scoring. No global proof graph or counterfactual tree.
- Independent source review of selected consequential criteria, with adjudication
  for disagreements and explicit handling of failed/incomplete review.
- Contract-aware exports that revalidate native results and preserved projections.
  Conditional references only block export when a criterion actually relies on them.
- Professional review UI, queue search/filters, exact evidence highlighting,
  score contributions, review warnings, failure recovery and saved-result comparison.
- Configurable evaluation depth, immutable checklists, original/reviewed history,
  appeals and recalculation, and genuine saved-report import without inference.

## Live development results

The first compact candidate retained an unnecessary generated deduction object.
Four of seven follow-up cases failed because binary No decisions omitted that
redundant object, even after repair. The selected labels in those rejected outputs
were diagnostically useful, but the outputs remain failures.

Version2 removes that duplicated generation duty. Code projects the configured
rule, criterion explanation and evidence into a deduction record without changing
the model's selected grade. Historical v1 validation remains unchanged.

| Check | Observed result |
|---|---|
| V2 live cases | 8/8 first-pass complete, no repairs |
| Predeclared determinate decisions | 49/49 matched |
| Custom changed criterion | 100 → 0 with the same source conversation |
| Additional independently reviewed cases | 2/2 complete; selected decisions confirmed |
| Focused integrated checks | 30 passed; one existing dependency warning |
| Frontend | Production build passed; desktop/mobile walkthrough and saved comparison worked |

The eight cases comprise six multilingual scenarios and two custom-checklist
versions. One corrected-advice ordinal was excluded before inference. The cases were
already used to diagnose the preceding candidate, so this is regression evidence. A source
review found no definite consequential error in the other five scenarios, while
retaining that corrected-advice interpretation as a qualification. Authors and
reviewers are AI assistants; this is not independent expert validation.

Paid artifacts under ignored `artifacts/delivery/` preserve `probe-01`,
`focused-01` (including failures), `focused-02`, and `reviewed-01`. The new full
organizer run is `dev-01`; budget-skipped call inputs were completed in
`dev-calls-completion-01` and `dev-call-final-01`. No completed result was replaced
by a more favorable repeat.

Current limitations: no organizer expert labels, genuine policy/source gaps,
transcript-only call assessment, and a local single-process demonstration.
No numerical product grade is inferred from a small development suite.


## Full DEV outcome

All 65 original conversations produced valid internal assessments. **43 have
final numeric scores ; 22 require review**. There are19 unresolved consultation
judgments,6 closing judgments and1 contact judgment (some conversations overlap).
The official JSON1.0 export contains all 65 original IDs:43 ok and 22 explicit
errors. This is output coverage, not measured expert accuracy.

60 of 65 completed on their first attempt; 5 required one mechanical repair each.
The 60 chats used the initial compact-v2 prompt. The 5 calls used the later generic
criterion prompt; the final call used a4300-token output cap to stay within the
remaining protected allowance. All used the exact saved reviewed015 checklist.
Each record retains its actual prompt hash, limits, attempts and usage.

Local estimated additional API cost for this delivery work is **$4.088872**.
This is not the provider's account balance: the user reported $0.60 remaining
before the final submitted call. No further paid runs were started afterward.
A prepared new custom demonstration remains **unrun** to conserve that balance.

## Fixes from the independent project review

- Current assessor instructions defer to custom criteria combining dimensions
  and no longer impose original-rubric10/0 grading anchors.
- The optional second assessment checks every criterion, including full-credit
  binary answers. Orchestration compares every returned decision and preserves
  revised decisions through the effective API/UI/export projection. A focused
  synthetic composition check verifies this; it is not a live accuracy result.
- Custom flag values such as `violation` display exactly with their configured
  description and neutral styling. A browser-render check verified the result.
- Accepting an appeal requires explicit supporting messages or a checked omission
  interval. Disputed evidence is not copied automatically. A real browser/backend
  check verified the selected support, counterevidence, interval, recalculation,
  immutable original and persisted history without new inference.
- The user's explicit corrected-prerequisite calibration is saved as reviewed016:
  consultation 15/20 when corrected before action and resolved without established
  remaining consequence. It applies to new runs; old labels/results remain intact.

A source-only audit identified a potential unnecessary abstention in EN001: an
independently reported taken-login obstacle supports the proposed different-login
next step, while the causal retention explanation remains unverified. The current
prompt distinguishes supported next steps from incidental explanations and keeps
review for material policy questions. This refinement has offline checks only;
saved DEV outcomes were not rerun or relabeled.

The [knowledge-gap list](DELIVERY_KNOWLEDGE_GAPS.md) identifies the actual missing
source/context information. The official submission is original-AI-only; the full
application export separately includes effective human judgments and review history.


## Final delivery candidate

`results/dev/results.json` validates with **65 original IDs, 65 numerical scores,
65 ok and 0 errors**. It is a mixed preserved/reassessed result set:43 numerical
v2/reviewed015 assessments and 22 v3/reviewed016 assessments. The release receipt
pins each selected report and record origin. No original transcript was rewritten.

The targeted reassessment exposed two actual interpretation issues. A general
eligibility question was incorrectly expanded into a reported blocked-funds
situation; its targeted correction now gives the appropriate full consultation
answer. Consecutive ASR fragments were incorrectly treated as separate initial
requests. The prompt now groups the initial client turn correctly, but the call's
needs-discovery No remains disputed because the new rationale requires an order
identifier whose necessity is not established. Its original numerical output was
preserved and a clearly attributed AI source-review appeal was opened. The
operator's independently evidenced wrong-topic/clarity problem was not removed.

The last call needed one explicit repair of incorrect source-role selections.
The failed attempt is retained and linked by response ID to its repair. Final
corrections were predeclared before inference; no desired grades were supplied.

Estimated additional delivery spend is **$5.874589 of the authorized $7**;
the reassessment/corrections portion is **$1.785717**. These are local token-based
estimates, not the provider's balance or invoice. Historical estimates omitted
cache-write detail and did not record returned service tier. Future requests now
explicitly select standard service, retain cache reads/writes and returned tier,
and use the documented rates with a cache-write allowance in reservations.
[Official model pricing](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
was checked on 2026-11-08. Historical charges were not rewritten as invoice facts.
There are no pending paid requests. Single-attempt mode is available to avoid
reserving a second call when intentionally running without automatic repair.

The new result has been imported into the application. Actual v3 numerical output,
uncertainty, source highlights and comparison with an earlier unscored revision
were checked in the browser. The final frontend build passed. Source-role/export,
review composition, cache pricing and single-attempt accounting received focused
offline checks; no large repeated full-suite run was used.

The ten unseen PROD inputs have not been supplied. `scripts/prepare_control_run.py`
and `docs/CONTROL_RUN.md` preserve those actual sources, freeze configuration and
lead through bounded inference and official export once available. No placeholder
PROD output or inferred organizer accuracy score was created.

# Measured performance

Measured on 8 November 2026 with **OpenAI `gpt-6.1-sol`, medium reasoning**. These are development measurements against declared AI-reviewed references, not organizer Ground Truth or a predicted competition score.

## Latest behavioral check

The [frozen 17-case panel](../evals/final-rubric-panel-v1.jsonl) has eight primary conversations, four translations, two irrelevant paraphrases and three identical repeats. Two AI reviewers independently agreed on all 64 primary decisions before inference. Its [freeze manifest](../evals/final-rubric-panel-v1.review.json) records sources, settings, hashes and an empathy-boundary qualification for case 406.

| Measurement | Observed result |
|---|---|
| First run, without automatic retries | **15/17 valid assessments**, two validation failures |
| Primary reference decisions, failures counted incorrect | **56/64**; seven of eight primary conversations completed |
| Primary score error on completed cases | MAE **0**, seven conversations; failed case excluded from MAE only |
| Controlled language agreement | **32/32** decisions across four RU/KZ translations |
| Paraphrase / repeat comparison | **8/16** and **16/24** delivered comparisons; failed base/variant counts as missing |
| First-run latency | Median **20.05s**, p95 **27.51s** per assessment |
| First-run estimated cost | **$0.848159**, including both failures; $0.050 per attempt |
| Fresh targeted check after correction | **3/3 valid; 24/24 decisions matched**, $0.177401 |

Both failures used valid operator-conduct quotations alongside applicable policy and independent customer/system evidence. The validator incorrectly rejected the additional operator role. The correction accepts that combination while still requiring independent customer/system support; an operator's claim alone cannot verify policy or private state. The targeted check included both failed cases and a disclosure-violation control.

Offline revalidation of all 17 saved responses succeeds without changing any model grade, status or explanation. Their eight primary vectors match all 64 references with MAE 0; translation, paraphrase and repeat decisions also match. This is **offline replay**, not a new 17/17 first-pass run. The original run used `7332f3e2dfe4`; the corrected candidate and three fresh checks use `042dd1f149fb`. Source review found no definite semantic grade error across the 136 raw decisions, with the predeclared empathy interpretation still qualified.

## DEV results and product behavior

### Pre-control reliability correction

Two independent AI reviewers assessed six selected DEV conversations from source
before seeing the saved judgments. The substantive deductions were supported;
remaining disagreements involved rubric boundaries, account-selection details and
noisy speech. This was a diagnostic audit, not a random accuracy benchmark or
human Ground Truth.

A fresh long-call assessment failed because its negative serious-error flag had
neither dialogue evidence nor a checked interval. The v3 generation schema now
requires either nonempty evidence or a checked interval for every judgment,
including negative flags. Source-role and exact-evidence validation remain in
place. The previously failing call then completed in a fresh request without a
retry ($0.097856, 39.14s). That check used a 5,000-token ceiling to preserve the
control budget; the application default remains 6,000. The two runs interpreted
an unclear introduction differently and both disclosed uncertainty, so successful
validation does not establish stable expert-level accuracy. Original outputs and
the DEV submission were not replaced.

All 65 selected saved assessments still validate, with all 520 grade/rationale
pairs and 65 totals unchanged. The integrated Python suite passed 805 tests.
Local evidence is preserved under ignored `artifacts/precontrol-audit/`.

- [Official DEV export](../results/dev/results.json): **65/65 numerical results, 65 ok, 0 errors**; 20 assessments retain material uncertainty. These are completed assessments, not measured expert agreement.
- DEV preserves 43 v2/reviewed015 and 22 v3/reviewed016 assessments. Conditional policy assumptions remain explicit in their rationales.
- A source audit restored nine omitted factual-support evidence turns across five DEV conversations. All 65 totals and 520 grade/rationale pairs stayed unchanged.
- An earlier fresh custom-criterion pair changed the same conversation from 100 to 50 on a configured 0/1/2 scale. Actual judgments, explanations and scores survived API/UI/full-export inspection.
- Exact source navigation, immutable revisions, appeals, recalculation, visible failures and saved-result persistence were exercised. An actual supplied call recording played; model assessments still use transcripts, not audio.
- Isolated Windows and Linux installs built and served an empty workspace with current defaults and no private development files. The UI continues to receive usability improvements; a clean install does not substitute for an independent user study.

## Cost and limitations

The initial 65 DEV assessments used 70 attempts at approximately **$3.21 / $0.049 per conversation**. Later difficult reassessments averaged about $0.081 per conversation. A long-call correction took 64.61 s and $0.103776. Costs depend on input/output length and retries; local estimates can differ from provider billing.

Standard mode normally uses one assessment call. Independent review adds a blind assessment of every criterion and, on disagreement, adjudication. Mechanical repairs are bounded; all calls count against batch and cumulative spending limits. Inspecting saved results and resolving a human appeal make no model calls.

The samples are small and authored; controlled translations and repeats are not independent accuracy samples. Policy applicability, noisy transcripts and rubric-boundary judgments remain sources of uncertainty. The 11:00 control dataset has not yet been evaluated. Raw runs and runtime databases remain local and ignored by Git.

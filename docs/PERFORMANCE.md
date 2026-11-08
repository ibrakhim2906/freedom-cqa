# Measured performance

Measured on 8 November 2026 with **OpenAI `gpt-6.1-sol`, medium reasoning**. These are development measurements against declared AI-reviewed references, not organizer Ground Truth or a predicted competition score.

## Russian checklist 017 release comparison

The release candidate now selects the Russian **`1-reviewed-017`** checklist
through one shared default for the API, CLI and control preparation. The evaluator
prompt remains **`rubric-assessor-v3-963619247384`**. Version 016 and its historical
results remain available unchanged. Translation changes the model input, so its
behavior was measured separately; identical weights alone were not treated as
proof of equivalent assessments.

The comparison reused the ten synthetic conversations against their previously
frozen references. It is **diagnostic comparison evidence, not a new held-out test
or organizer-label accuracy**. See the [compact 017 results](../evals/checklist017-validation.results.json).

| Measurement | Observed result |
|---|---|
| Reused ten-case comparison, no automatic retries | **10/10 completed** |
| Unambiguous reference judgments | **79/79 matched** |
| Comparison with 016 | **80/80** answer/status/uncertainty flags and all ten totals unchanged |
| Aggregate score error | MAE **0**, nine eligible conversations |
| Unknown closing opportunity | Remains explicitly uncertain; excluded from strict agreement and score MAE |
| Native source validation and score replay | **10/10 passed** |
| Additional known boundary cases | **2/3 completed**; **16/16** judgments matched on those two |
| Additional boundary source validation and score replay | **2/2 passed** |
| Ten-case comparison cost and p95 latency | **$0.621349**, **22.77 s** |
| Two completed boundary cases | **$0.132105** estimated cost |

Independent source review covered all 80 comparison judgments and the 16 completed
boundary judgments, including their explanations. It found no definite grading
error or matching grade with an unsupported explanation. The two completed
boundary cases check customer versus employee verification, private disclosure,
corrected wrong advice, and a coworker farewell that must not count as closing
with the customer. These are reused synthetic cases, including a 17-turn call;
they do not establish general long-call performance or performance without policy
context.

The third boundary case, `panel-404`, was first skipped at the local budget
boundary. Four separately recorded requests then received HTTP 429
`credit_balance_exhausted` and returned no assessment: the completion,
after-top-up, after-delay and funded attempts. Each is recorded as
`provider_rejected` with settled cost **$0**. That case is still incomplete, and
**3/3 is not claimed**. The total recorded cost of the 017 comparison and boundary
attempts so far is **$0.753454**. Any later successful attempt must retain this
history and be reported separately.

## Release validation snapshot

At the 8 November release checkpoint, **899 Python tests**, **42 Node tests** and
**4 browser integrity tests** passed; Ruff also passed. These counts describe the
checked source snapshot, not a guarantee for later changes. The offline Python
suite includes accepted-appeal score recalculation and preservation of historical
assessment snapshots.

A separate clean Windows source checkout passed **898 Python tests with one expected private-DEV skip**,
**42 Node tests**, a fresh frontend build and no-key startup with checklist 017.
Demo reference applicability, failed-envelope rejection, saved-result persistence
and schema/full exports passed with no model requests. Credentials and private
development data were excluded. Locked dependencies used available package caches;
cold-cache network installation was not measured.

A fresh browser workflow assessed the same conversation under two custom rule
configurations and produced **100 then 50**, at a combined model cost of
**$0.033017**. Evidence navigation, a cached read with **$0** additional spend,
appeal handling and reload preserved the original assessment results. This
workflow's appeal was **rejected**, so the second score stayed **50**; it does not
claim a live accepted-appeal recalculation. The first browser-test attempt failed
on a locator; the corrected test passed without another model call. This is a
configuration and persistence check, not another accuracy benchmark.

## Earlier frozen evaluation with checklist 016

Candidate **`rubric-assessor-v3-963619247384`** clarifies closing summaries, task identifiers versus identity verification, and opening turns split across call-transcript fragments. The saved checklist, scoring arithmetic and historical assessments are unchanged. All inspected explanations in the twelve fresh assessments were in Russian; evidence quotations retained their original language.

The [new ten-case set](../evals/fresh-release-v2.jsonl) contains four RU, three KZ and three EN conversations, including two synthetic call transcripts. An independent AI reviewer labelled all eight criteria from source before seeing the author's labels; another reviewed the four boundary criteria. The evaluator was frozen before the root reviewer read the cases. See the [reference provenance](../evals/fresh-release-v2.review.json) and [compact measured results](../evals/fresh-release-v2.results.json).

| Measurement | Observed result |
|---|---|
| Corrected set, no automatic retries | **10/10 completed**, no failures or budget skips |
| Unambiguous reference judgments | **79/79 matched** |
| Aggregate score error | MAE **0**, nine eligible conversations |
| Ambiguous closing | Provisional No with explicit uncertainty; excluded from strict agreement and score MAE |
| Two preselected identical repeats | **16/16** answer/status/uncertainty-flag comparisons and both totals unchanged |
| Exact source validation and score replay | **12/12 assessments**, including repeats |
| Main-run latency | Median **19.06 s**, p95 **25.13 s** |
| Main-run cost | **$0.582992**, about $0.058 per conversation |
| Repeat cost | **$0.040533** |
| Offline suite | **822 Python tests passed** |

A setup mistake in the initial fixture gave every policy an incompatible scope. The application correctly excluded those references and retained factual uncertainty. That run completed eight cases and skipped two at its budget boundary, costing **$0.474926**; it is not claimed as policy-grounded accuracy. The corrected fixture changes only `knowledge_scope`: transcripts, policy text, reference labels and the evaluator are identical. Both fixture versions and the correction record are retained. Eleven offline tests now guard applicability and preservation of the frozen labels. Total cost including this setup mistake, the corrected run and repeats was **$1.098451**.

Source review of all 80 corrected-run judgments found no definite grading error or matching answer with an unsupported explanation. All 185 selected source spans validate; the repeats add 31. The unknown closing opportunity in `fresh-v1-ru-03` remains an explicit limitation, not a uniquely established negative judgment. Two repeats are a small consistency check, not additional independent accuracy samples. No human or organizer Ground Truth was used.

To reproduce the corrected panel with a configured API key and sufficient local/provider budget:

```sh
python -m cqa.cli benchmark --cases-file evals/fresh-release-v2.jsonl --strategy assessor --checklist checklists/freedom-reviewed-016.json --repair-attempts 0 --concurrency 1 --budget-usd 0.90 --output artifacts/verification/fresh-release-v2.json
```

Use a new output filename for each run. The batch cap includes conservative allowance for the next request; it is not the expected bill. Reference labels stay outside the model input.

An earlier 17-case panel had eight primary conversations plus translations/paraphrases/repeats. Its first run delivered 15/17; a validator correction passed three targeted fresh checks and replayed all saved responses. Those historical results are separate from the latest ten-case measurement.

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
pairs and 65 totals unchanged. At that checkpoint the integrated Python suite passed 822 tests.
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

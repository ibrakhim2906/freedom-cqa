# Freedom CQA

Conversation Quality Analytics prototype for the Freedom Broker hackathon.

Status: the local React/FastAPI workflow is implemented: conversation import,
versioned checklists, real evaluations, evidence inspection, saved results and
appeals with preserved AI/human history. The benchmark CLI remains available.

The current [source contract v5](docs/SOURCE_CONTRACT_V5.md) derives review links
from explicit source relations and requires negative proofs to match the full
assertion scope. Historical results and frozen expectations remain preserved.
The [six-case manual rerun](docs/MANUAL_DIAGNOSTICS_V4.md) records five strict
passes, one retained rejection and remaining semantic qualifications, at $0 API
cost. These diagnostics do not establish production accuracy or reliability.

## Run the application

```powershell
./scripts/start-local.ps1
```

Open **http://127.0.0.1:8000**. Configure the backend key in the ignored `.env` first.
See [workflow, startup and verification details](docs/WORKFLOW.md) for imports,
reference context, spending limits, review decisions and remaining limitations.

The [official product-facts research](docs/OFFICIAL_PRODUCT_FACTS.md) adds a scoped,
optional reference pack integrated with [scope/date preview, immutable evaluation inputs and appeals](docs/WORKFLOW.md).
[Five complete assessment reviews](docs/COMPLETE_ASSESSMENT_REVIEW.md)
show how those facts affect useful judgments while preserving genuine deductions
and unresolved evidence. These are conditional manual reviews, not new benchmark results.

The [six-case acceptance suite](docs/OFFICIAL_FACTS_ACCEPTANCE_V1.md) freezes all
48 provisional expected judgments before paid inference. Verify the pinned inputs,
sources and label isolation for free with `uv run python -m scripts.verify_official_acceptance`.
The [first authorized real run](docs/OFFICIAL_FACTS_ACCEPTANCE_V1_RESULTS.md)
produced four valid assessments and two strict evidence-contract failures. It cost
$0.5133 using provider-reported tokens and cache-aware pricing. The original
expectations and freeze remain unchanged.

## Evaluator quick start

```powershell
uv sync --dev
# Configure OPENAI_API_KEY in the Git-ignored .env file.
uv run cqa check-config
uv run pytest -q
# Optional billable single-case check; use a fresh output filename.
uv run cqa benchmark --cases-file evals/core-anchors-v4.jsonl --case core-language-wrong --concurrency 1 --budget-usd 0.20 --output artifacts/benchmark/new-run.json
```

See [benchmark setup, data provenance, and result interpretation](docs/BENCHMARK.md).
There is no offline evaluation fallback.

New evaluations use the grounded evaluator and versioned
[reviewed checklist](checklists/freedom-reviewed-015.json). The
[rubric journal](docs/RUBRIC_DECISIONS.md) distinguishes accepted decisions from
the documented team interpretation R013. The original
`checklists/freedom-v1.json` remains available through `--checklist` for comparisons.
The [internal 100-point product rubric](docs/SOLUTION_GRADING_RUBRIC.md) distinguishes
our engineering targets from the organizer's actual selection priorities.

The latest [claim-dependency and corrected-advice checks](docs/CLAIM_DEPENDENCY_RESULTS.md)
recover the four frozen organizer validation failures while preserving real
deductions and unresolved evidence. The focused checks cost $1.69 including the
baseline; they do not establish organizer Ground Truth accuracy. The preceding
[65-case review](docs/ORGANIZER_65_REVIEW.md) remains preserved unchanged.

The subsequent [offline source audit](docs/EXISTING_RESULTS_AUDIT.md) reviews all
65 source/result pairs and the supplied materials without paid calls or score
changes. Its [missing-facts inventory](docs/MISSING_FACTS_INVENTORY.md) separates
24 reusable evidence topics from case labels and team interpretation choices.

The [evidence-context and semantic-coverage implementation](docs/EVIDENCE_CONTEXT_COVERAGE_RESULTS.md)
adds source-date provenance, grading-rule evidence, explicit answer support and
inspectable source exclusions. It passed local compatibility and rejection checks
without paid API calls; live model quality and provider acceptance remain untested.

The first real run is recorded in [baseline results](docs/BASELINE_RESULTS.md),
with [all-run coverage and spending](docs/BENCHMARK_RUN_SUMMARY.md) and
[reference-label review notes](docs/REFERENCE_REVIEW.md). These metrics are
development diagnostics, not organizer Ground Truth accuracy.

The [updated-rubric benchmark](docs/CALIBRATED_BENCHMARK_RESULTS.md) covers 117 real
API evaluations, a 24-case same-input control, and targeted checks. It reports
criterion agreement separately from score error and the loss of numeric coverage.

The [core workflow experiment](docs/CORE_EXPERIMENT_RESULTS.md) adds 14 fresh
diagnostic conversations, actual-request repeat checks, and transparent score bounds
for unresolved criteria. The experimental two-call evidence-first strategy added
cost without improving the tested judgments and was not promoted.
The report preserves a 6.93-point repeated-score drift and the remaining source
and reference limitations; passing the local anchors is not organizer accuracy.

The [grounded validation results](docs/GROUNDED_VALIDATION_RESULTS.md) complete the
earlier [interrupted candidate comparison](docs/GROUNDING_AND_OVERLAP_RESULTS.md).
The single-call grounded evaluator is now the default, with scoped references,
factual-claim citations and rule-linked deductions. The report preserves the
organizer example that needs review, reduced numeric coverage, costs and limits.
The legacy mode remains available through `--strategy direct` with an older checklist.

The [semantic review](docs/SEMANTIC_REVIEW.md) distinguishes suspected evaluator
mistakes from ambiguous labels. Original datasets remain frozen;
[structured review notes](evals/label-review-v2.json) do not override their expectations.
The [next evaluator experiment](docs/NEXT_EVALUATOR_EXPERIMENT.md) explains why a
full rewrite is not currently justified and how to compare substantive alternatives.
`uv run python -m scripts.prepare_human_review` prepares private source-based review
items without model predictions or paid API calls; existing review files are preserved.

To compare a frozen custom diagnostic file with bounded concurrency:

```powershell
uv run cqa benchmark --cases-file evals/review-v2.jsonl --concurrency 1 --budget-usd 0.40 --output artifacts/benchmark/my-review-run.json
```

Each new evaluation is billable. Reopening saved results should reuse the saved
evaluation when web persistence is implemented. Observed organizer averages before
the semantic comparison were approximately $0.026/chat and $0.046/call transcript,
excluding hosting and audio transcription; longer inputs and repairs cost more.

## Product goal

Let a quality reviewer configure a checklist, evaluate an operator's conversation,
inspect the evidence behind each judgment, and resolve appeals with a preserved
decision history. Support Russian, Kazakh, and English.

## Agreed design principles

- Evaluate the meaning of the saved criterion against the actual conversation.
- Preserve speaker attribution and original timestamps.
- Produce criterion-specific judgments, explanations, and evidence references.
- Use code for validation and score calculation.
- Keep insufficient evidence distinct from not applicable and from a failed criterion.
- Show unresolved evaluation failures explicitly; do not substitute generic judgments.
- Preserve checklist versions, original evaluations, and human review decisions.
- Verify the final displayed assessment using paraphrases and controlled evidence changes.
- Use the real API evaluation path; there is no offline evaluation fallback.

## Selected stack

React, TypeScript, Vite, and CSS Modules for the frontend; Python, FastAPI, and
Pydantic for the backend; SQLite with SQLAlchemy for storage; OpenAI API for
evaluation; pytest and Playwright for testing. The initial benchmark uses
gpt-6.1-sol at medium reasoning; final model selection remains open.

See [the stack and evaluation policy](docs/STACK.md) for responsibilities, failure
handling, and the first implementation milestone.

## Selection priorities

Accuracy against organizer Ground Truth on 10 unseen transcripts is the main
top-50 selection criterion. Functionality, usability, genuine analysis of new
inputs, and diversity of technical approaches also inform selection.
See [the organizer announcement](docs/JUDGING.md); no official numeric weights
have been supplied.

## Development environment

Use the Windows-native desktop agent and this Windows checkout initially.
The earlier browser/computer-use limitation with a WSL-hosted project has not
been verified as resolved in this session. WSL is available for targeted commands
if useful. The selected stack and unresolved implementation choices are recorded
in [the stack document](docs/STACK.md).

## Materials and open questions

- The student guide and Freedom introduction have been reviewed.
- Access to the DEV API was verified: 65 conversations were returned.
- The official eight-criterion checklist has been supplied and reviewed.
- All 65 DEV transcripts have been inspected; see [the data audit](docs/DATA_AUDIT.md).
- See [the evaluation design for discussion](docs/EVALUATION_DESIGN.md), including
  the organizer's chat/call clarification and our own test-dataset strategy.
- Sample rubrics discussed in chat are illustrative, not official scoring rules.
- Keep dataset records, call recordings, signed API URLs, and credentials outside Git.
- The guide requests a public repository for submission; this repository starts private.

## Progress

See [the progress checklist](docs/PROGRESS.md). The application and CLI share the
grounded evaluator and scorer. The local browser workflow has been exercised
through real API calls and reference-backed human review.

The current [evidence contract](docs/EVIDENCE_CONTRACT_V2.md) strictly separates
answer proof, omission context and claim observations. The updated evaluator
has [a six-case live result](docs/EVIDENCE_CONTRACT_V2_LIVE_RESULTS.md): six valid
first-attempt assessments and 48/48 frozen provisional judgments matched. The
frozen baseline and prior API results remain unchanged; broader reliability is
tested in a [fresh repeated-run experiment](docs/FRESH_REPEAT_V1_RESULTS.md).
That run failed its reliability gate: 18/24 first-pass and 22/24 final valid outputs;
evidence-chain and compound-counterfactual precision also remain open.

The subsequent [source-span and atomic-proof implementation](docs/SOURCE_SPANS_AND_ATOMIC_PROOFS.md)
addresses those mechanisms offline: source-selected citations, canonical observation
text and explicit proof dependencies. Its live reliability remains unmeasured;
the historical benchmark above has not been replaced or rescored.

[Three subsequent manual diagnostics](docs/MANUAL_DIAGNOSTICS_V2.md) exposed two
remaining contract failures and a qualified sequencing audit without API spending.
One response passed strict validation and two were rejected; these results are
not a production API benchmark or a new accuracy claim.

The [v4 source contract](docs/SOURCE_CONTRACT_V4.md) removes duplicated group
citations, couples observations to proofs and clarifies sequencing audits. In the
[Sol6.1medium manual rerun](docs/MANUAL_DIAGNOSTICS_V3.md), two initial responses
validate; the organizer call validates after one separately recorded model repair.
Remaining proof-scope and interpretation qualifications are retained. No API
inference was used and historical results remain unchanged.

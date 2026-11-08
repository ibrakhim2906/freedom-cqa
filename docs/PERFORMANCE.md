# Measured performance

Measured on 8 November 2026 with **OpenAI `gpt-6.1-sol`, medium reasoning**. These are development measurements, not organizer Ground Truth or a predicted competition score.

| Check | Observed result |
|---|---|
| Official DEV export | **65/65 numerical results; 65 ok, 0 errors** |
| Material uncertainty | 20 DEV assessments retain explicit qualifications |
| Fresh behavioral challenge | 8 attempts; 7 first-pass valid outputs |
| Declared reference decisions | 24/25 delivered matches; failed output counts as incorrect |
| Complete reference vectors | Mean absolute score error 0 across four vectors |
| Changed custom criterion | Same conversation changes from 100 to 50 on an actual 0/1/2 scale |
| Fresh challenge latency | Median 15.89 s; p95 21.41 s per assessment |
| Fresh challenge cost | $0.329345 total, including the failed attempt; $0.041 per attempted assessment |
| Targeted long-call reassessment | One valid result; 64.61 s; estimated $0.103776 |

## What the measurements mean

The fresh fixture and its labels are in [delivery-unseen-v1.jsonl](../evals/delivery-unseen-v1.jsonl) and its [review manifest](../evals/delivery-unseen-v1.review.json). Labels were authored before inference. They are provisional AI-reviewed references; one matching Kazakh consultation label has a linguistic ambiguity. Translations, repeated inputs and small authored samples do not establish population accuracy.

That batch used `rubric-assessor-v3-d6013d521311`. Its rejected response cited an unsuccessful operator reply for an unanswered request. The current `7332f3e2dfe4` representation accepts that saved response with its original grades and unanswered status intact; the reported first-pass result remains **7/8**. The later long-call check used the current version. No failed attempt was overwritten or counted as a fresh successful call.

The DEV export preserves 43 v2/reviewed015 results and 22 v3/reviewed016 results. Numerical completion is not measured agreement with expert grades. Conditional knowledge assumptions and remaining uncertainty are retained in the exported rationale.

## Cost and review depth

The initial 65 DEV assessments used 70 attempts, including repairs, at an estimated **$3.21 total / $0.049 per conversation**. The later 22 difficult reassessments and corrections averaged **$0.081 per conversation**. Costs vary with transcript length, output length and retries; local token-based estimates may differ from provider billing.

Standard mode normally uses one assessment call. Independent review adds a blind assessment of every criterion and, on disagreement, adjudication. Each stage permits at most one mechanical repair by default. All attempts count against the configured batch and cumulative spending caps. Opening saved results, navigating evidence and resolving a human appeal make no model call.

## Product checks

- Actual generated judgments, rationales and scores survived API, UI and full-export inspection unchanged.
- Criterion changes, exact evidence highlighting, immutable source revisions, appeals and score recalculation were exercised.
- An actual supplied call recording opened its external player and playback advanced without a media error. The model still evaluates transcripts, not audio.
- Isolated Windows and Linux installs built and served the application with empty storage, current defaults and no private development files.

Raw development runs and runtime databases remain local and ignored by Git. The required available result artifact is [results/dev/results.json](../results/dev/results.json).

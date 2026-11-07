# Reference-label review after the initial baseline

The v1 dataset and first-run report are preserved unchanged. These notes do not
retroactively improve the baseline metrics and do not constitute human adjudication.

## Optional filename detail: auth-en-secondary-detail

The provisional expectation was consultation 15: main task resolved, secondary
detail omitted. The evaluator returned 20 because the customer explicitly withdrew
the optional filename question after successfully downloading the report.

That explanation is defensible, and the case as written is a weak anchor for a
15 rating. A future dataset revision should distinguish an outstanding secondary
detail from a withdrawn request. Keep the original disagreement visible.

## Closing after connection loss: p1-en-009

The provisional expectation was closing N/A, based on the explicit connection-loss
event. The evaluator returned No, interpreting the customer's confirmation as an
opportunity for a normal closing before the connection was lost.

The official condition is that the conversation ended before there was an
opportunity to close, not that every connection-loss event automatically produces
N/A. The supplied case does not explicitly state whether that opportunity existed.
Neither a fixed silence threshold nor a prepared result should settle the question.
This needs reference-policy/label review rather than forced prompt tuning.

## Structural failures are a separate problem

Five first-run evaluations were rejected for an invalid checked-message reference
or a non-verbatim/misreferenced quote. They remain failures in end-to-end metrics.
The next version constrains message/criterion IDs in the response schema and
permits one explicitly recorded, costed validation-repair attempt. It does not
substitute scores or compare against test expectations during repair.

All five previously rejected cases returned valid results on the targeted recheck.
That is a small development regression check, not an independent reliability study.

## Remaining evidence gap

Most organizer judgments lack reference labels. Eight authored cases have complete
reference vectors, but largely belong to a simple shared scenario family. Their
zero aggregate-score error is not representative evidence for overall score accuracy.

The next valuable step is to review a broader set of full criterion vectors,
particularly consultation scale boundaries, closing opportunity, and noisy calls.
Keep these labels frozen before further prompt/model comparisons.

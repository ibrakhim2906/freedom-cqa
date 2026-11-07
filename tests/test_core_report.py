from copy import deepcopy

import pytest

from scripts.report_core_experiment import repeat_stability


def paired():
    baseline = {"suite_sha256": "same-frozen-suite", "summary": {}, "rows": [
        {"case_id": "one", "record": {"status": "completed", "request_fingerprint": "identical-inference",
         "evaluation": {"judgments": [{"criterion_id": "new", "status": "scored", "answer": "complete"}]},
         "score": {"total": 100}}}]}
    return baseline, deepcopy(baseline)


def test_stability_includes_every_judgment_and_reports_score_drift():
    baseline, repeat = paired()
    repeat["rows"][0]["record"]["evaluation"]["judgments"][0]["answer"] = "partial"
    repeat["rows"][0]["record"]["score"]["total"] = 50
    result = repeat_stability(baseline, repeat)
    assert result["judgments_checked"] == 1 and result["judgments_unchanged"] == 0
    assert len(result["changes"]) == len(result["score_drifts"]) == 1


@pytest.mark.parametrize("change", ["request", "failure", "criteria"])
def test_nonidentical_or_failed_requests_cannot_be_reported_as_repeat_stability(change):
    baseline, repeat = paired()
    record = repeat["rows"][0]["record"]
    if change == "request":
        record["request_fingerprint"] = "different-checklist-or-prompt"
    elif change == "failure":
        record["status"] = "failed"
    else:
        record["evaluation"]["judgments"] = []
    with pytest.raises(ValueError):
        repeat_stability(baseline, repeat)

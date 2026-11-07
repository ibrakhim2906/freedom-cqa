from copy import deepcopy

import pytest

from scripts.report_grounded_validation import resume_quota_rows, stability


def row(record):
    return {"case_id": "one", "record": record, "comparison": {"checks": []}}


def test_only_reconciled_provider_rejection_can_be_continued():
    rejected = row({"status": "failed", "api_error_code": "credit_balance_exhausted", "error": "api_http_429",
                    "usage": None, "ledger_call_id": 10, "request_fingerprint": "same"})
    completed = row({"status": "completed", "request_fingerprint": "same"})
    assert resume_quota_rows([rejected], [completed], {10}) == [completed]
    with pytest.raises(ValueError):
        resume_quota_rows([rejected], [completed], set())
    with pytest.raises(ValueError):
        resume_quota_rows([completed], [completed], {10})
    changed = deepcopy(completed)
    changed["record"]["request_fingerprint"] = "changed-prompt"
    with pytest.raises(ValueError):
        resume_quota_rows([rejected], [changed], {10})


def test_stability_records_unlabelled_judgment_and_total_drift():
    original = row({"status": "completed", "request_fingerprint": "same", "score": {"total": 100},
                    "evaluation": {"judgments": [{"criterion_id": "arbitrary", "status": "scored", "answer": "high"}]}})
    repeated = deepcopy(original)
    repeated["record"]["evaluation"]["judgments"][0]["answer"] = "low"
    repeated["record"]["score"]["total"] = 50
    result = stability([original], [repeated])
    assert result["judgments"] == 1 and result["unchanged"] == 0
    assert len(result["changes"]) == len(result["score_drifts"]) == 1

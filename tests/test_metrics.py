from cqa.datasets import authored_cases
from cqa.metrics import compare_case, summarize
from cqa.rubric import load_checklist


def test_failures_remain_in_end_to_end_denominator():
    case = authored_cases()[0]
    failure = {"status": "failed", "evaluation": None, "score": None, "error": "api_http_401"}
    comparison = compare_case(case, failure, load_checklist())
    report = summarize([{"case_id": case.id, "source": case.source, "language": "EN",
                         "channel": "agent chat", "record": failure, "comparison": comparison}])
    assert report["by_source"]["authored"]["end_to_end_agreement"] == 0
    assert report["by_source"]["authored"]["completed_only_agreement"] is None
    assert report["unknown_cost_attempts"] == 1
    assert report["by_source"]["authored"]["full_reference_score_cases"] == 0


def test_unlabelled_organizer_results_do_not_become_accuracy():
    report = summarize([{"case_id": "unlabelled", "source": "organizer", "language": "RU",
        "channel": "voice call", "record": {"status": "completed", "score": {"total": 95}},
        "comparison": {"checks": [], "total_absolute_error": None}}])
    assert report["by_source"]["organizer"]["end_to_end_agreement"] is None
    assert report["by_source"]["organizer"]["full_reference_score_cases"] == 0


def test_budget_skips_are_explicit_and_not_counted_as_live_attempts():
    case = authored_cases()[0]
    record = {"status": "skipped_budget", "score": None, "evaluation": None}
    report = summarize([{"case_id": case.id, "source": case.source, "language": "EN",
        "channel": "agent chat", "record": record,
        "comparison": compare_case(case, record, load_checklist())}])
    assert report["statuses"] == {"skipped_budget": 1}
    assert report["by_source"]["authored"]["attempted"] == 0
    assert report["by_source"]["authored"]["selected"] == 1

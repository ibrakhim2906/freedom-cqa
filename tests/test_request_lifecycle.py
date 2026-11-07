import pytest

from cqa.datasets import load_cases
from cqa.evaluator import schema_for
from cqa.models import Evaluation, RequestCoverage
from cqa.rubric import load_checklist
from cqa.scoring import validate_evaluation
from cqa.settings import ROOT


def candidate(case):
    return Evaluation(judgments=[{
        "criterion_id": e.criterion_id, "status": e.status, "answer": e.answer,
        "explanation": e.rationale, "evidence": [], "counterevidence": [],
        "checked_message_ids": [m.id for m in case.conversation.messages], "uncertainty": None,
    } for e in case.expectations], request_coverage=[], scope_notes=[])


def test_withdrawal_requires_customer_evidence_and_preserves_other_requests():
    case = next(c for c in load_cases(ROOT / "evals/review-v2.jsonl") if c.id == "review-en-withdrawn")
    result = candidate(case)
    result.request_coverage = [
        RequestCoverage(request="Download report", request_message_ids=["m1"], status="answered",
                        answer_message_ids=["m2"], explanation="Download steps provided."),
        RequestCoverage(request="Choose filename", request_message_ids=["m1"], status="withdrawn",
                        answer_message_ids=[], explanation="Customer cancels filename question.",
                        withdrawal_message_ids=["m3"]),
    ]
    validate_evaluation(result, case.conversation, load_checklist())
    result.request_coverage[1].withdrawal_message_ids = ["m2"]
    with pytest.raises(ValueError, match="customer messages"):
        validate_evaluation(result, case.conversation, load_checklist())
    result.request_coverage[1].withdrawal_message_ids = []
    with pytest.raises(ValueError, match="withdrawal evidence"):
        validate_evaluation(result, case.conversation, load_checklist())


def test_historical_request_records_remain_readable():
    old = {"request": "Download", "request_message_ids": ["m1"], "status": "answered",
           "answer_message_ids": ["m2"], "explanation": "Steps provided."}
    assert RequestCoverage.model_validate(old).withdrawal_message_ids == []


def test_new_strict_schema_requires_and_constrains_withdrawal_evidence():
    case = load_cases(ROOT / "evals/review-v2.jsonl")[0]
    definition = schema_for(case.conversation, load_checklist())["$defs"]["RequestCoverage"]
    assert set(definition["required"]) == set(definition["properties"])
    assert definition["properties"]["withdrawal_message_ids"]["items"]["enum"] == ["m1", "m3"]


def test_duplicate_case_ids_cannot_silently_corrupt_comparison(tmp_path):
    case = load_cases(ROOT / "evals/review-v2.jsonl")[0]
    path = tmp_path / "duplicates.jsonl"
    path.write_text((case.model_dump_json() + "\n") * 2, encoding="utf-8")
    with pytest.raises(ValueError, match="unique case IDs"):
        load_cases(path)

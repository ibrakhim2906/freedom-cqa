import json

from .models import Conversation, Expectation, Message, TestCase
from .settings import ROOT

REPRESENTATIVE_IDS = ["p1-ru-003", "p1-ru-009", "p1-ru-025", "p1-ru-029",
                      "p1-kz-003", "p1-kz-008", "p1-kz-013",
                      "p1-en-006", "p1-en-007", "p1-en-009",
                      "p4-ru-001", "p4-ru-002", "p4-ru-003", "p4-ru-004", "p4-ru-005"]

# Audit-derived candidate judgments, NOT organizer Ground Truth or independent human labels.
ORGANIZER_EXPECTATIONS = {
    "p1-ru-003": {"consultation": ("10", "Substantial commission question remains unanswered.")},
    "p1-ru-009": {"identity": ("no", "Account restriction disclosed before confirmed verification."),
                   "serious": ("yes", "Individual account information disclosed without verification.")},
    "p1-ru-025": {"contact": ("yes", "Operator greets and introduces herself in the first response."),
                   "consultation": (None, "Customer leaves without formulating the request."),
                   "closing": (None, "Customer departure prevents a closing.")},
    "p1-ru-029": {"serious": ("yes", "Operator directs an insulting remark at the customer."),
                   "empathy": ("no", "Response is rude despite a subsequently useful answer.")},
    "p1-kz-003": {"identity": ("yes", "System confirmation precedes case-specific handling.")},
    "p1-kz-008": {"contact": ("no", "First operator response does not introduce the operator.")},
    "p1-kz-013": {"serious": ("yes", "Private paid consultation is offered; refusal is irrelevant.")},
    "p1-en-006": {"identity": ("yes", "System identity confirmation precedes account-specific handling.")},
    "p1-en-007": {"consultation": ("10", "When withdrawal can be retried remains unanswered.")},
    "p1-en-009": {"closing": (None, "Explicit connection loss prevents a closing.")},
}


def authored_cases():
    path = ROOT / "evals/authored-v1.jsonl"
    return [TestCase.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def organizer_cases(*, representative=False):
    path = ROOT / "data/private/dev.json"
    if not path.exists():
        raise ValueError("Organizer DEV JSON is missing at data/private/dev.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["data"]["records"]
    cases = []
    for row in rows:
        if representative and row["conversation_id"] not in REPRESENTATIVE_IDS:
            continue
        expected = ORGANIZER_EXPECTATIONS.get(row["conversation_id"], {})
        cases.append(TestCase(id=row["conversation_id"], family="organizer-" + row["conversation_id"],
            source="organizer", label_provenance="ai_authored_provisional" if expected else "unlabelled",
            tags=[row["channel"]],
            conversation=Conversation(id=row["conversation_id"], channel=row["channel"], language=row["language"],
                messages=[Message(id=f"m{i}", **turn) for i, turn in enumerate(row["transcript"], 1)]),
            expectations=[Expectation(criterion_id=k, status="not_applicable" if v is None else "scored",
                answer=v, rationale=reason) for k, (v, reason) in expected.items()]))
    return cases


def load_suite(name):
    if name == "authored":
        return authored_cases()
    if name == "organizer":
        return organizer_cases()
    if name == "organizer-sample":
        return organizer_cases(representative=True)
    if name == "combined":
        return authored_cases() + organizer_cases(representative=True)
    raise ValueError("Unknown suite")

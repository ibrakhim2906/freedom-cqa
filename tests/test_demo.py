"""Prepared demo tests use isolated databases, an empty key and a forbidden evaluator."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app import create_app
from backend.demo import DEMO_VERSION, prepared_demo
from backend.storage import Appeal, Batch, Job
from cqa.models import Evaluation
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score
from cqa.settings import ROOT, Settings


def forbidden_factory():
    return Mock(side_effect=AssertionError("The prepared demo must never create an evaluator"))


def open_demo(client):
    response = client.post("/api/demo/open", json={})
    assert response.status_code == 200, response.text
    return response.json()


def stored_counts(app):
    with app.state.store.session() as session:
        return {
            "jobs": session.scalar(select(func.count()).select_from(Job)),
            "batches": session.scalar(select(func.count()).select_from(Batch)),
            "appeals": session.scalar(select(func.count()).select_from(Appeal)),
            "active": session.scalar(select(func.count()).select_from(Job).where(
                Job.status.in_(["queued", "running"]))),
        }


@pytest.fixture
def demo_client(tmp_path):
    factory = forbidden_factory()
    settings = Settings(api_key="", ledger_path=tmp_path / "usage.sqlite3")
    app = create_app(settings=settings, database_path=tmp_path / "app.sqlite3", evaluator_factory=factory)
    with TestClient(app) as client:
        yield client, app
    factory.assert_not_called()


def test_prepared_demo_uses_valid_quotes_and_calculates_875_from_70_of_80():
    checklist = load_checklist(ROOT / "checklists/freedom-reviewed-017.json")
    conversation, record = prepared_demo(checklist)
    evaluation = Evaluation.model_validate(record["evaluation"])
    score = calculate_score(evaluation, checklist)
    assert record["score"] == score
    assert score["earned_points"] == 70
    assert score["applicable_weight"] == 80
    assert score["total"] == 87.5
    assert score["provisional"] is False
    judgments = {judgment.criterion_id: judgment for judgment in evaluation.judgments}
    assert judgments["identity"].status == "not_applicable"
    assert judgments["identity"].answer is None
    assert judgments["consultation"].answer == "10"
    assert judgments["management"].answer == "10"
    assert judgments["serious"].answer == "no"
    messages = {message.id: message.text for message in conversation.messages}
    references = {reference.id: reference.text for reference in conversation.references}
    assert len(messages) == 9
    for judgment in evaluation.judgments:
        assert judgment.evidence
        assert set(judgment.checked_message_ids) <= messages.keys()
        for evidence in [*judgment.evidence, *judgment.counterevidence]:
            assert evidence.quote and evidence.quote in messages[evidence.message_id]
    for deduction in evaluation.deductions:
        for evidence in deduction.evidence:
            assert evidence.quote and evidence.quote in messages[evidence.message_id]
    quoted_references = record["assessment"]["criteria"]["consultation"]["reference_evidence"]
    assert quoted_references
    for evidence in quoted_references:
        assert evidence["quote"] and evidence["quote"] in references[evidence["reference_id"]]


def test_open_demo_is_free_labelled_idempotent_and_survives_restart(tmp_path):
    factory = forbidden_factory()
    settings = Settings(api_key="", ledger_path=tmp_path / "usage.sqlite3")
    database = tmp_path / "app.sqlite3"
    app = create_app(settings=settings, database_path=database, evaluator_factory=factory)
    with TestClient(app) as client:
        before = client.get("/api/config").json()
        assert before["api_key_configured"] is False
        opened = open_demo(client)
        assert opened["reused"] is False
        again = open_demo(client)
        assert again == {**opened, "reused": True}
        job = client.get(f"/api/jobs/{opened['job_id']}").json()
        assert job["status"] == "completed"
        assert job["is_demo"] is True
        assert job["effective"]["source"] == "prepared_demo"
        assert job["effective"]["score"]["total"] == 87.5
        assert job["conversation"]["metadata"]["prepared_demo"] is True
        assert job["runtime"] == {"strategy": "prepared_demo", "model": "none", "paid": False}
        record = job["record"]
        assert record["demo"]["prepared"] is True
        assert record["demo"]["version"] == DEMO_VERSION
        assert record["model"] == "prepared-demo"
        assert record["response_id"] is None
        assert record["usage"] is None
        assert record["attempt_count"] == 0
        assert record["attempt_records"] == []
        assert record["billing_state"] == "not_submitted"
        assert job["started_at"] is None
        assert job["appeals"] == []
        rows = client.get("/api/jobs").json()
        assert len(rows) == 1 and rows[0]["is_demo"] is True
        conversations = client.get("/api/conversations").json()
        assert len(conversations) == 1
        summary = conversations[0]["latest_assessment"]
        assert summary["id"] == opened["job_id"]
        assert summary["is_demo"] is True
        assert summary["source"] == "prepared_demo"
        exported = client.get(f"/api/jobs/{opened['job_id']}/export").json()
        assert exported["is_demo"] is True
        assert exported["effective"]["source"] == "prepared_demo"
        assert exported["record"] == record
        batch = client.get(f"/api/batches/{job['batch_id']}").json()
        assert batch["budget_usd"] == batch["committed_usd"] == 0
        assert stored_counts(app) == {"jobs": 1, "batches": 1, "appeals": 0, "active": 0}
        assert client.get("/api/config").json() == before
        factory.assert_not_called()

    restarted = create_app(settings=settings, database_path=database, evaluator_factory=factory)
    with TestClient(restarted) as client:
        persisted = client.get(f"/api/jobs/{opened['job_id']}")
        assert persisted.status_code == 200
        assert persisted.json()["record"] == record
        assert persisted.json()["effective"]["source"] == "prepared_demo"
        assert open_demo(client) == {**opened, "reused": True}
        assert stored_counts(restarted) == {"jobs": 1, "batches": 1, "appeals": 0, "active": 0}
        assert client.get("/api/config").json() == before
    factory.assert_not_called()


@pytest.mark.parametrize("force", [False, True])
def test_actual_review_cannot_reuse_demo_as_model_cache_without_a_key(demo_client, force):
    client, app = demo_client
    opened = open_demo(client)
    before = client.get("/api/config").json()["ledger"]
    response = client.post("/api/evaluations", json={
        "conversation_ids": [opened["conversation_id"]], "checklist_id": opened["checklist_id"],
        "request_id": f"real-review-{force}", "budget_usd": 1, "force": force,
    })
    assert response.status_code == 422, response.text
    assert "OPENAI_API_KEY" in response.json()["detail"]
    assert stored_counts(app) == {"jobs": 1, "batches": 1, "appeals": 0, "active": 0}
    assert client.get("/api/config").json()["ledger"] == before
    unchanged = client.get(f"/api/jobs/{opened['job_id']}").json()
    assert unchanged["effective"]["source"] == "prepared_demo"
    assert unchanged["record"]["attempt_count"] == 0


def test_prepared_demo_rejects_appeals_without_changing_the_saved_result(demo_client):
    client, app = demo_client
    opened = open_demo(client)
    path = f"/api/jobs/{opened['job_id']}"
    before = client.get(path).json()
    ledger = client.get("/api/config").json()["ledger"]
    response = client.post(f"{path}/appeals", json={
        "criterion_id": "consultation", "author": "Проверяющий", "reason": "Проверка учебного разбора",
        "message_ids": ["m6"],
    })
    assert response.status_code == 409, response.text
    assert "Учебный разбор" in response.json()["detail"]
    assert client.get(path).json() == before
    assert stored_counts(app) == {"jobs": 1, "batches": 1, "appeals": 0, "active": 0}
    assert client.get("/api/config").json()["ledger"] == ledger

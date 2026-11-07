"""Isolated API tests. Synthetic evaluators are injected here only, never exposed by runtime configuration."""

import copy
import json
import time
from typing import ClassVar
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.storage import Job
from cqa.evaluator import Evaluator
from cqa.ledger import BudgetExceeded, Ledger
from cqa.models import Evaluation, Judgment
from cqa.scoring import calculate_score
from cqa.settings import Settings

CONVERSATION = {"id": "fresh-ru", "channel": "agent chat", "language": "RU", "messages": [
    {"id": "customer-1", "timestamp": "00:01", "speaker": "client", "text": "Как получить отчёт?"},
    {"id": "agent-1", "timestamp": "00:02", "speaker": "operator", "text": "Здравствуйте. Откройте раздел Отчёты."}]}
CHECKLIST = {"id": "unseen-checklist", "version": "1", "title": "A new checklist", "instructions": [], "criteria": [
    {"id": "new-clarity", "title": "Clarity", "instruction": "Assess clear actionable wording.", "kind": "binary",
     "weight": 10, "levels": [{"value": "complete", "fraction": 1, "description": "Clear"},
                               {"value": "missing", "fraction": 0, "description": "Unclear"}]},
    {"id": "new-contact", "title": "Contact", "instruction": "Assess a greeting.", "kind": "binary", "weight": 5,
     "levels": [{"value": "present", "fraction": 1, "description": "Greeting"},
                {"value": "absent", "fraction": 0, "description": "None"}]}]}


class TestOnlyEvaluator:
    __test__ = False
    calls: ClassVar[list] = []

    def __init__(self, settings, ledger, ceiling):
        self.ledger, self.ceiling = ledger, ceiling

    async def close(self):
        pass

    async def evaluate(self, conversation, checklist):
        type(self).calls.append((conversation.model_dump(), checklist.model_dump()))
        call = self.ledger.reserve("test-only", .01, self.ceiling)
        self.ledger.finish(call, "completed", cost=.001, input_tokens=1, output_tokens=1)
        result = Evaluation(judgments=[Judgment(criterion_id=c.id, status="scored",
            answer=(min if i == 0 else max)(c.levels, key=lambda l: l.fraction).value,
            explanation="TEST ONLY: source-specific explanation", evidence=[{"message_id": conversation.messages[-1].id,
            "quote": conversation.messages[-1].text}], counterevidence=[],
            checked_message_ids=[m.id for m in conversation.messages], uncertainty=None)
            for i, c in enumerate(checklist.criteria)], request_coverage=[], scope_notes=["Isolated test fixture"])
        return {"status": "completed", "evaluation": result.model_dump(), "score": calculate_score(result, checklist),
                "model": "TEST-ONLY", "response_id": "test-only", "error": None,
                "usage": {"estimated_cost_usd": .001, "input_tokens": 1, "output_tokens": 1},
                "attempt_count": 1, "latency_seconds": .01}


class FailingTestEvaluator(TestOnlyEvaluator):
    async def evaluate(self, *_):
        return {"status": "failed", "evaluation": None, "score": None, "error": "test_provider_failure", "usage": None}


@pytest.fixture
def setup(tmp_path):
    TestOnlyEvaluator.calls = []
    settings = Settings(api_key="fictional-test-key", ledger_path=tmp_path / "usage.sqlite3", max_spend=1)
    path = tmp_path / "app.sqlite3"
    app = create_app(settings=settings, database_path=path, evaluator_factory=TestOnlyEvaluator)
    with TestClient(app) as client:
        yield client, app, settings, path


def import_one(client, value=None):
    response = client.post("/api/conversations/import", json={"content": json.dumps(value or CONVERSATION)})
    assert response.status_code == 200, response.text
    return response.json()["conversations"][0]["id"]


def save_checklist(client, value=None):
    response = client.post("/api/checklists", json=value or CHECKLIST)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def run(client, conversation_id, checklist_id, key="request-1", force=False):
    response = client.post("/api/evaluations", json={"conversation_ids": [conversation_id], "checklist_id": checklist_id,
        "request_id": key, "budget_usd": .1, "force": force})
    assert response.status_code == 202, response.text
    return response.json()


def wait_for_job(client, job_id):
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(.02)
    pytest.fail("Test worker did not finish")


def test_historical_result_context_is_identified_as_reconstructed_without_rewriting_record(setup):
    client, app, _, _ = setup
    cid, checklist_id = import_one(client), save_checklist(client)
    result = run(client, cid, checklist_id)
    job = wait_for_job(client, result["job_ids"][0])
    assert job["evidence_context_origin"] == "captured_with_request"
    with app.state.store.session.begin() as session:
        stored = session.get(Job, job["id"])
        legacy_record = {k: v for k, v in stored.record.items()
                         if k not in {"evidence_context", "assessment_context"}}
        stored.record = legacy_record
    inspected = client.get(f"/api/jobs/{job['id']}").json()
    assert inspected["evidence_context_origin"] == "reconstructed_for_inspection"
    assert inspected["record"] == legacy_record
    exported = client.get(f"/api/jobs/{job['id']}/export").json()
    assert exported["evidence_context_origin"] == "reconstructed_for_inspection"
    assert exported["record"] == legacy_record


def test_import_is_atomic_idempotent_and_preserves_revisions(setup):
    client, _, _, _ = setup
    first = import_one(client)
    assert import_one(client) == first
    changed = copy.deepcopy(CONVERSATION)
    changed["messages"][-1]["text"] = "A different reply"
    second = import_one(client, changed)
    assert first != second
    assert client.get(f"/api/conversations/{first}").json()["content"]["messages"][-1]["text"] == CONVERSATION["messages"][-1]["text"]
    response = client.post("/api/conversations/import", json={"content": json.dumps([changed, {"id": "invalid"}])})
    assert response.status_code == 422
    assert len(client.get("/api/conversations").json()) == 2
    assert "fictional-test-key" not in client.get("/api/config").text


def test_organizer_and_diagnostic_import_strip_labels_and_preserve_sources(setup):
    client, _, _, _ = setup
    organizer = {"data": {"records": [{"conversation_id": "org", "channel": "voice call", "language": "KZ",
        "audio_url": "https://example.org/recording", "transcript": [{k: v for k, v in m.items() if k != "id"} for m in CONVERSATION["messages"]]}]}}
    cid = import_one(client, organizer)
    imported = client.get(f"/api/conversations/{cid}").json()
    assert imported["content"]["messages"][0]["id"] == "m1"
    assert imported["metadata"]["recording_url"] == "https://example.org/recording"
    diagnostic = {"conversation": CONVERSATION, "expectations": [{"secret": "DO-NOT-INFER"}]}
    did = import_one(client, diagnostic)
    assert "DO-NOT-INFER" not in client.get(f"/api/conversations/{did}").text


def test_checklist_versions_cache_and_changed_inputs_never_reuse_wrong_result(setup):
    client, _, _, _ = setup
    cid, checklist_id = import_one(client), save_checklist(client)
    first = run(client, cid, checklist_id)
    original = wait_for_job(client, first["job_ids"][0])
    assert original["status"] == "completed" and original["effective"]["score"]["total"] == 33.33
    cached = run(client, cid, checklist_id, "cached")
    assert cached["reused"] == first["job_ids"]
    assert run(client, cid, checklist_id)["idempotent"]
    assert len(TestOnlyEvaluator.calls) == 1
    edited = copy.deepcopy(CHECKLIST)
    edited["criteria"][0]["instruction"] = "Now assess a different meaning."
    assert client.post("/api/checklists", json=edited).status_code == 422
    edited["version"] = "2"
    revised_id = save_checklist(client, edited)
    fresh = wait_for_job(client, run(client, cid, revised_id, "new-version")["job_ids"][0])
    assert fresh["checklist"]["content"]["version"] == "2"
    assert original["checklist"]["content"]["version"] == "1"
    assert TestOnlyEvaluator.calls[-1][1]["criteria"][0]["instruction"] == edited["criteria"][0]["instruction"]
    assert len(TestOnlyEvaluator.calls) == 2
    assert client.get(f"/api/jobs/{original['id']}/export").json()["record"] == original["record"]


def test_appeal_acceptance_recalculates_without_modifying_ai_and_conflicts_are_rejected(setup):
    client, _, _, _ = setup
    cid, checklist_id = import_one(client), save_checklist(client)
    job = wait_for_job(client, run(client, cid, checklist_id)["job_ids"][0])
    original_record = copy.deepcopy(job["record"])
    appeal = client.post(f"/api/jobs/{job['id']}/appeals", json={"criterion_id": "new-clarity", "author": "Operator",
        "reason": "The reply identifies a concrete source section", "message_ids": ["agent-1"]})
    assert appeal.status_code == 201
    bad = dict(job["effective"]["judgments"][0]) | {"answer": "illegal-tier"}
    resolution = {"decision": "accept", "reviewer": "QA reviewer", "rationale": "The cited reply is actionable",
                  "expected_revision": 0, "judgment": bad}
    endpoint = f"/api/appeals/{appeal.json()['id']}/resolve"
    assert client.post(endpoint, json=resolution).status_code == 422
    valid = dict(job["effective"]["judgments"][0]) | {"answer": "complete", "explanation": "Human reviewed the actionable route"}
    resolution["judgment"] = valid
    assert client.post(endpoint, json=resolution).status_code == 200
    assert client.post(endpoint, json=resolution).status_code == 409
    updated = client.get(f"/api/jobs/{job['id']}").json()
    assert updated["effective"]["score"]["total"] == 100
    assert updated["effective"]["source"] == "human_review" and updated["review_revision"] == 1
    assert updated["record"] == original_record
    assert len(TestOnlyEvaluator.calls) == 1
    assert updated["appeals"][0]["resolution"]["before"]["answer"] == "missing"


def test_failure_is_visible_and_explicit_retry_is_a_new_attempt(tmp_path):
    settings = Settings(api_key="test-only", ledger_path=tmp_path / "usage.sqlite3", max_spend=1)
    app = create_app(settings=settings, database_path=tmp_path / "app.sqlite3", evaluator_factory=FailingTestEvaluator)
    with TestClient(app) as client:
        cid, checklist_id = import_one(client), save_checklist(client)
        failed = wait_for_job(client, run(client, cid, checklist_id)["job_ids"][0])
        assert failed["status"] == "failed" and failed["effective"] is None
        assert failed["record"]["evaluation"] is None and failed["record"]["score"] is None
        retried = client.post(f"/api/jobs/{failed['id']}/retry", json={"request_id": "retry", "budget_usd": .1}).json()
        second = wait_for_job(client, retried["job_ids"][0])
        assert second["id"] != failed["id"] and second["retry_of"] == failed["id"]
        assert client.get(f"/api/jobs/{failed['id']}").json()["status"] == "failed"


def test_restart_preserves_results_and_marks_inflight_calls_interrupted(tmp_path):
    settings = Settings(api_key="test-only", ledger_path=tmp_path / "usage.sqlite3", max_spend=1)
    path = tmp_path / "app.sqlite3"
    app = create_app(settings=settings, database_path=path, evaluator_factory=TestOnlyEvaluator)
    with TestClient(app) as client:
        cid, checklist_id = import_one(client), save_checklist(client)
        job = wait_for_job(client, run(client, cid, checklist_id)["job_ids"][0])
        with app.state.store.session.begin() as session:
            saved = session.get(Job, job["id"])
            saved.status = "running"
        grouped = Ledger(settings.ledger_path, 1, budget_group=job["batch_id"], group_limit=.5)
        held = grouped.hold("test", .2, 1)
        grouped.reserve("test", .05, 1, hold_id=held)  # Crash before usage was received.
        other = Ledger(settings.ledger_path, 1)
        cli_hold = other.hold("test", .1, 1)  # An unrelated CLI run must stay protected.
    reopened = create_app(settings=settings, database_path=path, evaluator_factory=TestOnlyEvaluator)
    with TestClient(reopened) as client:
        assert client.get(f"/api/conversations/{cid}").status_code == 200
        interrupted = client.get(f"/api/jobs/{job['id']}").json()
        assert interrupted["status"] == "interrupted" and interrupted["effective"] is None
        assert interrupted["record"]["billing_state"] == "unknown"
        assert grouped.group_committed(job["batch_id"]) == pytest.approx(.051)
        assert other.summary()["protected_allowance_usd"] == .1
        other.release(cli_hold)


def test_batch_budget_is_independent_from_other_batches_and_global_cap_is_still_enforced(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    a, b = Ledger(path, .15, budget_group="a", group_limit=.1), Ledger(path, .15, budget_group="b", group_limit=.1)
    first = a.reserve("test", .08, .15)
    a.finish(first, "completed", cost=.01)
    b.reserve("test", .08, .15)
    with pytest.raises(BudgetExceeded):
        a.reserve("test", .08, .15)  # global cap, not another batch consuming a's group allowance
    assert a.group_committed("a") == .01 and b.group_committed("b") == .08
    with pytest.raises(BudgetExceeded):
        b.reserve("test", .03, .15)


def test_real_evaluator_budget_preflight_exposes_actionable_details_without_a_paid_call(tmp_path):
    evaluators = []
    def factory(settings, ledger, ceiling):
        evaluator = Evaluator(settings, ledger, ceiling)
        evaluator.client.responses.create = AsyncMock()
        evaluators.append(evaluator)
        return evaluator
    settings = Settings(api_key="test-only", ledger_path=tmp_path / "usage.sqlite3", max_spend=1)
    app = create_app(settings=settings, database_path=tmp_path / "app.sqlite3", evaluator_factory=factory)
    with TestClient(app) as client:
        cid, checklist_id = import_one(client), save_checklist(client)
        queued = client.post("/api/evaluations", json={"conversation_ids": [cid], "checklist_id": checklist_id,
            "request_id": "preflight", "budget_usd": .000001})
        assert queued.status_code == 202
        job = wait_for_job(client, queued.json()["job_ids"][0])
        assert job["status"] == "failed" and job["record"]["attempt_count"] == 0
        assert "bounded repair" in job["record"]["error_detail"]
        assert job["record"]["budget_required_usd"] > job["record"]["budget_available_usd"]
        assert job["record"]["billing_state"] == "not_submitted"
        evaluators[0].client.responses.create.assert_not_called()
        assert app.state.workflow.ledger.committed() == 0


@pytest.mark.parametrize("payload", [{"data": None}, {"conversation": "invalid"}, {"data": {"records": [None]}},
                                    {"conversation_id": "bad", "transcript": [None]}])
def test_malformed_import_is_a_validation_error_not_a_server_crash(setup, payload):
    client, _, _, _ = setup
    response = client.post("/api/conversations/import", json={"content": json.dumps(payload)})
    assert response.status_code == 422
    assert client.get("/api/conversations").json() == []


def test_empty_criterion_instructions_cannot_be_saved(setup):
    client, _, _, _ = setup
    invalid = copy.deepcopy(CHECKLIST)
    invalid["criteria"][0]["instruction"] = "   "
    assert client.post("/api/checklists", json=invalid).status_code == 422


def test_stale_review_on_another_open_appeal_cannot_overwrite_a_newer_decision(setup):
    client, _, _, _ = setup
    cid, checklist_id = import_one(client), save_checklist(client)
    job = wait_for_job(client, run(client, cid, checklist_id)["job_ids"][0])
    appeals = [client.post(f"/api/jobs/{job['id']}/appeals", json={"criterion_id": criterion, "author": "Operator",
        "reason": "Review this judgment", "message_ids": ["agent-1"]}).json() for criterion in ["new-clarity", "new-contact"]]
    original_score = job["effective"]["score"]
    resolution = {"decision": "reject", "reviewer": "Reviewer", "rationale": "The original source supports the judgment",
                  "expected_revision": 0}
    assert client.post(f"/api/appeals/{appeals[0]['id']}/resolve", json=resolution).status_code == 200
    assert client.post(f"/api/appeals/{appeals[1]['id']}/resolve", json=resolution).status_code == 409
    resolution["expected_revision"] = 1
    assert client.post(f"/api/appeals/{appeals[1]['id']}/resolve", json=resolution).status_code == 200
    saved = client.get(f"/api/jobs/{job['id']}").json()
    assert saved["review_revision"] == 2 and saved["effective"]["score"] == original_score
    assert saved["record"] == job["record"]


def test_saved_evaluation_still_loads_without_an_api_key(tmp_path):
    settings = Settings(api_key="test-only", ledger_path=tmp_path / "usage.sqlite3", max_spend=1)
    path = tmp_path / "app.sqlite3"
    with TestClient(create_app(settings=settings, database_path=path, evaluator_factory=TestOnlyEvaluator)) as client:
        cid, checklist_id = import_one(client), save_checklist(client)
        job = wait_for_job(client, run(client, cid, checklist_id)["job_ids"][0])
    from dataclasses import replace
    with TestClient(create_app(settings=replace(settings, api_key=""), database_path=path)) as client:
        assert not client.get("/api/config").json()["api_key_configured"]
        cached = run(client, cid, checklist_id, key="without-key")
        assert cached["reused"] == [job["id"]]
        failed = client.post(f"/api/jobs/{job['id']}/retry", json={"request_id": "requires-key", "budget_usd": .1})
        assert failed.status_code == 422 and "OPENAI_API_KEY" in failed.json()["detail"]


def test_foreign_origin_cannot_mutate_local_workspace(setup):
    client, _, _, _ = setup
    response = client.post("/api/conversations/import", json={"content": json.dumps(CONVERSATION)},
                           headers={"Origin": "https://unrelated.example"})
    assert response.status_code == 403

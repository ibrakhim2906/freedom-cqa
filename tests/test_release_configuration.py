"""Offline release checks: every entry point uses one default; saved choices stay exact."""

import json
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.storage import digest
from cqa.models import Evaluation, Judgment
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score
from cqa.settings import Settings
from scripts import prepare_control_run as control

ROOT = Path(__file__).resolve().parents[1]


def settings_for(tmp_path):
    return Settings(api_key="isolated-release-test", ledger_path=tmp_path / "usage.sqlite3", max_spend=1)


def reject_evaluation(*_):
    pytest.fail("This release inspection must not instantiate an evaluator")


def test_api_and_prepared_example_use_the_exact_cli_default(tmp_path):
    expected = load_checklist().model_dump()
    expected_hash = digest({"content": expected, "metadata": {}})
    app = create_app(settings=settings_for(tmp_path), database_path=tmp_path / "app.sqlite3",
                     evaluator_factory=reject_evaluation)
    with TestClient(app) as client:
        advertised = client.get("/api/config").json()["default_checklist"]
        assert advertised == {"id": expected["id"], "version": expected["version"]}
        matches = [row for row in client.get("/api/checklists").json()
                   if row["external_id"] == advertised["id"] and row["version"] == advertised["version"]]
        assert len(matches) == 1
        assert matches[0]["content"] == expected
        assert matches[0]["content_hash"] == expected_hash
        response = client.post("/api/demo/open")
        assert response.status_code == 200, response.text
        job = client.get(f"/api/jobs/{response.json()['job_id']}").json()
        assert job["checklist"]["content"] == expected
        assert job["checklist"]["content_hash"] == expected_hash
        assert job["record"]["demo"]["prepared"] is True
        assert job["runtime"]["strategy"] == "prepared_demo"


def test_explicit_saved_choice_and_job_snapshot_survive_default_reload(tmp_path):
    calls = []

    class IsolatedEvaluator:
        def __init__(self, *_):
            pass

        async def close(self):
            pass

        async def evaluate(self, conversation, checklist):
            calls.append(checklist.model_dump())
            result = Evaluation(judgments=[Judgment(
                criterion_id=criterion.id, status="scored", answer=criterion.levels[-1].value,
                explanation="Isolated plumbing fixture; not a model or quality assessment.",
                evidence=[], counterevidence=[], checked_message_ids=[conversation.messages[0].id],
                uncertainty=None) for criterion in checklist.criteria], request_coverage=[], scope_notes=[])
            return {"status": "completed", "evaluation": result.model_dump(),
                    "score": calculate_score(result, checklist), "model": "TEST-ONLY",
                    "usage": None, "attempt_count": 0, "billing_state": "not_submitted", "error": None}

    default = load_checklist()
    alternatives = [load_checklist(path) for path in (
        ROOT / "checklists/freedom-reviewed-016.json", ROOT / "checklists/freedom-reviewed-017.json")]
    selected = next(checklist for checklist in alternatives if checklist.version != default.version)
    settings = settings_for(tmp_path)
    database = tmp_path / "app.sqlite3"
    app = create_app(settings=settings, database_path=database, evaluator_factory=IsolatedEvaluator)
    with TestClient(app) as client:
        saved = client.post("/api/checklists", json=selected.model_dump())
        assert saved.status_code == 200, saved.text
        selected_row = saved.json()
        imported = client.post("/api/conversations/import", json={"content": json.dumps({
            "id": "release-snapshot-only", "channel": "agent chat", "language": "EN",
            "messages": [{"id": "m1", "speaker": "client", "timestamp": "00:01", "text": "Hello."}]})})
        assert imported.status_code == 200, imported.text
        response = client.post("/api/evaluations", json={
            "conversation_ids": [imported.json()["conversations"][0]["id"]],
            "checklist_id": selected_row["id"], "request_id": "release-snapshot-only", "budget_usd": .1})
        assert response.status_code == 202, response.text
        job_id = response.json()["job_ids"][0]
        for _ in range(100):
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["status"] not in {"queued", "running"}:
                break
            time.sleep(.02)
        assert job["status"] == "completed", job
        assert calls == [selected.model_dump()]
        assert job["checklist_id"] == selected_row["id"]
        assert job["checklist"]["content"] == selected.model_dump()
        assert job["checklist"]["content_hash"] == selected_row["content_hash"]
        assert job["runtime"]["model"] == settings.model
        assert job["runtime"]["strategy"] == settings.strategy
        original_export = client.get(f"/api/jobs/{job_id}/export").json()
    # A release-default change/reload must not relabel existing results or invoke the model.
    reopened = create_app(settings=settings, database_path=database, evaluator_factory=reject_evaluation)
    with TestClient(reopened) as client:
        assert client.get(f"/api/jobs/{job_id}/export").json() == original_export
        current = {row["id"]: row for row in client.get("/api/checklists").json()}
        assert current[selected_row["id"]]["content"] == selected.model_dump()
        assert current[selected_row["id"]]["content_hash"] == selected_row["content_hash"]


def test_control_manifest_and_embedded_checklists_match_the_cli_default(tmp_path, monkeypatch):
    for directory in ("checklists", "config"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    reference = Path("references/freedom-global-products-20261107.json")
    (tmp_path / reference).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / reference, tmp_path / reference)
    monkeypatch.setattr(control, "ROOT", tmp_path)
    source = tmp_path / "rehearsal-source.json"
    source.write_text(json.dumps({"isSuccess": True, "data": {"dataset_group_id": "DEV", "records": [
        {"conversation_id": f"release-only-{index}", "channel": "agent chat", "language": "EN",
         "transcript": [{"timestamp": "00:01", "speaker": "client", "text": "Hello."}]}
        for index in range(10)]}}), encoding="utf-8")
    output = tmp_path / "artifacts/release-check/input.jsonl"
    result = control.prepare(source, output, split="rehearsal")
    assert result["paid_api_calls"] == 0 and result["results_created"] is False
    manifest = json.loads(output.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    expected = load_checklist().model_dump()
    assert manifest["checklist"]["id"] == expected["id"]
    assert manifest["checklist"]["version"] == expected["version"]
    assert load_checklist(tmp_path / manifest["checklist"]["path"]).model_dump() == expected
    cases = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(cases) == 10
    assert all(case["checklist_override"] == expected and not case["expectations"] for case in cases)

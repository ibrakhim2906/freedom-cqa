"""Preset imports must preserve source/history and cannot start model calls."""
import copy
import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.importing import parse_import
from cqa.grounding import evidence_context_for, select_reference_context
from cqa.settings import ROOT, Settings
from scripts.prepare_control_run import AS_OF, RATIONALE, SCOPE
from tests.test_failed_import_envelopes import snapshot


def source(group="FBroker"):
    return {"isSuccess": True, "data": {"dataset_group_id": group, "records": [
        {"conversation_id": "fresh-preset-" + str(i), "channel": "agent chat", "language": lang,
         "transcript": [{"timestamp": "00:01", "speaker": "client", "text": text},
                        {"timestamp": "00:02", "speaker": "operator", "text": "Hello."}]}
        for i, (lang, text) in enumerate([("RU", "Тариф?"), ("KZ", "Тариф?"), ("EN", "Pricing?")])]}}


@pytest.fixture
def isolated(tmp_path):
    factory = Mock(side_effect=AssertionError("Preset import must not instantiate an evaluator"))
    app = create_app(settings=Settings(api_key="", ledger_path=tmp_path / "usage.sqlite3"),
                     database_path=tmp_path / "app.sqlite3", evaluator_factory=factory)
    with TestClient(app) as client:
        yield client, app
    factory.assert_not_called()


def test_preset_matches_control_preparation_preserves_history_and_is_idempotent(isolated):
    client, app = isolated
    demo = client.post("/api/demo/open", json={}).json()
    original_export = client.get(f"/api/jobs/{demo['job_id']}/export").json()
    content = json.dumps(source(), ensure_ascii=False)
    ordinary = client.post("/api/conversations/import", json={"content": content}).json()
    before = snapshot(app)
    ledger = client.get("/api/config").json()["ledger"]
    response = client.post("/api/conversations/import", json={"content": content, "reference_preset": "fbroker"})
    assert response.status_code == 200, response.text
    rows = response.json()["conversations"]
    assert response.json()["created"] == 3
    for row, (conversation, _) in zip(rows, parse_import(content), strict=True):
        stored = client.get(f"/api/conversations/{row['id']}").json()["content"]
        expected = select_reference_context(conversation, ROOT / "references/freedom-global-products-20261107.json",
            SCOPE, mode="snapshot_review", as_of=AS_OF, rationale=RATIONALE)
        assert stored == expected.model_dump()
        assert stored["messages"] == conversation.model_dump()["messages"]
        assert stored["occurred_on"] == conversation.occurred_on
        assert sum(r["usable"] for r in evidence_context_for(expected)["references"]) == 9
    repeated = client.post("/api/conversations/import", json={"content": content, "reference_preset": "fbroker"}).json()
    assert repeated["created"] == 0 and repeated["reused"] == 3
    assert [r["id"] for r in repeated["conversations"]] == [r["id"] for r in rows]
    for row in ordinary["conversations"]:
        assert client.get(f"/api/conversations/{row['id']}").json()["content"]["references"] == []
    assert client.get(f"/api/jobs/{demo['job_id']}/export").json() == original_export
    after = snapshot(app)
    assert all(after[table] == before[table] for table in ("jobs", "batches", "appeals"))
    assert client.get("/api/config").json()["ledger"] == ledger


@pytest.mark.parametrize("kind", ["Swap", "DEV", "unknown", "missing", "outer_conflict", "failed", "scope_conflict"])
def test_invalid_or_conflicting_preset_is_atomic(isolated, kind):
    client, app = isolated
    payload = source(kind)
    if kind == "missing":
        del payload["data"]["dataset_group_id"]
    elif kind == "outer_conflict":
        payload["data"]["dataset_group_id"] = "FBroker"
        payload["dataset_group_id"] = "Swap"
    elif kind == "failed":
        payload["data"]["dataset_group_id"] = "FBroker"
        payload["isSuccess"] = False
    elif kind == "scope_conflict":
        payload["data"]["dataset_group_id"] = "FBroker"
        payload["data"]["records"][-1]["knowledge_scope"] = "other-product"
    before = copy.deepcopy(snapshot(app))
    response = client.post("/api/conversations/import", json={
        "content": json.dumps(payload), "reference_preset": "fbroker"})
    assert response.status_code == 422
    assert snapshot(app) == before


def test_swap_normal_upload_retains_original_no_fbroker_context(isolated):
    client, _ = isolated
    response = client.post("/api/conversations/import", json={"content": json.dumps(source("Swap"))})
    assert response.status_code == 200
    for row in response.json()["conversations"]:
        content = client.get(f"/api/conversations/{row['id']}").json()["content"]
        assert not content["references"] and content["reference_context"] is None

"""Explicit failed responses cannot import cached records or modify prior results."""

import copy
import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import create_app
from backend.importing import parse_import
from backend.storage import Appeal, Batch, Document, Job
from cqa.settings import Settings

ROW = {"id": "cached-source", "channel": "agent chat", "language": "EN", "messages": [
    {"id": "m1", "timestamp": "", "speaker": "client", "text": "PRIVATE-CACHED-TEXT"}]}


def envelope(shape, status=False):
    if shape == "outer":
        return {"isSuccess": status, "data": {"records": [ROW]}}
    if shape == "inner":
        return {"isSuccess": True, "data": {"isSuccess": status, "records": [ROW]}}
    return {"isSuccess": status, "records": [ROW]}


def snapshot(app):
    with app.state.store.session() as session:
        return copy.deepcopy({model.__tablename__: [dict(row) for row in session.execute(
            select(model.__table__).order_by(model.id)).mappings()]
            for model in (Document, Job, Batch, Appeal)})


@pytest.mark.parametrize("shape", ["outer", "inner", "records"])
def test_failed_import_is_atomic_and_preserves_existing_results(tmp_path, shape):
    factory = Mock(side_effect=AssertionError("No evaluator may be created"))
    app = create_app(settings=Settings(api_key="", ledger_path=tmp_path / "ledger.sqlite3"),
        database_path=tmp_path / "app.sqlite3", evaluator_factory=factory)
    with TestClient(app) as client:
        assert client.post("/api/demo/open", json={}).status_code == 200
        before = snapshot(app)
        assert before["jobs"]  # An existing completed result must remain unchanged.
        response = client.post("/api/conversations/import", json={"content": json.dumps(envelope(shape))})
        assert response.status_code == 422
        assert "reports failure" in response.json()["detail"]
        assert "PRIVATE-CACHED-TEXT" not in response.text
        assert snapshot(app) == before
    factory.assert_not_called()


@pytest.mark.parametrize("shape", ["outer", "inner", "records"])
@pytest.mark.parametrize("status", [True, None, 0, "false"])
def test_only_explicit_boolean_false_is_rejected(shape, status):
    parsed = parse_import(json.dumps(envelope(shape, status)))
    assert len(parsed) == 1 and parsed[0][0].messages[0].timestamp == ""


def test_raw_conversation_metadata_is_not_mistaken_for_a_response_envelope():
    parsed = parse_import(json.dumps(ROW | {"isSuccess": False}))
    assert parsed[0][0].id == ROW["id"]

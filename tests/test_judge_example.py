"""Importing the example through the input-only endpoint never starts a review or creates a grade."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from cqa.settings import Settings


def test_example_import_is_repeatable_and_never_starts_a_review(tmp_path):
    def forbidden_evaluator(*args, **kwargs):
        raise AssertionError("Import must not invoke an evaluator")

    settings = Settings(api_key="", ledger_path=tmp_path / "usage.sqlite3")
    app = create_app(settings=settings, database_path=tmp_path / "app.sqlite3",
                     evaluator_factory=forbidden_evaluator)
    sample = (Path(__file__).resolve().parents[1] / "examples/judge-example.json").read_text(encoding="utf-8")
    with TestClient(app) as client:
        before = client.get("/api/config").json()
        first = client.post("/api/conversations/import", json={"content": sample})
        assert first.status_code == 200
        assert first.json()["created"] == 1
        saved_id = first.json()["conversations"][0]["id"]
        content = client.get(f"/api/conversations/{saved_id}").json()["content"]
        assert len(content["messages"]) == 9
        assert len(content["references"]) == 1
        again = client.post("/api/conversations/import", json={"content": sample})
        assert again.status_code == 200
        assert again.json()["created"] == 0
        assert again.json()["reused"] == 1
        assert again.json()["conversations"][0]["id"] == saved_id
        assert client.get("/api/jobs").json() == []
        assert len(client.get("/api/conversations").json()) == 1
        assert client.get("/api/config").json() == before

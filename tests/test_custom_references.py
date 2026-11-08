"""Local source attachment is immutable, bounded, and never contacts a provider."""

from copy import deepcopy

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.custom_references import register_custom_reference_routes
from backend.storage import Document, Store
from cqa.models import Conversation

PRIVATE = "PRIVATE-DOCUMENT-CONTENT"
SOURCE = {"id": "source-chat", "channel": "agent chat", "language": "RU", "knowledge_scope": "profile",
    "occurred_on": "2026-11-08", "messages": [{"id": "m1", "speaker": "client", "timestamp": "00:01", "text": "Как изменить профиль?"}],
    "references": [{"id": "existing", "text": "Original attached text.", "provenance": "Original supplied source"}]}
EXTRA = {"recording_url": "https://example.org/recording", "retained": {"field": "value"}, "temporal_context": {"origin": "explicit"}}


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / "sources.sqlite3")
    with store.session.begin() as session:
        original, _ = store.document(session, "conversation", Conversation.model_validate(SOURCE).model_dump(), deepcopy(EXTRA))
        original_id = original.id
    app = FastAPI()

    def view(document, detail=False, session=None):
        return {"id": document.id, "content": document.content, "metadata": document.extra}

    register_custom_reference_routes(app, store, view)
    with TestClient(app) as client:
        yield client, store, original_id


def document(**updates):
    return {"title": "Инструкция по профилю", "text": "  Исходный текст\nс точными пробелами.  ", **updates}


def post(client, source_id, documents, *, preview=False):
    suffix = "/preview" if preview else ""
    return client.post(f"/api/conversations/{source_id}/custom-references{suffix}", json={"documents": documents})


def count(store):
    with store.session() as session:
        return len(list(session.scalars(select(Document))))


def test_multiple_documents_preserve_original_sources_text_and_metadata(setup):
    client, store, source_id = setup
    items = [document(source_url="https://example.org/help", scope="profile", date_kind="snapshot", snapshot_on="2026-11-08"),
             document(title="Дополнение", text="Второй документ.")]
    response = post(client, source_id, items)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["id"] != source_id
    assert saved["content"]["messages"] == SOURCE["messages"]
    assert saved["content"]["knowledge_scope"] == SOURCE["knowledge_scope"]
    assert saved["content"]["occurred_on"] == SOURCE["occurred_on"]
    assert saved["content"]["reference_context"] is None
    assert len(saved["content"]["references"]) == 3
    assert saved["content"]["references"][1]["text"] == items[0]["text"]
    assert saved["content"]["references"][1]["source_url"] == items[0]["source_url"]
    assert saved["content"]["references"][1]["date_basis"] == "snapshot"
    assert saved["content"]["references"][1]["valid_from"] is None
    for name, value in EXTRA.items():
        assert saved["metadata"][name] == value
    assert saved["metadata"]["reference_parent_revision_id"] == source_id
    reference_id = saved["content"]["references"][1]["id"]
    assert saved["metadata"]["custom_reference_documents"][reference_id]["title"] == items[0]["title"]
    assert "не проверялись" in saved["content"]["references"][1]["provenance"]
    with store.session() as session:
        original = session.get(Document, source_id)
        assert len(original.content["references"]) == 1
        assert original.extra == EXTRA


def test_repeating_on_parent_or_child_reuses_saved_revision_and_duplicate_input(setup):
    client, store, source_id = setup
    first = post(client, source_id, [document(), document()]).json()
    assert first["custom_reference_summary"]["added"] == 1
    assert first["custom_reference_summary"]["reused"] == 1
    assert post(client, source_id, [document()]).json()["id"] == first["id"]
    repeated = post(client, first["id"], [document()]).json()
    assert repeated["id"] == first["id"]
    assert repeated["custom_reference_summary"]["added"] == 0
    assert count(store) == 2
    changed = post(client, first["id"], [document(text="Изменённый текст.")]).json()
    assert changed["id"] != first["id"] and len(changed["content"]["references"]) == 3


def test_preview_is_read_only_and_unknown_metadata_stays_unknown(setup):
    client, store, source_id = setup
    preview = post(client, source_id, [document()], preview=True)
    assert preview.status_code == 200
    result = preview.json()
    assert result["documents"][0]["warnings"] == ["user_provided", "source_unknown", "scope_unknown", "date_unknown"]
    assert count(store) == 1
    saved = post(client, source_id, [document()]).json()["content"]["references"][-1]
    assert saved["scope"] is None and saved["snapshot_on"] is None
    assert saved["valid_from"] is None and saved["valid_until"] is None and saved["retrieved_on"] is None
    assert "действие на дату диалога не подтверждено" in saved["provenance"]


@pytest.mark.parametrize(("fields", "reason"), [
    ({"scope": "different-product"}, "scope_mismatch"),
    ({"date_kind": "snapshot", "snapshot_on": "2026-11-07"}, "snapshot_date_mismatch"),
    ({"date_kind": "validity", "valid_from": "2026-11-09"}, "before_validity_window"),
    ({"date_kind": "validity", "valid_until": "2026-11-07"}, "after_validity_window"),
])
def test_scope_and_date_guards_are_preserved_without_rewriting_conversation(setup, fields, reason):
    client, _, source_id = setup
    saved = post(client, source_id, [document(**fields)]).json()
    info = saved["custom_reference_summary"]["documents"][0]
    assert not info["usable"] and reason in info["rejection_reasons"]
    assert saved["content"]["occurred_on"] == SOURCE["occurred_on"]
    assert saved["content"]["knowledge_scope"] == SOURCE["knowledge_scope"]


def test_existing_conditional_context_is_retained_and_not_presented_as_actual_date(setup):
    client, store, _ = setup
    original = Conversation.model_validate(SOURCE | {"occurred_on": None, "knowledge_scope": None,
        "reference_context": {"mode": "snapshot_review", "scope": "profile", "as_of": "2026-11-08",
            "rationale": "Explicit test assumption", "pack_id": "previous-pack", "pack_sha256": "a" * 64}})
    with store.session.begin() as session:
        source, _ = store.document(session, "conversation", original.model_dump(), EXTRA)
        source_id = source.id
    saved = post(client, source_id, [document(scope="profile", date_kind="snapshot", snapshot_on="2026-11-08")]).json()
    assert saved["content"]["reference_context"] == original.reference_context.model_dump()
    assert saved["content"]["occurred_on"] is None and saved["content"]["knowledge_scope"] is None
    assert saved["custom_reference_summary"]["context"]["assessment"]["conditional"] is True


@pytest.mark.parametrize("invalid", [
    document(title="   "), document(text="\n "), document(text=PRIVATE * 10_000),
    document(source_url="javascript:" + PRIVATE), document(source_url="https://user:password@example.org/"),
    document(date_kind="snapshot"), document(date_kind="snapshot", snapshot_on=PRIVATE),
    document(date_kind="unknown", valid_from="2026-01-01"),
    document(date_kind="validity", valid_from="2026-11-09", valid_until="2026-11-08"),
    document(**{PRIVATE: PRIVATE}),
])
def test_bad_input_is_atomic_and_never_echoes_document_content(setup, invalid):
    client, store, source_id = setup
    response = post(client, source_id, [document(), invalid])
    assert response.status_code == 422
    assert PRIVATE not in response.text
    assert count(store) == 1


def test_request_limits_and_missing_conversation(setup):
    client, store, source_id = setup
    assert post(client, source_id, [document()] * 11).status_code == 422
    assert post(client, source_id, [document(text="x" * 100_000)] * 4).json()["detail"]["code"] == "total_text_limit"
    too_large = client.post(f"/api/conversations/{source_id}/custom-references", content=b"x" * 2_000_001)
    assert too_large.status_code == 413
    assert post(client, "missing", [document()]).status_code == 404
    assert count(store) == 1

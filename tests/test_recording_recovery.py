"""Recording recovery changes presentation, never frozen assessment inputs."""

import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.recordings import matching_recording
from backend.storage import Document, Job, Store, digest
from cqa.models import Checklist, Conversation, Evaluation, Judgment
from cqa.models import TestCase as Case
from cqa.scoring import calculate_score
from cqa.settings import Settings
from scripts.import_saved_assessments import import_report, sha


def saved_report(tmp_path):
    conversation = Conversation(id="call-recording-test", channel="voice call", language="EN",
        knowledge_scope="assessment-context", messages=[
            {"id": "m1", "timestamp": "00:01", "speaker": "client", "text": "I need a statement."},
            {"id": "m2", "timestamp": "00:02", "speaker": "operator", "text": "Hello, I am Ana."}])
    checklist = Checklist(id="recording-test", version="1", title="Greeting", instructions=[], criteria=[
        {"id": "greeting", "title": "Greeting", "instruction": "Greet the client.", "kind": "binary", "weight": 1,
         "levels": [{"value": "yes", "fraction": 1, "description": "Greeting present."},
                    {"value": "no", "fraction": 0, "description": "Greeting absent."}]}])
    evaluation = Evaluation(judgments=[Judgment(criterion_id="greeting", status="scored", answer="yes",
        explanation="The operator greets the client.", evidence=[{"message_id": "m2", "quote": "Hello, I am Ana."}],
        counterevidence=[], checked_message_ids=[], uncertainty=None)], request_coverage=[], scope_notes=[])
    record = {"status": "completed", "conversation_id": conversation.id, "strategy": "direct",
        "input_fingerprint": "frozen-input", "evaluation": evaluation.model_dump(),
        "score": calculate_score(evaluation, checklist)}
    case = Case(id=conversation.id, family="isolated-test", source="authored", label_provenance="unlabelled",
                tags=[], conversation=conversation, expectations=[])
    report = tmp_path / "saved.json"
    report.with_suffix(".suite.jsonl").write_text(case.model_dump_json() + "\n", encoding="utf-8")
    report.write_text(json.dumps({"suite_sha256": sha(case.model_dump_json().encode()),
        "selected_case_ids": [case.id], "rows": [{"case_id": case.id, "record": record}]}), encoding="utf-8")
    rubric = tmp_path / "checklist.json"
    rubric.write_text(checklist.model_dump_json(), encoding="utf-8")
    return report, rubric, conversation.model_dump(), record


def test_new_import_preserves_unique_recording_and_reuse_is_idempotent(tmp_path):
    report, rubric, content, record = saved_report(tmp_path)
    path = tmp_path / "app.sqlite3"
    store = Store(path)
    with store.session.begin() as session:
        donor_content = content | {"knowledge_scope": "original-context"}
        donor, _ = store.document(session, "conversation", donor_content,
                                  {"recording_url": "https://example.org/recording"})
        donor_id = donor.id
    first = import_report(report, path, rubric)
    second = import_report(report, path, rubric)
    assert first["imported"] == second["reused"] == 1
    assert first["jobs"] == second["jobs"]
    with store.session() as session:
        job = session.get(Job, first["jobs"][0]["job_id"])
        source = session.get(Document, job.conversation_id)
        assert source.content == content and job.record == record
        assert source.extra["recording_url"] == "https://example.org/recording"
        assert source.extra["recording_source_revision_id"] == donor_id
        assert source.content_hash == digest({"content": content, "metadata": source.extra})
    store.engine.dispose()


def test_existing_import_recovers_view_only_and_conflicts_remove_fallback(tmp_path):
    report, rubric, content, record = saved_report(tmp_path)
    path = tmp_path / "app.sqlite3"
    imported = import_report(report, path, rubric)
    job_id = imported["jobs"][0]["job_id"]
    store = Store(path)
    with store.session.begin() as session:
        job = session.get(Job, job_id)
        source = session.get(Document, job.conversation_id)
        source_id, original_hash = source.id, source.content_hash
        assert source.extra == {}
        donor_content = content | {"knowledge_scope": "original-context"}
        donor, _ = store.document(session, "conversation", donor_content,
                                  {"recording_url": "https://example.org/recording"})
        donor_id = donor.id

    def no_inference(*args, **kwargs):
        raise AssertionError("Recording recovery must never instantiate an evaluator")

    app = create_app(settings=Settings(api_key="", ledger_path=tmp_path / "usage.sqlite3"),
                     database_path=path, evaluator_factory=no_inference)
    with TestClient(app) as client:
        expected = {"url": "https://example.org/recording", "source_revision_id": donor_id,
                    "origin": "matching_source_revision"}
        for endpoint in [f"/api/conversations/{source_id}", f"/api/jobs/{job_id}", f"/api/jobs/{job_id}/export"]:
            response = client.get(endpoint)
            assert response.status_code == 200
            value = response.json()
            source_view = value.get("conversation", value)
            assert source_view["resolved_recording"] == expected
            assert source_view["metadata"] == {} and source_view["content_hash"] == original_hash
            if "record" in value:
                assert value["record"] == record
        assert import_report(report, path, rubric)["reused"] == 1
        with store.session.begin() as session:
            store.document(session, "conversation", donor_content,
                           {"recording_url": "https://example.org/conflicting-recording"})
        assert client.get(f"/api/conversations/{source_id}").json()["resolved_recording"] is None
        own = client.get(f"/api/conversations/{donor_id}").json()
        assert own["metadata"]["recording_url"] == expected["url"] and own["resolved_recording"] is None
    with store.session() as session:
        source = session.get(Document, source_id)
        assert source.content == content and source.extra == {} and source.content_hash == original_hash
        assert session.get(Job, job_id).record == record
    store.engine.dispose()


@pytest.mark.parametrize("changed", ["id", "channel", "language", "messages"])
def test_recording_never_crosses_a_changed_dialogue_identity(tmp_path, changed):
    _, _, content, _ = saved_report(tmp_path)
    other = deepcopy(content)
    if changed == "messages":
        other["messages"][0]["text"] = "A different request."
    else:
        other[changed] = {"id": "another-id", "channel": "agent chat", "language": "RU"}[changed]
    store = Store(tmp_path / "app.sqlite3")
    with store.session.begin() as session:
        store.document(session, "conversation", other, {"recording_url": "https://example.org/other"})
        assert matching_recording(session, content) is None
    store.engine.dispose()

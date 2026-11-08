"""Offline control preparation must not mistake development inputs for PROD."""

import json
import shutil

import pytest

from cqa.datasets import load_cases
from cqa.settings import ROOT
from scripts import prepare_control_run as control


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    for name in ("references/freedom-global-products-20261107.json",
                 "checklists/freedom-reviewed-016.json"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    monkeypatch.setattr(control, "ROOT", tmp_path)
    rows = [{"conversation_id": f"offline-{i}", "channel": "agent chat", "language": "KZ",
             "transcript": [{"timestamp": "00:01", "speaker": "client", "text": "Сәлеметсіз бе!"},
                            {"timestamp": "00:02", "speaker": "operator", "text": "Сәлеметсіз бе!"}]}
            for i in range(10)]
    payload = {"isSuccess": True, "data": {"dataset_group_id": "DEV", "records": rows}}
    source, output = tmp_path / "source.json", tmp_path / "artifacts/control/input.jsonl"
    return source, output, payload


def save(source, payload):
    source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_dev_subset_cannot_be_prepared_as_prod(workspace):
    source, output, payload = workspace
    save(source, payload)
    with pytest.raises(ValueError, match="DEV cannot be labelled PROD"):
        control.prepare(source, output)
    assert not output.exists()


def test_explicit_rehearsal_preserves_original_turns_and_has_no_labels(workspace):
    source, output, payload = workspace
    save(source, payload)
    original = source.read_bytes()
    result = control.prepare(source, output, split="rehearsal")
    manifest = json.loads(output.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    assert manifest["split"] == "rehearsal" and manifest["source"]["dataset_group_id"] == "DEV"
    assert result["paid_api_calls"] == 0 and result["results_created"] is False
    for case, row in zip(load_cases(output), payload["data"]["records"], strict=True):
        assert not case.expectations and case.label_provenance == "unlabelled"
        assert case.conversation.id == row["conversation_id"]
        assert [m.model_dump(exclude={"id"}) for m in case.conversation.messages] == row["transcript"]
        assert case.conversation.occurred_on is None
        assert case.conversation.knowledge_scope is None
        assert case.conversation.reference_context.mode == "snapshot_review"
    assert source.read_bytes() == original


def test_failed_organizer_response_cannot_create_control_inputs(workspace):
    source, output, payload = workspace
    payload["isSuccess"] = False
    payload["data"]["dataset_group_id"] = "PROD"
    save(source, payload)
    with pytest.raises(ValueError, match="reports failure"):
        control.prepare(source, output)
    assert not output.exists()


@pytest.mark.parametrize("field,value", [
    ("knowledge_scope", "a-different-broker"),
    ("occurred_on", "2026-11-01"),
])
def test_known_scope_or_source_date_conflict_cannot_be_hidden(workspace, field, value):
    source, output, payload = workspace
    payload["data"]["dataset_group_id"] = "PROD"
    row = payload["data"]["records"][0]
    row[field] = value
    if field == "occurred_on":
        row["transcript"][0]["timestamp"] = "2026-11-02T10:00:00+05:00"
        row["transcript"][1]["timestamp"] = "2026-11-02T10:00:01+05:00"
    save(source, payload)
    with pytest.raises(ValueError, match="scope|timestamp"):
        control.prepare(source, output)
    assert not output.exists()

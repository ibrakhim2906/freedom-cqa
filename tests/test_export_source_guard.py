"""Known DEV and failed organizer responses must not become control submissions."""

import json
import sys

import pytest

from scripts.export_submission import main, validate_source_group


@pytest.mark.parametrize("group", ["DEV", "dev", " DEV "])
@pytest.mark.parametrize("nested", [True, False])
def test_explicit_dev_source_is_rejected_for_prod(group, nested):
    envelope = {"dataset_group_id": group, "records": []}
    payload = {"isSuccess": True, "data": envelope} if nested else envelope
    with pytest.raises(ValueError, match="DEV cannot be exported as PROD"):
        validate_source_group(json.dumps(payload), "prod")
    validate_source_group(json.dumps(payload), "dev")


@pytest.mark.parametrize("split", ["dev", "prod"])
@pytest.mark.parametrize("nested", [False, True])
def test_failed_organizer_response_is_rejected(split, nested):
    payload = {"isSuccess": True, "data": {"records": []}}
    (payload["data"] if nested else payload)["isSuccess"] = False
    with pytest.raises(ValueError, match="reports failure"):
        validate_source_group(json.dumps(payload), split)


def test_unknown_control_group_and_supported_unwrapped_formats_remain_available():
    for payload in [{"data": {"dataset_group_id": "ROUND-2", "records": []}}, [], {"id": "one"}]:
        validate_source_group(json.dumps(payload), "prod")
    validate_source_group('{"id":"one"}\n{"id":"two"}', "prod")


def test_cli_rejects_dev_before_reading_reports_or_overwriting_output(tmp_path, monkeypatch, capsys):
    source, output = tmp_path / "source.json", tmp_path / "results.json"
    source.write_text(json.dumps({"isSuccess": True, "data": {
        "dataset_group_id": "DEV", "records": []}}), encoding="utf-8")
    output.write_bytes(b"preserve-existing-submission")
    monkeypatch.setattr(sys, "argv", ["export_submission", "--source", str(source),
        "--report", str(tmp_path / "must-not-be-read.json"), "--split", "prod", "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "DEV cannot be exported as PROD" in capsys.readouterr().err
    assert output.read_bytes() == b"preserve-existing-submission"


@pytest.mark.parametrize("nested", [False, True])
def test_cli_rejects_failed_response_before_reading_reports_or_overwriting_output(tmp_path, monkeypatch, capsys, nested):
    source, output = tmp_path / "source.json", tmp_path / "results.json"
    payload = {"isSuccess": True, "data": {"records": []}}
    (payload["data"] if nested else payload)["isSuccess"] = False
    source.write_text(json.dumps(payload), encoding="utf-8")
    output.write_bytes(b"preserve-existing-submission")
    monkeypatch.setattr(sys, "argv", ["export_submission", "--source", str(source),
        "--report", str(tmp_path / "must-not-be-read.json"), "--split", "prod", "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "reports failure" in capsys.readouterr().err
    assert output.read_bytes() == b"preserve-existing-submission"

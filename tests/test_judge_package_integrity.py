"""Regression checks for policy applicability in the shipped offline example."""
import json

from backend.demo import prepared_demo
from cqa.grounding import evidence_context_for
from cqa.models import Conversation
from cqa.rubric import load_checklist
from cqa.settings import ROOT


def test_shipped_example_references_are_usable_under_its_actual_scope():
    examples = json.loads((ROOT / "examples/judge-example.json").read_text(encoding="utf-8"))
    assert examples
    for raw in examples:
        conversation = Conversation.model_validate(raw)
        references = evidence_context_for(conversation)["references"]
        assert references
        assert all(item["usable"] and not item["rejection_reasons"] for item in references)


def test_prepared_demo_policy_citations_only_use_applicable_supplied_references():
    checklist = load_checklist()
    conversation, record = prepared_demo(checklist)
    usable = {item["reference_id"] for item in record["evidence_context"]["references"] if item["usable"]}
    sources = {reference.id: reference.text for reference in conversation.references}
    policy_based = [item for item in record["assessment"]["criteria"].values()
                    if item["factual_basis"] == "policy_reference"]
    assert policy_based
    for assessment in policy_based:
        assert assessment["reference_evidence"]
        for evidence in assessment["reference_evidence"]:
            assert evidence["reference_id"] in usable
            assert evidence["quote"] in sources[evidence["reference_id"]]
    assert record["score"]["total"] == 87.5
    assert record["attempt_count"] == 0 and record["response_id"] is None


def test_packaged_documented_submission_export_help_is_self_contained(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    import sysconfig
    import zipfile

    from scripts.build_judge_package import REQUIRED_FILES, build_package

    source = tmp_path / "source"
    for name in REQUIRED_FILES:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == "frontend/dist/index.html":
            target.write_text('<script src="/assets/app.js"></script>', encoding="utf-8")
        else:
            shutil.copyfile(ROOT / name, target)
    assets = source / "frontend/dist/assets"
    assets.mkdir()
    (assets / "app.js").write_text("// Offline test asset", encoding="utf-8")
    for folder in ("cqa", "backend"):
        (source / folder).mkdir(exist_ok=True)
        for path in (ROOT / folder).glob("*.py"):
            shutil.copyfile(path, source / folder / path.name)
    output = tmp_path / "judge.zip"
    build_package(source, output)
    with zipfile.ZipFile(output) as archive:
        assert "Freedom CQA/scripts/export_submission.py" in archive.namelist()
        archive.extractall(tmp_path / "extracted")
    package = tmp_path / "extracted/Freedom CQA"
    # -S prevents an editable repository installation from silently supplying
    # a missing scripts namespace module outside the extracted archive.
    bootstrap = (
        "import sys;from pathlib import Path;"
        f"sys.path[:0]={[str(package), sysconfig.get_path('purelib')]!r};"
        "import scripts.export_submission as exporter;"
        f"assert Path(exporter.__file__).resolve().is_relative_to(Path({str(package)!r}).resolve());"
        "sys.argv=['scripts.export_submission','--help'];exporter.main()"
    )
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("OPENAI_", "CQA_")) and key != "PYTHONPATH"}
    environment["OPENAI_API_KEY"] = ""
    result = subprocess.run([sys.executable, "-B", "-S", "-c", bootstrap],
                            cwd=package, env=environment, capture_output=True,
                            text=True, encoding="utf-8", timeout=20, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--source" in result.stdout and "--report" in result.stdout and "--split" in result.stdout
    assert not (package / ".env").exists()
    assert not (package / "data").exists()

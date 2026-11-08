from cqa.rubric import DEFAULT_CHECKLIST_PATH, load_checklist
from cqa.settings import ROOT, Settings


def test_fresh_checkout_uses_delivery_assessor_without_local_env(monkeypatch, tmp_path):
    monkeypatch.setattr("cqa.settings.ROOT", tmp_path)
    for name in ("CQA_STRATEGY", "OPENAI_MODEL", "CQA_REASONING_EFFORT", "CQA_LEDGER_PATH", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.load()
    assert settings.strategy == "assessor"
    assert settings.model == "gpt-6.1-sol" and settings.effort == "medium"
    assert settings.api_key == ""
    assert settings.ledger_path == tmp_path / "data/runtime/usage.sqlite3"
    assert load_checklist() == load_checklist(ROOT / DEFAULT_CHECKLIST_PATH)

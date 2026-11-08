import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts.build_judge_package import REQUIRED_FILES, build_package
from scripts.configure_judge import configure_key, key_is_configured
from scripts.launch_judge import acquire_workspace_lock, ensure_settings, verify_package, wait_until_ready

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate(tmp_path):
    root = tmp_path / "source"
    for name in REQUIRED_FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    for name in ("backend/app.py", "cqa/settings.py", "cqa/__init__.py"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Runtime source", encoding="utf-8")
    (root / ".env.example").write_text("OPENAI_API_KEY=\nOTHER=preserve\n", encoding="utf-8")
    (root / "frontend/dist/index.html").write_text('<script src="/assets/app.js"></script>', encoding="utf-8")
    (root / "frontend/dist/assets").mkdir()
    (root / "frontend/dist/assets/app.js").write_text("// built UI", encoding="utf-8")
    return root


def test_package_allowlist_excludes_local_settings_data_and_sources(candidate, tmp_path):
    for name in (".env", ".env.local", "data/runtime/app.sqlite3", "data/private/dev.json", "evals/private.jsonl",
                 ".git/config", "frontend/src/App.tsx", "frontend/node_modules/package.json",
                 "frontend/dist/assets/app.js.map", "backend/__pycache__/app.pyc", "references/private.json"):
        path = candidate / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("DO NOT SHIP", encoding="utf-8")
    output = tmp_path / "judge.zip"
    result = build_package(candidate, output)
    assert result["bytes"] > 0
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert "Freedom CQA/frontend/dist/assets/app.js" in names
        assert "Freedom CQA/checklists/freedom-reviewed-016.json" in names
        assert "Freedom CQA/checklists/freedom-reviewed-017.json" in names
        assert "Freedom CQA/checklists/freedom-reviewed-018.json" in names
        assert "Freedom CQA/docs/RUSSIAN_CHECKLIST_017.md" in names
        assert not any(b"DO NOT SHIP" in archive.read(name) for name in names)
        manifest = json.loads(archive.read("Freedom CQA/judge-package.json"))
        for name, expected in manifest["files"].items():
            assert hashlib.sha256(archive.read(f"Freedom CQA/{name}")).hexdigest() == expected
    with pytest.raises(FileExistsError):
        build_package(candidate, output)


def test_package_refuses_missing_built_assets(candidate, tmp_path):
    (candidate / "frontend/dist/assets/app.js").unlink()
    with pytest.raises(ValueError, match="app.js"):
        build_package(candidate, tmp_path / "judge.zip")


def test_extracted_package_verifies_and_detects_changed_runtime(candidate, tmp_path):
    output = tmp_path / "judge.zip"
    build_package(candidate, output)
    with zipfile.ZipFile(output) as archive:
        archive.extractall(tmp_path / "extracted")
    root = tmp_path / "extracted/Freedom CQA"
    verify_package(root)
    ensure_settings(root)
    verify_package(root)  # Local settings and runtime data are intentionally outside the manifest.
    (root / "backend/app.py").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="backend/app.py"):
        verify_package(root)


def test_setup_preserves_other_values_and_never_prints_key(candidate, capsys):
    ensure_settings(candidate)
    dummy_key = "sk-test-only-not-a-real-key"
    assert configure_key(candidate, interactive=True, prompt=lambda _: dummy_key, environ={})
    assert key_is_configured(candidate, {})
    assert "OTHER=preserve" in (candidate / ".env").read_text(encoding="utf-8")
    assert dummy_key not in capsys.readouterr().out
    before = (candidate / ".env").read_bytes()
    ensure_settings(candidate)
    assert configure_key(candidate, interactive=True, prompt=lambda _: pytest.fail("must not reprompt"), environ={})
    assert (candidate / ".env").read_bytes() == before


def test_skipping_key_or_noninteractive_setup_never_writes(candidate):
    ensure_settings(candidate)
    before = (candidate / ".env").read_bytes()
    assert not configure_key(candidate, interactive=True, prompt=lambda _: "", environ={})
    assert not configure_key(candidate, interactive=False, prompt=lambda _: pytest.fail("must not prompt"), environ={})
    assert (candidate / ".env").read_bytes() == before


def test_one_packaged_worker_per_folder(candidate):
    first = acquire_workspace_lock(candidate)
    try:
        with pytest.raises(ValueError, match="уже открыта"):
            acquire_workspace_lock(candidate)
    finally:
        first.close()
    acquire_workspace_lock(candidate).close()


def test_readiness_never_opens_browser_or_retries_an_exited_server():
    class Exited:
        def poll(self):
            return 1
    with pytest.raises(RuntimeError, match="завершился"):
        wait_until_ready(Exited(), 8000)


@pytest.mark.skipif(os.name != "nt", reason="Runs the real Windows CMD interpreter")
@pytest.mark.parametrize("exit_code", [0, 7])
def test_packaged_cmd_uses_crlf_russian_utf8_and_forwards_arguments(candidate, tmp_path, exit_code):
    # Simulate a source checkout with LF; the archive must still contain a runnable batch file.
    wrapper = (REPOSITORY / "Start Freedom CQA.cmd").read_bytes().replace(b"\r\n", b"\n")
    (candidate / "Start Freedom CQA.cmd").write_bytes(wrapper)
    output = tmp_path / "judge.zip"
    build_package(candidate, output)
    with zipfile.ZipFile(output) as archive:
        packaged = archive.read("Freedom CQA/Start Freedom CQA.cmd")
        assert b"\r\n" in packaged and b"\n" not in packaged.replace(b"\r\n", b"")
        archive.extractall(tmp_path / "extracted")
    root = tmp_path / "extracted/Freedom CQA"
    verify_package(root)
    bin_dir = tmp_path / "fake tools"
    bin_dir.mkdir()
    (bin_dir / "uv.cmd").write_bytes(b'@echo off\r\n"%TEST_PYTHON%" "%TEST_PROBE%" %*\r\nexit /b %errorlevel%\r\n')
    probe = tmp_path / "probe.py"
    log = tmp_path / "argv.json"
    probe.write_text(
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['TEST_LOG']).write_text(json.dumps({'argv': sys.argv[1:], "
        "'utf8': os.environ.get('PYTHONUTF8'), 'encoding': sys.stdout.encoding}), encoding='utf-8')\n"
        "print('\\u041f\\u0440\\u043e\\u0432\\u0435\\u0440\\u043a\\u0430 UTF-8')\n"
        f"sys.exit({exit_code})\n", encoding="ascii")
    environment = {**os.environ, "PATH": str(bin_dir) + os.pathsep + str(Path(os.environ["SystemRoot"]) / "System32"),
                   "TEST_PYTHON": sys.executable, "TEST_PROBE": str(probe), "TEST_LOG": str(log),
                   "PYTHONUTF8": "0", "PYTHONIOENCODING": "cp1252"}
    command = f'"{os.environ["COMSPEC"]}" /d /s /c ""{root / "Start Freedom CQA.cmd"}" --port 8012 --no-browser --no-prompt"'
    result = subprocess.run(command, check=False,
                            env=environment, input=b"", capture_output=True, timeout=15)
    stdout = result.stdout.decode("utf-8")
    stderr = result.stderr.decode("utf-8")
    assert result.returncode == exit_code, (stdout, stderr)
    assert "Подготавливаем Python" in stdout
    assert "Проверка UTF-8" in stdout
    assert "not recognized" not in stdout + stderr
    if exit_code:
        assert "Не удалось запустить приложение" in stdout
    recorded = json.loads(log.read_text(encoding="utf-8"))
    assert recorded == {"argv": ["run", "--locked", "--no-dev", "python", "scripts/launch_judge.py",
                                  "--port", "8012", "--no-browser", "--no-prompt"],
                        "utf8": "1", "encoding": "utf-8"}
    assert not (root / ".env").exists()
    assert not (root / "data").exists()


@pytest.mark.skipif(os.name != "nt", reason="Runs the real Windows CMD interpreter")
@pytest.mark.parametrize("missing", ["manifest", "uv"])
def test_cmd_missing_prerequisite_guidance_is_readable_without_real_uv(tmp_path, missing):
    wrapper = tmp_path / "Start Freedom CQA.cmd"
    wrapper.write_bytes((REPOSITORY / wrapper.name).read_bytes())
    if missing == "uv":
        (tmp_path / "judge-package.json").write_text("{}", encoding="utf-8")
    environment = {**os.environ, "PATH": str(Path(os.environ["SystemRoot"]) / "System32")}
    command = f'"{os.environ["COMSPEC"]}" /d /s /c ""{wrapper}""'
    result = subprocess.run(command, check=False, cwd=tmp_path, env=environment, input=b"", capture_output=True, timeout=15)
    stdout = result.stdout.decode("utf-8")
    assert result.returncode == 1
    assert "not recognized" not in stdout + result.stderr.decode("utf-8")
    if missing == "uv":
        assert "Сначала установите uv: winget install --id astral-sh.uv -e" in stdout
        assert "https://docs.astral.sh/uv/getting-started/installation/" in stdout
    else:
        assert "Этот запуск предназначен для готового ZIP-пакета" in stdout
    assert not (tmp_path / ".env").exists()


@pytest.mark.parametrize("arguments,returncode,expected", [
    (["--help"], 0, "Открыть подготовленную версию"),
    (["--port", "0"], 2, "Порт должен быть целым числом"),
])
def test_direct_launcher_overrides_legacy_pipe_encoding(arguments, returncode, expected):
    result = subprocess.run([sys.executable, str(REPOSITORY / "scripts/launch_judge.py"), *arguments], check=False,
                            env={**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "cp1252"},
                            capture_output=True, timeout=15)
    assert result.returncode == returncode, result.stderr
    assert expected in (result.stdout + result.stderr).decode("utf-8")

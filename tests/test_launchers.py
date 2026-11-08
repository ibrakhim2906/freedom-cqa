"""Exercise launcher control flow with fake tools: no downloads, builds, keys or servers."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
SHELL = shutil.which("sh")
if not SHELL and os.name == "nt":
    git_shell = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/usr/bin/sh.exe"
    if git_shell.exists():
        SHELL = str(git_shell)


@pytest.fixture(params=["powershell", "shell"])
def launcher(request, tmp_path):
    kind = request.param
    executable = POWERSHELL if kind == "powershell" else SHELL
    if not executable:
        pytest.skip(f"{kind} is not installed")
    if kind == "powershell" and os.name != "nt":
        pytest.skip("Windows launcher uses Windows command shims")
    project = tmp_path / "checkout with spaces"
    (project / "scripts").mkdir(parents=True)
    (project / "frontend").mkdir()
    for file in ("pyproject.toml", "uv.lock", "frontend/package.json", "frontend/pnpm-lock.yaml"):
        (project / file).write_text("test fixture\n", encoding="utf-8")
    (project / ".env.example").write_text("OPENAI_API_KEY=\n", encoding="utf-8")
    suffix = "ps1" if kind == "powershell" else "sh"
    script = project / "scripts" / f"start-local.{suffix}"
    script.write_text((ROOT / "scripts" / script.name).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    tool_dir = tmp_path / "tools"
    tool_dir.mkdir()
    environment = dict(os.environ)
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("ENV", None)
    environment.pop("BASH_ENV", None)
    environment["PATH"] = str(tool_dir)
    if kind == "shell":
        environment["PATH"] += os.pathsep + str(Path(executable).parent)

    def tool(name, version, allow_setup=False):
        if kind == "powershell":
            file = tool_dir / f"{name}.cmd"
            content = f'@echo off\nif "%1"=="--version" (\n echo {version}\n exit /b 0\n)\n'
            content += f'if "%2"=="--version" (\n echo {version}\n exit /b 0\n)\n'
            # cmd treats the '=' in pnpm's first option as an argument separator.
            content += f'if "%3"=="--version" (\n echo {version}\n exit /b 0\n)\n'
            content += f"exit /b {0 if allow_setup else 87}\n"
        else:
            file = tool_dir / name
            content = f'#!/bin/sh\ncase "$*" in *--version*) printf "%s\\n" "{version}"; exit 0;; esac\n'
            content += f"exit {0 if allow_setup else 87}\n"
        file.write_text(content, encoding="utf-8", newline="\n")
        file.chmod(0o755)

    for name, version in (("uv", "uv 0.12.17"), ("node", "v24.22.1"), ("pnpm", "11.25.0")):
        tool(name, version)

    def run(*arguments, check=True):
        command = [executable, "-NoProfile", "-File", str(script)] if kind == "powershell" else [executable, str(script)]
        if check:
            command.append("-CheckOnly" if kind == "powershell" else "--check")
        command.extend(arguments)
        return subprocess.run(command, cwd=tmp_path, env=environment, text=True, encoding="utf-8", capture_output=True, timeout=20,
                              check=False)

    return kind, project, tool_dir, tool, run


def tree_snapshot(project):
    return {str(file.relative_to(project)): file.read_bytes() for file in project.rglob("*") if file.is_file()}


def test_check_mode_never_creates_settings_or_runs_install_commands(launcher):
    _, project, _, _, run = launcher
    before = tree_snapshot(project)
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Проверка пройдена" in result.stdout
    assert tree_snapshot(project) == before
    assert not (project / ".env").exists()


def test_check_mode_preserves_existing_settings(launcher):
    _, project, _, _, run = launcher
    (project / ".env").write_text("TEST_ONLY_SENTINEL=unchanged\n", encoding="utf-8")
    before = tree_snapshot(project)
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TEST_ONLY_SENTINEL" not in result.stdout + result.stderr
    assert tree_snapshot(project) == before


@pytest.mark.parametrize("port", ["0", "65536", "invalid"])
def test_invalid_port_fails_before_any_setup(launcher, port):
    kind, project, _, _, run = launcher
    before = tree_snapshot(project)
    result = run(*(["-Port", port] if kind == "powershell" else [port]))
    assert result.returncode != 0
    assert tree_snapshot(project) == before


def test_wrong_node_version_reports_install_instructions(launcher):
    _, project, _, tool, run = launcher
    tool("node", "v20.0.0")
    before = tree_snapshot(project)
    result = run()
    assert result.returncode != 0
    assert "https://nodejs.org/en/download" in result.stdout
    assert tree_snapshot(project) == before


def test_missing_pnpm_reports_exact_install_command(launcher):
    kind, project, tool_dir, _, run = launcher
    # Keep a failing shim first on PATH so /usr/bin/pnpm can never be invoked.
    shim = tool_dir / ("pnpm.cmd" if kind == "powershell" else "pnpm")
    shim.write_text("@echo off\nexit /b 127\n" if kind == "powershell" else "#!/bin/sh\nexit 127\n",
                    encoding="utf-8", newline="\n")
    before = tree_snapshot(project)
    result = run()
    assert result.returncode != 0
    assert "npm install -g pnpm@11.25.0" in result.stdout
    assert tree_snapshot(project) == before


@pytest.mark.parametrize("existing", [False, True])
def test_normal_launcher_creates_settings_once_with_only_stubbed_setup_tools(launcher, existing):
    _, project, _, tool, run = launcher
    for name, version in (("uv", "uv 0.12.17"), ("node", "v24.22.1"), ("pnpm", "11.25.0")):
        tool(name, version, allow_setup=True)
    expected = "TEST_ONLY_SENTINEL=unchanged\n" if existing else "OPENAI_API_KEY=\n"
    if existing:
        (project / ".env").write_text(expected, encoding="utf-8")
    result = run(check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / ".env").read_text(encoding="utf-8") == expected
    assert "[4/4] Запускаем http://127.0.0.1:8000" in result.stdout


def test_prebuilt_package_does_not_need_or_run_node_and_pnpm(launcher):
    _, project, _, tool, run = launcher
    (project / "judge-package.json").write_text(
        '{"package_type": "freedom-cqa-judge", "prebuilt_frontend": true}', encoding="utf-8")
    (project / "frontend/dist").mkdir()
    (project / "frontend/dist/index.html").write_text("Built interface", encoding="utf-8")
    for name in ("launch_judge.py", "configure_judge.py"):
        (project / "scripts" / name).write_text("# Test only", encoding="utf-8")
    # Incorrect versions would fail source preflight; packaged preflight must skip them.
    tool("node", "v1.0.0")
    tool("pnpm", "1.0.0")
    (project / "frontend/package.json").unlink()
    (project / "frontend/pnpm-lock.yaml").unlink()
    before = tree_snapshot(project)
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Node.js и pnpm не требуются" in result.stdout
    assert tree_snapshot(project) == before


@pytest.mark.parametrize("configured", [False, True])
@pytest.mark.parametrize("name", ["start-local.ps1", "start-local.sh"])
def test_actual_key_warning_survives_windows_legacy_output_encoding(tmp_path, configured, name):
    import sys

    source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
    if name.endswith("ps1"):
        check = source.split("$taskKeyCheck = @'\n", 1)[1].split("\n'@", 1)[0]
    else:
        check = source.split("uv run --no-sync --no-dev python -c '\n", 1)[1].split("\n'", 1)[0]
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("CQA_", "OPENAI_"))}
    environment.update(PYTHONIOENCODING="cp1252", PYTHONUTF8="0",
                       OPENAI_API_KEY="test-only-never-used" if configured else "")
    # Run the launcher's actual configuration check, not a fake tool stub.
    check = "import sys;sys.path.insert(0," + repr(str(ROOT)) + ");\n" + check
    result = subprocess.run([sys.executable, "-c", check], cwd=tmp_path, env=environment,
                            capture_output=True, timeout=15, check=False)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    output = result.stdout.decode("utf-8")
    assert ("Ключ API настроен" if configured else "Ключ API не задан") in output
    assert "test-only-never-used" not in output

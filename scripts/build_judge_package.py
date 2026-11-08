"""Package the built application from an explicit runtime allowlist; never install or build."""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

PACKAGE_ROOT = "Freedom CQA"
PACKAGE_MARKER = "judge-package.json"
REQUIRED_FILES = (
    "pyproject.toml", "uv.lock", ".env.example", "README.md",
    "docs/JUDGE_QUICKSTART.md", "docs/WORKFLOW.md", "docs/PERFORMANCE.md",
    "docs/SUBMISSION_FORMAT.md", "docs/RUSSIAN_CHECKLIST_017.md",
    "checklists/freedom-reviewed-016.json", "checklists/freedom-reviewed-017.json",
    "references/fbroker-platform-20261107.json", "references/freedom-global-products-20261107.json",
    "examples/judge-example.json", "config/submission.json",
    "scripts/start-local.ps1", "scripts/start-local.sh", "scripts/launch_judge.py",
    "scripts/configure_judge.py", "scripts/export_submission.py", "Start Freedom CQA.cmd", "Start Freedom CQA.sh",
    "frontend/dist/index.html",
)
ASSET_EXTENSIONS = {".html", ".js", ".css", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".ico", ".woff", ".woff2", ".ttf"}
PACKAGE_GUIDE = """Freedom CQA — запуск для проверки

1. Распакуйте ZIP полностью в отдельную папку. Не запускайте приложение внутри архива.
2. Установите uv, если он ещё не установлен:
   Windows: winget install --id astral-sh.uv -e
   Инструкции: https://docs.astral.sh/uv/getting-started/installation/
3. Windows: дважды нажмите Start Freedom CQA.cmd.
   Linux/macOS: sh "Start Freedom CQA.sh"
4. Если ключ API ещё не задан, введите его в терминале. Символы не отображаются.
   Нажмите Enter, чтобы пропустить ввод и посмотреть готовый учебный разбор без ключа.
5. Дождитесь открытия браузера. В приложении откройте помощь и попробуйте пример.

Node.js, pnpm и сборка интерфейса не нужны: интерфейс уже включён в архив.
Первый запуск скачает Python и зависимости через uv; требуется интернет.
Оставьте терминал открытым. Для остановки нажмите Ctrl+C.
Если порт 8000 занят, откройте командную строку в распакованной папке:
  "Start Freedom CQA.cmd" --port 8001
В PowerShell: & "./Start Freedom CQA.cmd" --port 8001

Реальная оценка использует ваш ключ API и оплачивается с вашего аккаунта.
Учебный разбор, импорт данных и чтение сохранённых оценок не вызывают модель.
Ключ сохраняется только в локальном .env. Не пересылайте эту папку после настройки.
Результаты сохраняются в data/runtime внутри распакованной папки.
Не удаляйте её, если хотите сохранить результаты.

Подробный маршрут проверки: docs/JUDGE_QUICKSTART.md.
"""


def package_files(root: Path) -> dict[str, Path]:
    root = root.resolve()
    paths = {name: root / name for name in REQUIRED_FILES}
    for folder in ("backend", "cqa"):
        for path in sorted((root / folder).glob("*.py")):
            paths[path.relative_to(root).as_posix()] = path
    for path in sorted((root / "frontend/dist").rglob("*")):
        if path.is_file() and path.suffix.lower() in ASSET_EXTENSIONS:
            paths[path.relative_to(root).as_posix()] = path
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE", "NOTICE.md"):
        if (root / name).is_file():
            paths[name] = root / name
    for name in ("backend/app.py", "cqa/settings.py", "cqa/__init__.py"):
        if name not in paths:
            raise ValueError(f"В пакете отсутствует обязательный модуль: {name}")
    for name, path in paths.items():
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Нет обычного файла внутри проекта: {name}")
    index = paths["frontend/dist/index.html"].read_text(encoding="utf-8")
    assets = re.findall(r'''(?:src|href)=["'](/assets/[^"']+)["']''', index)
    if not any(asset.endswith(".js") for asset in assets):
        raise ValueError("Нет собранного интерфейса. Сначала выполните pnpm run build в frontend.")
    for asset in assets:
        if f"frontend/dist{asset}" not in paths:
            raise ValueError(f"Не найден файл собранного интерфейса: {asset}")
    return paths


def build_package(root: Path, output: Path) -> dict:
    files = package_files(root)
    payload = {name: path.read_bytes() for name, path in files.items()}
    # CMD parses UTF-8 batch files unreliably with bare LF, including after a Linux checkout.
    for name, content in payload.items():
        if name.lower().endswith(".cmd"):
            payload[name] = content.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    payload["НАЧНИТЕ ЗДЕСЬ.txt"] = PACKAGE_GUIDE.encode("utf-8")
    manifest = {"format_version": 1, "package_type": "freedom-cqa-judge", "prebuilt_frontend": True,
                "files": {name: hashlib.sha256(content).hexdigest() for name, content in sorted(payload.items())}}
    payload[PACKAGE_MARKER] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Never replace an existing delivery accidentally. Give each new candidate its own filename.
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(payload.items()):
            archive.writestr(f"{PACKAGE_ROOT}/{name}", content)
    return {"path": str(output), "file_count": len(payload), "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description="Подготовить ZIP для судей из уже собранного интерфейса.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="Новый ZIP; по умолчанию dist/release/freedom-cqa-judge.zip")
    args = parser.parse_args()
    try:
        result = build_package(args.root, args.output or args.root / "dist/release/freedom-cqa-judge.zip")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Пакет не создан: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

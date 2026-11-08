"""Start one local backend from an extracted package and open its ready UI."""

import argparse
import hashlib
import http.client
import json
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def verify_package(root: Path) -> None:
    manifest_path = root / "judge-package.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("format_version") != 1 or manifest.get("package_type") != "freedom-cqa-judge"
            or manifest.get("prebuilt_frontend") is not True):
        raise ValueError("Неизвестный формат пакета. Распакуйте полный ZIP заново.")
    files = manifest.get("files", {})
    required = {"frontend/dist/index.html", "backend/app.py", "cqa/settings.py",
                "checklists/freedom-reviewed-016.json", "checklists/freedom-reviewed-017.json",
                "examples/judge-example.json"}
    if not required.issubset(files):
        raise ValueError("В пакете не хватает обязательных файлов. Распакуйте полный ZIP заново.")
    for name, expected in files.items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f"В пакете отсутствует файл: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Файл пакета изменён или повреждён: {name}. Распакуйте исходный ZIP заново.")


def ensure_settings(root: Path) -> None:
    target = root / ".env"
    if target.exists():
        if not target.is_file():
            raise ValueError(".env существует, но это не файл.")
        return
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write((root / ".env.example").read_bytes())


def require_free_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise ValueError(f"Порт {port} занят. Закройте прежний запуск или добавьте --port 8001.") from error


def acquire_workspace_lock(root: Path):
    """Keep only one packaged worker attached to this folder, even on different ports."""
    runtime = root / "data/runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    stream = (runtime / ".judge-launch.lock").open("a+b")
    try:
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        stream.close()
        raise ValueError("Эта папка уже открыта в другом запуске. Используйте открытое окно или сначала закройте его.") from error
    return stream


def wait_until_ready(process, port: int, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Сервер завершился до запуска интерфейса. Прочитайте сообщение выше.")
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
        try:
            connection.request("GET", "/api/config")
            response = connection.getresponse()
            response.read()
            if response.status == 200 and process.poll() is None:
                return
        except (OSError, http.client.HTTPException):
            pass
        finally:
            connection.close()
        time.sleep(0.2)
    raise RuntimeError("Сервер не ответил за минуту. Прочитайте сообщения в этом окне.")


def port_number(value: str) -> int:
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Порт должен быть целым числом от 1 до 65535.") from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Порт должен быть целым числом от 1 до 65535.")
    return port


def main() -> int:
    # Windows redirects Python pipes using a legacy code page unless explicitly configured.
    # Set child defaults as well: this route also runs directly from PowerShell or sh.
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    for stream in (sys.stdout, sys.stderr):
        if callable(getattr(stream, "reconfigure", None)):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Открыть подготовленную версию Freedom CQA.")
    parser.add_argument("--port", type=port_number, default=8000)
    parser.add_argument("--no-browser", action="store_true", help="Не открывать браузер автоматически")
    parser.add_argument("--no-prompt", action="store_true", help="Не запрашивать ключ в терминале")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    process = None
    workspace_lock = None
    try:
        verify_package(root)
        require_free_port(args.port)
        workspace_lock = acquire_workspace_lock(root)
        ensure_settings(root)
        from configure_judge import configure_key
        configure_key(root, interactive=sys.stdin.isatty() and not args.no_prompt)
        # One process owns the local worker and persistent databases; no reload or extra workers.
        process = subprocess.Popen([sys.executable, "-m", "backend.app", "--port", str(args.port)], cwd=root)
        wait_until_ready(process, args.port)
        url = f"http://127.0.0.1:{args.port}"
        print(f"Приложение готово: {url}\nНе закрывайте это окно. Для остановки нажмите Ctrl+C.", flush=True)
        if not args.no_browser:
            try:
                if not webbrowser.open(url):
                    print("Браузер не открылся автоматически. Откройте адрес выше вручную.")
            except webbrowser.Error:
                print("Браузер не открылся автоматически. Откройте адрес выше вручную.")
        return process.wait()
    except KeyboardInterrupt:
        print("\nОстанавливаем приложение. Сохранённые результаты остаются в data/runtime.")
        # The foreground child receives the same Ctrl+C. Give its shutdown hooks time to finish.
        if process is not None and process.poll() is None:
            try:
                process.wait(timeout=15)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                pass
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Не удалось запустить приложение: {error}", file=sys.stderr)
        return 1
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if workspace_lock is not None:
            workspace_lock.close()


if __name__ == "__main__":
    raise SystemExit(main())

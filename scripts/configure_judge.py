"""Optional masked API-key setup for an extracted judge package."""

import getpass
import os
from pathlib import Path

from dotenv import dotenv_values, set_key


def key_is_configured(root: Path, environ=None) -> bool:
    environ = os.environ if environ is None else environ
    values = {**dotenv_values(root / ".env"), **environ}
    value = (values.get("OPENAI_API_KEY") or "").strip()
    return bool(value and value not in {"your_key_here", "YOUR_API_KEY"})


def configure_key(root: Path, *, interactive: bool, prompt=getpass.getpass, environ=None) -> bool:
    if key_is_configured(root, environ):
        print("Ключ API уже настроен. Его доступ и баланс будут проверены при запуске оценки.")
        return True
    if not interactive:
        print("Ключ API не задан. Готовый учебный разбор доступен без ключа; для своих данных настройте OPENAI_API_KEY в .env.")
        return False
    print("Готовый учебный разбор доступен без ключа. Для оценки своих данных нужен ключ OpenAI API; он сохранится только в локальном .env.")
    try:
        value = prompt("Ключ OpenAI API (Enter — пропустить): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nВвод пропущен. В приложении нажмите «Открыть пример», чтобы посмотреть готовый разбор.")
        return False
    if not value:
        print("Ввод пропущен. Нажмите «Открыть пример»: готовый разбор доступен бесплатно, без обращения к модели.")
        return False
    if any(character.isspace() for character in value) or "\x00" in value:
        raise ValueError("Ключ не сохранён: он должен занимать одну строку без пробелов.")
    set_key(str(root / ".env"), "OPENAI_API_KEY", value, quote_mode="always")
    print("Ключ сохранён. Оценки используют ваш аккаунт и заданные ограничения расходов.")
    return True

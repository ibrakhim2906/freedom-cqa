#!/usr/bin/env sh
set -eu
cd -- "$(dirname -- "$0")"
if [ ! -f judge-package.json ]; then
    printf '%s\n' 'Этот запуск предназначен для готового ZIP-пакета. Для исходников используйте sh scripts/start-local.sh.' >&2
    exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' 'Сначала установите uv: https://docs.astral.sh/uv/getting-started/installation/' >&2
    exit 1
fi
printf '%s\n' 'Подготавливаем Python и зависимости. Первый запуск требует интернета и может занять несколько минут.'
exec uv run --locked --no-dev python scripts/launch_judge.py "$@"

#!/usr/bin/env sh
set -eu

fail() { printf '%s\n' "Не удалось запустить: $*" >&2; exit 1; }
task_repository=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
task_port=8000
task_port_set=false
task_check=false
for task_argument in "$@"; do
    case "$task_argument" in
        --check|--check-only) task_check=true ;;
        -h|--help) printf '%s\n' 'Запуск: sh scripts/start-local.sh [ПОРТ] [--check]' 'Порт по умолчанию: 8000. --check только проверяет программы, без установки, запуска и чтения .env.'; exit 0 ;;
        *[!0-9]*|'') fail 'Укажите порт от 1 до 65535 и/или --check. Пример: sh scripts/start-local.sh 8001 --check' ;;
        *) if [ "$task_port_set" = true ]; then fail 'Порт можно указать только один раз.'; fi; task_port=$task_argument; task_port_set=true ;;
    esac
done
[ "${#task_port}" -le 5 ] && [ "$task_port" -ge 1 ] && [ "$task_port" -le 65535 ] || fail 'Порт должен быть целым числом от 1 до 65535.'
cd "$task_repository"

printf '%s\n' 'Проверяем готовность к запуску...'
task_packaged=false
task_required='pyproject.toml uv.lock .env.example'
if [ -f judge-package.json ]; then
    grep -q '"package_type"[[:space:]]*:[[:space:]]*"freedom-cqa-judge"' judge-package.json && grep -q '"prebuilt_frontend"[[:space:]]*:[[:space:]]*true' judge-package.json || fail 'Неверный пакет. Распакуйте исходный ZIP заново.'
    task_packaged=true
    task_required="$task_required frontend/dist/index.html scripts/launch_judge.py scripts/configure_judge.py"
else task_required="$task_required frontend/package.json frontend/pnpm-lock.yaml"; fi
for task_file in $task_required; do
    [ -f "$task_file" ] || fail "Отсутствует $task_file. Нужна полная копия проекта."
done
task_problems=0
task_uv_version=$(uv --version 2>/dev/null) || task_uv_version=''
case "$task_uv_version" in
    'uv '[0-9]*.[0-9]*.[0-9]*) printf '  %s\n' "$task_uv_version" ;;
    *) printf '%s\n' '  Как исправить: Установите uv по инструкции https://docs.astral.sh/uv/getting-started/installation/ (для Homebrew: brew install uv). Затем заново откройте терминал.'; task_problems=$((task_problems + 1)) ;;
esac
if [ "$task_packaged" = false ]; then
task_node_version=$(node --version 2>/dev/null) || task_node_version=''
task_node_major=${task_node_version#v}
task_node_major=${task_node_major%%.*}
case "$task_node_major" in
    ''|*[!0-9]*) task_node_major=0 ;;
esac
if [ "$task_node_major" -lt 24 ]; then
    printf '%s\n' '  Как исправить: Для исходников установите Node.js 24 LTS: https://nodejs.org/en/download (24 или новее), затем заново откройте терминал.'
    task_problems=$((task_problems + 1))
else printf '  Node.js %s\n' "$task_node_version"; fi
# Keep version inspection offline, even when pnpm is a Corepack shim.
task_pnpm_version=$(COREPACK_ENABLE_NETWORK=0 pnpm --manage-package-manager-versions=false --version 2>/dev/null) || task_pnpm_version=''
if [ "$task_pnpm_version" != '11.25.0' ]; then
    printf '  Как исправить: Нужен pnpm 11.25.0 (найден: %s). После Node.js выполните: npm install -g pnpm@11.25.0. Инструкция: https://pnpm.io/installation\n' "${task_pnpm_version:-не найден}"
    task_problems=$((task_problems + 1))
else printf '  pnpm %s\n' "$task_pnpm_version"; fi
else printf '%s\n' '  Интерфейс уже собран. Node.js и pnpm не требуются.'; fi
[ "$task_problems" -eq 0 ] || fail 'Проверка не пройдена. Установите недостающие программы, заново откройте терминал и повторите запуск.'
printf '%s\n' '  uv подберёт Python 3.12 или новее; отдельно устанавливать Python не нужно.'
if [ "$task_check" = true ]; then
    printf 'Проверка пройдена для порта %s. Установка, сборка и запуск не выполнялись; .env не читался и не менялся.\n' "$task_port"
    printf '%s\n' 'Для запуска: sh scripts/start-local.sh. Доступ API, сеть и свободный порт проверяются при использовании.'
    exit 0
fi
if [ "$task_packaged" = true ]; then
    printf '%s\n' 'Подготавливаем Python и зависимости. Браузер откроется, когда приложение будет готово.'
    exec uv run --locked --no-dev python scripts/launch_judge.py --port "$task_port"
fi

printf '%s\n' '[1/4] Подготавливаем локальные настройки...'
if [ ! -e .env ]; then
    (umask 077; set -C; cat .env.example > .env) || fail 'Не удалось создать .env из .env.example.'
    printf '%s\n' 'Создан .env. Для новой платной оценки укажите в нём OPENAI_API_KEY. Интерфейс откроется и без ключа.'
elif [ ! -f .env ]; then fail '.env существует, но это не файл.'; fi
printf '%s\n' '[2/4] Устанавливаем зависимости Python по lock-файлу (при необходимости uv скачает Python)...'
uv sync --locked --no-dev || fail 'Не удалось подготовить Python. Проверьте ошибку выше и соединение. Если lock-файл не поддерживается, обновите uv по инструкции установки.'
uv run --no-sync --no-dev python -c '
from cqa.settings import Settings
settings = Settings.load()
try:
    settings.require_key()
except ValueError:
    print("Ключ API не задан. Интерфейс откроется. Перед новой оценкой добавьте OPENAI_API_KEY в .env и перезапустите приложение.")
else:
    print("Ключ API настроен. Новая оценка оплачивается с вашего аккаунта в пределах заданных ограничений расходов.")
' || fail 'Не удалось загрузить настройки. Сверьте сообщение выше с .env.example.'

printf '%s\n' '[3/4] Устанавливаем зависимости и собираем интерфейс...'
(
    cd frontend
    pnpm install --frozen-lockfile || fail 'Не удалось установить зависимости интерфейса. Проверьте сообщение выше и доступ к реестру пакетов.'
    pnpm run build || fail 'Не удалось собрать интерфейс. Сохраните сообщение выше для разбора проблемы.'
) || exit 1
printf '[4/4] Запускаем http://127.0.0.1:%s — откройте адрес после сообщения о готовности сервера.\n' "$task_port"
printf '%s\n' 'Для остановки нажмите Ctrl+C. Если порт занят: sh scripts/start-local.sh 8001'
uv run --no-sync --no-dev cqa-serve --port "$task_port" || fail 'Сервер завершился с ошибкой. Прочитайте сообщение выше; если адрес занят, выберите другой порт.'

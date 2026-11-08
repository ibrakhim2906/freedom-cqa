#!/usr/bin/env sh
set -eu

task_repository=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
task_port=${1:-8000}
cd "$task_repository"

uv sync --locked --no-dev
(
    cd frontend
    pnpm install --frozen-lockfile
    pnpm run build
)
exec uv run --locked --no-dev cqa-serve --port "$task_port"

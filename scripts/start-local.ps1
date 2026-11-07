param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$taskRepository = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $taskRepository
try {
    uv sync --dev
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
    Push-Location -LiteralPath (Join-Path $taskRepository 'frontend')
    try {
        pnpm install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed' }
        pnpm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    } finally { Pop-Location }
    uv run cqa-serve --port $Port
} finally { Pop-Location }

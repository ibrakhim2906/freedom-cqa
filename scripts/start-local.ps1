param(
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$taskRepository = Split-Path -Parent $PSScriptRoot
$taskPnpm = if (Get-Command pnpm.cmd -ErrorAction SilentlyContinue) { 'pnpm.cmd' } else { 'pnpm' }

function Get-ToolVersion([string]$Name, [string[]]$VersionArguments = @('--version')) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) { return '' }
    try {
        $taskVersion = (& $Name @VersionArguments 2>$null | Out-String).Trim()
        if ($LASTEXITCODE -eq 0) { return $taskVersion }
    } catch { }
    return ''
}

Push-Location -LiteralPath $taskRepository
try {
    Write-Host 'Проверяем готовность к запуску...'
    $taskPackaged = Test-Path -LiteralPath 'judge-package.json' -PathType Leaf
    $taskRequired = @('pyproject.toml', 'uv.lock', '.env.example')
    if ($taskPackaged) {
        $taskManifest = Get-Content -Raw -LiteralPath 'judge-package.json' | ConvertFrom-Json
        if ($taskManifest.package_type -ne 'freedom-cqa-judge' -or $taskManifest.prebuilt_frontend -ne $true) { throw 'Неверный пакет. Распакуйте исходный ZIP заново.' }
        $taskRequired += @('frontend/dist/index.html', 'scripts/launch_judge.py', 'scripts/configure_judge.py')
    } else { $taskRequired += @('frontend/package.json', 'frontend/pnpm-lock.yaml') }
    foreach ($taskFile in $taskRequired) {
        if (-not (Test-Path -LiteralPath $taskFile -PathType Leaf)) { throw "Отсутствует $taskFile. Нужна полная копия проекта." }
    }
    $taskProblems = [System.Collections.Generic.List[string]]::new()
    $taskUvVersion = Get-ToolVersion 'uv'
    if ($taskUvVersion -notmatch '^uv \d+\.\d+\.\d+') {
        $taskProblems.Add('uv не найден или не запускается. Установите: winget install --id astral-sh.uv -e. Инструкция: https://docs.astral.sh/uv/getting-started/installation/')
    } else { Write-Host "  $taskUvVersion" }
    if (-not $taskPackaged) {
    $taskNodeVersion = Get-ToolVersion 'node'
    if ($taskNodeVersion -notmatch '^v(\d+)\.\d+\.\d+$' -or [int]$Matches[1] -lt 24) {
        $taskProblems.Add('Для исходников нужен Node.js 24 или новее. Установите Node.js 24 LTS: https://nodejs.org/en/download и заново откройте терминал.')
    } else { Write-Host "  Node.js $taskNodeVersion" }
    # Version inspection must not make Corepack or pnpm download another package manager.
    $taskCorepackNetwork = [Environment]::GetEnvironmentVariable('COREPACK_ENABLE_NETWORK', 'Process')
    try {
        $env:COREPACK_ENABLE_NETWORK = '0'
        $taskPnpmVersion = Get-ToolVersion $taskPnpm @('--manage-package-manager-versions=false', '--version')
    } finally { [Environment]::SetEnvironmentVariable('COREPACK_ENABLE_NETWORK', $taskCorepackNetwork, 'Process') }
    if ($taskPnpmVersion -ne '11.25.0') {
        $taskProblems.Add("Нужен pnpm 11.25.0 (найден: $(if ($taskPnpmVersion) { $taskPnpmVersion } else { 'не найден' })). После установки Node.js выполните: npm install -g pnpm@11.25.0. Инструкция: https://pnpm.io/installation")
    } else { Write-Host "  pnpm $taskPnpmVersion" }
    } else { Write-Host '  Интерфейс уже собран. Node.js и pnpm не требуются.' }
    if ($taskProblems.Count) {
        foreach ($taskProblem in $taskProblems) { Write-Host "  Как исправить: $taskProblem" }
        throw 'Проверка не пройдена. Установите недостающие программы, заново откройте терминал и повторите запуск.'
    }
    Write-Host '  uv подберёт Python 3.12 или новее; отдельно устанавливать Python не нужно.'
    if ($CheckOnly) {
        Write-Host "Проверка пройдена для порта $Port. Установка, сборка и запуск не выполнялись; .env не читался и не менялся."
        Write-Host 'Для запуска: ./scripts/start-local.ps1. Доступ API, сеть и свободный порт проверяются при использовании.'
        return
    }
    if ($taskPackaged) {
        Write-Host 'Подготавливаем Python и зависимости. Браузер откроется, когда приложение будет готово.'
        uv run --locked --no-dev python scripts/launch_judge.py --port $Port
        if ($LASTEXITCODE -ne 0) { throw 'Запуск готового пакета завершился с ошибкой. Прочитайте сообщение выше.' }
        return
    }

    Write-Host '[1/4] Подготавливаем локальные настройки...'
    if (-not (Test-Path -LiteralPath '.env')) {
        [IO.File]::Copy((Join-Path $taskRepository '.env.example'), (Join-Path $taskRepository '.env'), $false)
        Write-Host 'Создан .env. Для новой платной оценки укажите в нём OPENAI_API_KEY. Интерфейс откроется и без ключа.'
    } elseif (-not (Test-Path -LiteralPath '.env' -PathType Leaf)) { throw '.env существует, но это не файл.' }
    Write-Host '[2/4] Устанавливаем зависимости Python по lock-файлу (при необходимости uv скачает Python)...'
    uv sync --locked --no-dev
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось подготовить Python. Проверьте ошибку выше и соединение. Если lock-файл не поддерживается, обновите uv по инструкции установки.' }
    $taskKeyCheck = @'
from cqa.settings import Settings
settings = Settings.load()
try:
    settings.require_key()
except ValueError:
    print('Ключ API не задан. Интерфейс откроется. Перед новой оценкой добавьте OPENAI_API_KEY в .env и перезапустите приложение.')
else:
    print('Ключ API настроен. Новая оценка оплачивается с вашего аккаунта в пределах заданных ограничений расходов.')
'@
    uv run --no-sync --no-dev python -c $taskKeyCheck
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось загрузить настройки. Сверьте сообщение выше с .env.example.' }

    Write-Host '[3/4] Устанавливаем зависимости и собираем интерфейс...'
    Push-Location -LiteralPath (Join-Path $taskRepository 'frontend')
    try {
        & $taskPnpm install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить зависимости интерфейса. Проверьте сообщение выше и доступ к реестру пакетов.' }
        & $taskPnpm run build
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось собрать интерфейс. Сохраните сообщение выше для разбора проблемы.' }
    } finally { Pop-Location }
    Write-Host "[4/4] Запускаем http://127.0.0.1:$Port — откройте адрес после сообщения о готовности сервера."
    Write-Host 'Для остановки нажмите Ctrl+C. Если порт занят, повторите с -Port 8001.'
    uv run --no-sync --no-dev cqa-serve --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Сервер завершился с ошибкой. Прочитайте сообщение выше; если адрес занят, используйте -Port 8001.' }
} catch {
    Write-Host "Не удалось запустить: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally { Pop-Location }

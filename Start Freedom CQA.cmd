@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
pushd "%~dp0"
if not exist "judge-package.json" (
  echo Этот запуск предназначен для готового ZIP-пакета. Для исходников используйте scripts\start-local.ps1.
  pause
  popd
  exit /b 1
)
where uv >nul 2>nul
if errorlevel 1 (
  echo Сначала установите uv: winget install --id astral-sh.uv -e
  echo Инструкция: https://docs.astral.sh/uv/getting-started/installation/
  echo Затем заново откройте этот файл.
  pause
  popd
  exit /b 1
)
echo Подготавливаем Python и зависимости. Первый запуск требует интернета и может занять несколько минут.
call uv run --locked --no-dev python scripts/launch_judge.py %*
set "task_exit=%errorlevel%"
if not "%task_exit%"=="0" (
  echo Не удалось запустить приложение. Прочитайте сообщения выше.
  pause
)
popd
exit /b %task_exit%

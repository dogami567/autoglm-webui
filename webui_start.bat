@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"

REM Force UTF-8 output to avoid UnicodeEncodeError in some Windows consoles.
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

REM Add local ADB to PATH if present (prefer repo/platform-tools, fallback to tools/platform-tools).
set "LOCAL_ADB_DIR="
if exist "%~dp0platform-tools\\adb.exe" set "LOCAL_ADB_DIR=%~dp0platform-tools"
if exist "%~dp0tools\\platform-tools\\adb.exe" set "LOCAL_ADB_DIR=%~dp0tools\\platform-tools"
if not "%LOCAL_ADB_DIR%"=="" set "PATH=%LOCAL_ADB_DIR%;%PATH%"

REM Ensure venv exists.
if not exist ".venv\\Scripts\\python.exe" (
  echo [ERROR] .venv not found. Run setup.bat first.
  exit /b 1
)

REM Load config (env.bat is git-ignored).
if exist "env.bat" (
  call "env.bat"
)

REM Defaults (override with WEBUI_HOST/WEBUI_PORT).
if "%WEBUI_HOST%"=="" set "WEBUI_HOST=127.0.0.1"
if "%WEBUI_PORT%"=="" set "WEBUI_PORT=7860"

echo ========================================
echo   Open-AutoGLM WebUI
echo ========================================
echo URL: http://%WEBUI_HOST%:%WEBUI_PORT%/
echo Press CTRL+C to stop.
echo ========================================
echo.

".venv\\Scripts\\python.exe" -m uvicorn webui.server:app --host %WEBUI_HOST% --port %WEBUI_PORT%

endlocal

@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo ========================================
echo   Open-AutoGLM Environment Check
echo ========================================
echo.

REM Add local ADB to PATH if present (prefer repo/platform-tools, fallback to tools/platform-tools).
set "LOCAL_ADB_DIR="
if exist "%~dp0platform-tools\\adb.exe" set "LOCAL_ADB_DIR=%~dp0platform-tools"
if exist "%~dp0tools\\platform-tools\\adb.exe" set "LOCAL_ADB_DIR=%~dp0tools\\platform-tools"
if not "%LOCAL_ADB_DIR%"=="" set "PATH=%LOCAL_ADB_DIR%;%PATH%"

echo [1/3] Python...
.venv\\Scripts\\python.exe --version
if errorlevel 1 (
  echo [ERROR] Python/venv not found. Run setup.bat
  goto :end
)
echo [OK] Python
echo.

echo [2/3] Dependencies...
.venv\\Scripts\\python.exe -c "import openai; import PIL; import phone_agent; print('openai:', openai.__version__); print('phone_agent:', phone_agent.__version__)"
if errorlevel 1 (
  echo [ERROR] Dependencies missing. Run setup.bat
  goto :end
)
echo [OK] Dependencies
echo.

echo [3/3] ADB...
where adb >nul 2>&1
if errorlevel 1 (
  echo [WARN] ADB not found on PATH.
  echo        Expected: %~dp0platform-tools\\adb.exe (or tools\\platform-tools\\adb.exe)
) else (
  adb version
  echo [OK] ADB
)
echo.

echo ========================================
echo   Done
echo ========================================
echo.
echo Usage:
echo   run.bat --list-apps
echo   run.bat --list-devices
echo   run.bat "your task"
echo.

:end
pause
endlocal

@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist ".venv\\Scripts\\python.exe" (
  echo [ERROR] .venv not found. Run setup.bat first.
  exit /b 1
)

set "LOCAL_ADB_DIR="
if exist "%~dp0platform-tools\\adb.exe" set "LOCAL_ADB_DIR=%~dp0platform-tools"
if exist "%~dp0tools\\platform-tools\\adb.exe" set "LOCAL_ADB_DIR=%~dp0tools\\platform-tools"
if not "%LOCAL_ADB_DIR%"=="" set "PATH=%LOCAL_ADB_DIR%;%PATH%"

if exist "env.bat" (
  call "env.bat"
) else (
  echo [WARN] env.bat not found. You can copy env.example.bat to env.bat and configure it.
)

if "%PHONE_AGENT_BASE_URL%"=="" set "PHONE_AGENT_BASE_URL=http://localhost:8000/v1"
if "%PHONE_AGENT_MODEL%"=="" set "PHONE_AGENT_MODEL=autoglm-phone-9b"
if "%PHONE_AGENT_API_KEY%"=="" set "PHONE_AGENT_API_KEY=EMPTY"
if "%PHONE_AGENT_DEVICE_TYPE%"=="" set "PHONE_AGENT_DEVICE_TYPE=adb"
if "%PHONE_AGENT_LANG%"=="" set "PHONE_AGENT_LANG=cn"
if "%PHONE_AGENT_MAX_STEPS%"=="" set "PHONE_AGENT_MAX_STEPS=100"

echo.
echo Starting Phone Agent...
echo - PHONE_AGENT_BASE_URL=%PHONE_AGENT_BASE_URL%
echo - PHONE_AGENT_MODEL=%PHONE_AGENT_MODEL%
echo - PHONE_AGENT_DEVICE_TYPE=%PHONE_AGENT_DEVICE_TYPE%
echo - PHONE_AGENT_DEVICE_ID=%PHONE_AGENT_DEVICE_ID%
echo.

if "%~1"=="" (
  ".venv\\Scripts\\python.exe" main.py
) else (
  ".venv\\Scripts\\python.exe" main.py %*
)

endlocal

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
)

echo Listing connected devices...
".venv\\Scripts\\python.exe" main.py --list-devices

endlocal

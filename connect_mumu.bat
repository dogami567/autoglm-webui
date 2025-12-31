@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"

REM Add local ADB to PATH (prefer repo/platform-tools, fallback to tools/platform-tools).
set "LOCAL_ADB_DIR="
if exist "%~dp0platform-tools\\adb.exe" set "LOCAL_ADB_DIR=%~dp0platform-tools"
if exist "%~dp0tools\\platform-tools\\adb.exe" set "LOCAL_ADB_DIR=%~dp0tools\\platform-tools"
if not "%LOCAL_ADB_DIR%"=="" set "PATH=%LOCAL_ADB_DIR%;%PATH%"

echo Checking ADB...
adb version
if errorlevel 1 (
  echo [ERROR] adb not found on PATH.
  echo        Expected: %~dp0platform-tools\\adb.exe (or tools\\platform-tools\\adb.exe)
  pause
  exit /b 1
)

echo.
echo Connecting MuMu (127.0.0.1:16384)...
adb connect 127.0.0.1:16384

echo.
echo Devices:
adb devices -l

pause
endlocal


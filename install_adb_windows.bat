@echo off
setlocal EnableExtensions

cd /d "%~dp0"

where adb >nul 2>nul
if %errorlevel%==0 (
  echo ADB is already available on PATH.
  exit /b 0
)

set "TOOLS_DIR=%~dp0tools"
set "PT_DIR=%TOOLS_DIR%\\platform-tools"
set "ZIP_PATH=%TOOLS_DIR%\\platform-tools-latest-windows.zip"
set "URL=https://dl.google.com/android/repository/platform-tools-latest-windows.zip"

if exist "%PT_DIR%\\adb.exe" (
  echo ADB is already downloaded: %PT_DIR%
  echo Note: start.bat will auto-add it to PATH for the current session.
  exit /b 0
)

if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

echo Downloading Android platform-tools...
echo   %URL%
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%URL%' -OutFile '%ZIP_PATH%'"
if errorlevel 1 (
  echo [ERROR] Failed to download platform-tools.
  exit /b 1
)

echo Extracting to: %TOOLS_DIR%
powershell -NoProfile -Command "Expand-Archive -Force -Path '%ZIP_PATH%' -DestinationPath '%TOOLS_DIR%'"
if errorlevel 1 (
  echo [ERROR] Failed to extract platform-tools.
  exit /b 1
)

if not exist "%PT_DIR%\\adb.exe" (
  echo [ERROR] adb.exe not found after extraction.
  exit /b 1
)

echo OK. ADB installed locally at:
echo   %PT_DIR%
echo Next: run start.bat (it will auto-add platform-tools to PATH).

endlocal


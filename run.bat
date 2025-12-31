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
) else (
  if exist "env.example.bat" (
    copy /y "env.example.bat" "env.bat" >nul
    echo Created env.bat. Please edit it and rerun run.bat.
    exit /b 1
  )
)

REM Defaults.
if "%PHONE_AGENT_BASE_URL%"=="" set "PHONE_AGENT_BASE_URL=https://open.bigmodel.cn/api/paas/v4"
if "%PHONE_AGENT_MODEL%"=="" set "PHONE_AGENT_MODEL=autoglm-phone"
if "%PHONE_AGENT_API_KEY%"=="" set "PHONE_AGENT_API_KEY=EMPTY"
if "%PHONE_AGENT_DEVICE_TYPE%"=="" set "PHONE_AGENT_DEVICE_TYPE=adb"
if "%PHONE_AGENT_LANG%"=="" set "PHONE_AGENT_LANG=cn"
if "%PHONE_AGENT_MAX_STEPS%"=="" set "PHONE_AGENT_MAX_STEPS=100"

REM ADB: auto-connect if device id looks like IP:PORT.
if /i "%PHONE_AGENT_DEVICE_TYPE%"=="adb" (
  if not "%PHONE_AGENT_DEVICE_ID%"=="" (
    echo %PHONE_AGENT_DEVICE_ID%| findstr /r "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*:[0-9][0-9]*$" >nul
    if not errorlevel 1 adb connect %PHONE_AGENT_DEVICE_ID% >nul 2>&1
  ) else (
    REM Try MuMu default.
    adb connect 127.0.0.1:16384 >nul 2>&1
    for /f "skip=1 tokens=1,2" %%A in ('adb devices') do (
      if "%%A"=="127.0.0.1:16384" if "%%B"=="device" set "PHONE_AGENT_DEVICE_ID=127.0.0.1:16384"
    )
  )
)

echo ========================================
echo   Open-AutoGLM config
echo ========================================
echo BASE_URL=%PHONE_AGENT_BASE_URL%
echo MODEL=%PHONE_AGENT_MODEL%
echo DEVICE_TYPE=%PHONE_AGENT_DEVICE_TYPE%
echo DEVICE_ID=%PHONE_AGENT_DEVICE_ID%
echo LANG=%PHONE_AGENT_LANG%
echo MAX_STEPS=%PHONE_AGENT_MAX_STEPS%
echo ========================================
echo.

REM Prompt API key for hosted services unless this is a utility command.
set "ARGS=%*"
set "SKIP_KEY_PROMPT=0"
echo %ARGS%| findstr /i /c:"--help" /c:"-h" /c:"--list-devices" /c:"--list-apps" /c:"--wda-status" /c:"--pair" >nul
if not errorlevel 1 set "SKIP_KEY_PROMPT=1"

if /i "%PHONE_AGENT_API_KEY%"=="your-bigmodel-api-key" set "PHONE_AGENT_API_KEY=EMPTY"
if /i "%PHONE_AGENT_API_KEY%"=="your-zai-api-key" set "PHONE_AGENT_API_KEY=EMPTY"
if /i "%PHONE_AGENT_API_KEY%"=="your-api-key-here" set "PHONE_AGENT_API_KEY=EMPTY"

echo %PHONE_AGENT_BASE_URL%| findstr /i "bigmodel.cn api.z.ai novita.ai parasail.io" >nul
if not errorlevel 1 (
  if /i "%PHONE_AGENT_API_KEY%"=="EMPTY" if "%SKIP_KEY_PROMPT%"=="0" (
    echo [INFO] Hosted model service detected, API key is required.
    set /p PHONE_AGENT_API_KEY=Enter PHONE_AGENT_API_KEY:
    echo.
  )
)

".venv\\Scripts\\python.exe" main.py %*

endlocal

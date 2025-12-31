@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo [1/4] Checking Python version...
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.10+ is required. Current:
  python --version
  exit /b 1
)

echo [2/4] Creating venv (.venv)...
if not exist ".venv\\Scripts\\python.exe" (
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv.
    exit /b 1
  )
)

echo [3/4] Installing dependencies...
".venv\\Scripts\\python.exe" -m pip install -U pip setuptools wheel
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
".venv\\Scripts\\python.exe" -m pip install -e .
if errorlevel 1 exit /b 1

echo [4/4] Preparing env.bat (optional)...
if not exist "env.bat" (
  copy /y "env.example.bat" "env.bat" >nul
  echo Created env.bat. Please edit it and fill in API key / base-url before running start.bat.
)

echo.
echo OK. Next: run start.bat
endlocal


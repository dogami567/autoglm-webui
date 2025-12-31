@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not exist "docker.model.env" (
  copy /y "docker.model.env.example" "docker.model.env" >nul
  echo Created docker.model.env. Please edit it before running again.
  exit /b 1
)

REM Prefer storing HF cache on host disk (avoid filling Docker Desktop disk)
set "HF_CACHE_DIR="
for /f "tokens=1,* delims==" %%A in ('findstr /b "HF_CACHE_DIR=" docker.model.env 2^>nul') do set "HF_CACHE_DIR=%%B"
if "%HF_CACHE_DIR%"=="" set "HF_CACHE_DIR=%~dp0.cache\\huggingface"
if not exist "%HF_CACHE_DIR%" mkdir "%HF_CACHE_DIR%" >nul 2>&1

docker compose -p autoglm-model --env-file docker.model.env -f docker/compose.model.vllm.yml up -d
echo Model service should be available at: http://localhost:8000/v1

endlocal

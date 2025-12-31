@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not exist "docker.env" (
  copy /y "docker.env.example" "docker.env" >nul
  echo Created docker.env. Please edit it before running again.
  exit /b 1
)

docker compose -p autoglm-agent --env-file docker.env -f docker/compose.agent.yml run --rm --build agent %*

endlocal

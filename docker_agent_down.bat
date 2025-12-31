@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if exist "docker.env" (
  docker compose -p autoglm-agent --env-file docker.env -f docker/compose.agent.yml down
) else (
  docker compose -p autoglm-agent -f docker/compose.agent.yml down
)

endlocal

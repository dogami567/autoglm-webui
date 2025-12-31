@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if exist "docker.model.env" (
  docker compose -p autoglm-model --env-file docker.model.env -f docker/compose.model.vllm.yml down
) else (
  docker compose -p autoglm-model -f docker/compose.model.vllm.yml down
)

endlocal

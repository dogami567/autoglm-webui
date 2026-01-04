#!/bin/bash

set -e

cd "$(dirname "$0")"

# Force UTF-8 output
export PYTHONIOENCODING="utf-8"
export LC_ALL="en_US.UTF-8"
export LANG="en_US.UTF-8"

# Ensure venv exists
if [ ! -f ".venv/bin/python" ]; then
  echo "[ERROR] .venv not found. Run ./setup.sh first."
  exit 1
fi

# Load config (env.sh is git-ignored)
if [ -f "env.sh" ]; then
  source env.sh
fi

# Defaults (override with WEBUI_HOST/WEBUI_PORT)
: ${WEBUI_HOST:="127.0.0.1"}
: ${WEBUI_PORT:="7860"}

echo "========================================"
echo "   Open-AutoGLM WebUI (Mac + iPhone)"
echo "========================================"
echo "URL: http://${WEBUI_HOST}:${WEBUI_PORT}/"
echo "Device Type: ${PHONE_AGENT_DEVICE_TYPE:-adb}"
echo "Press CTRL+C to stop."
echo "========================================"
echo ""

.venv/bin/python -m uvicorn webui.server:app --host "${WEBUI_HOST}" --port "${WEBUI_PORT}"

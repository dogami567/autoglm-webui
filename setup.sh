#!/bin/bash

set -e

cd "$(dirname "$0")"

echo "[1/4] Checking Python version..."
python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null || {
  echo "[ERROR] Python 3.10+ is required. Current:"
  python3 --version
  exit 1
}

echo "[2/4] Creating venv (.venv)..."
if [ ! -f ".venv/bin/python" ]; then
  python3 -m venv .venv
  if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to create venv."
    exit 1
  fi
fi

echo "[3/4] Installing dependencies..."
.venv/bin/python -m pip install -U pip setuptools wheel || exit 1
.venv/bin/python -m pip install -r requirements.txt || exit 1
.venv/bin/python -m pip install -e . || exit 1

echo "[4/4] Preparing env.sh (optional)..."
if [ ! -f "env.sh" ]; then
  cat > env.sh << 'EOF'
#!/bin/bash
# Environment configuration for autoglm-webui

# Anthropic API (local reverse proxy)
export ANTHROPIC_API_KEY="sk-fbcba6038d8a437caaa5647195f6c2f4"
export ANTHROPIC_BASE_URL="http://127.0.0.1:8045"

# Phone Agent API (use Anthropic API)
export PHONE_AGENT_BASE_URL="http://127.0.0.1:8045"
export PHONE_AGENT_MODEL="claude-sonnet-4-5"
export PHONE_AGENT_API_KEY="sk-fbcba6038d8a437caaa5647195f6c2f4"

# Device Type: adb, hdc, or ios
export PHONE_AGENT_DEVICE_TYPE="ios"

# For iOS devices:
export PHONE_AGENT_WDA_URL="http://localhost:8100"
# export PHONE_AGENT_DEVICE_ID="00008030-001529600C05802E"

# WebUI settings:
export WEBUI_HOST="127.0.0.1"
export WEBUI_PORT="7860"

# scrcpy path (optional, for screen mirroring):
# export SCRCPY_EXE="/opt/homebrew/bin/scrcpy"
EOF
  echo "Created env.sh with your Anthropic API configuration."
fi

echo ""
echo "✅ Setup complete!"
echo "Next steps:"
echo "  1. Review/edit env.sh if needed"
echo "  2. Make sure WebDriverAgent is running (http://localhost:8100)"
echo "  3. Run: ./webui_start.sh"

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
# Use localhost when using iproxy (USB connection)
export PHONE_AGENT_WDA_URL="http://localhost:8100"
# Use WiFi IP only when WDA is running directly on iPhone via Xcode
# export PHONE_AGENT_WDA_URL="http://192.168.1.9:8100"
# export PHONE_AGENT_DEVICE_ID="00008030-001529600C05802E"

# WebUI settings:
export WEBUI_HOST="127.0.0.1"
export WEBUI_PORT="7860"

# scrcpy path (optional, for screen mirroring):
# export SCRCPY_EXE="/opt/homebrew/bin/scrcpy"

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open-AutoGLM (Phone Agent) is an AI-powered mobile automation framework that controls Android/iOS/HarmonyOS devices using vision-language models. The system captures screenshots, understands UI via AutoGLM model, and executes actions through ADB (Android), HDC (HarmonyOS), or WebDriverAgent (iOS).

**Core Flow**: Screenshot → Vision Model Analysis → Action Parsing → Device Control → Loop

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Run agent (interactive mode)
python main.py --base-url <MODEL_URL> --model <MODEL_NAME>

# Run agent with task
python main.py --base-url <MODEL_URL> --model <MODEL_NAME> "Open Chrome browser"

# Using third-party model services
python main.py --base-url https://open.bigmodel.cn/api/paas/v4 --model "autoglm-phone" --apikey <KEY> "task"

# Device commands
python main.py --list-devices
python main.py --list-apps
python main.py --connect 192.168.1.100:5555

# HarmonyOS device
python main.py --device-type hdc --base-url <URL> "task"

# iOS device
python main.py --device-type ios --wda-url http://localhost:8100 "task"

# Check model deployment
python scripts/check_deployment_cn.py --base-url <URL> --model <MODEL>
python scripts/check_deployment_en.py --base-url <URL> --model <MODEL>

# Run tests
pytest tests/

# Docker deployment (vLLM model server)
docker compose -f docker/compose.model.vllm.yml up
```

## Architecture

```
phone_agent/
├── agent.py              # PhoneAgent main class - orchestrates automation loop
├── agent_ios.py          # IOSPhoneAgent for iOS devices
├── device_factory.py     # Factory pattern for device type abstraction
├── adb/                  # Android device control via ADB
│   ├── connection.py     # Remote/local connection management
│   ├── device.py         # Device control (tap, swipe, launch app)
│   ├── input.py          # Text input via ADB Keyboard
│   └── screenshot.py     # Screen capture
├── hdc/                  # HarmonyOS device control via HDC
├── xctest/               # iOS device control via WebDriverAgent
├── actions/
│   └── handler.py        # Action executor - maps model output to device commands
├── config/
│   ├── apps.py           # Android app package name mappings
│   ├── apps_harmonyos.py # HarmonyOS app mappings
│   ├── apps_ios.py       # iOS bundle ID mappings
│   ├── prompts_zh.py     # Chinese system prompts
│   └── prompts_en.py     # English system prompts
└── model/
    └── client.py         # OpenAI-compatible API client
```

**Key Classes**:
- `PhoneAgent` (`agent.py`): Main agent class, manages the screenshot→model→action loop
- `ActionHandler` (`actions/handler.py`): Parses model output and executes device actions
- `ModelClient` (`model/client.py`): Handles communication with vision-language model API
- `DeviceFactory` (`device_factory.py`): Abstract factory for device-specific implementations

## Agent Action Types

The model outputs actions in this format:
```python
do(action="Launch", app="Chrome")
do(action="Tap", element=[x, y])
do(action="Type", text="search query")
do(action="Swipe", element=[x1, y1, x2, y2])
do(action="Back")
do(action="Home")
do(action="Wait")
finish(message="Task completed")
```

## Configuration

**Environment Variables**:
- `PHONE_AGENT_BASE_URL`: Model API URL (default: `http://localhost:8000/v1`)
- `PHONE_AGENT_MODEL`: Model name (default: `autoglm-phone-9b`)
- `PHONE_AGENT_API_KEY`: API key
- `PHONE_AGENT_MAX_STEPS`: Max steps per task (default: 100)
- `PHONE_AGENT_DEVICE_ID`: Device ID for multi-device setups
- `PHONE_AGENT_DEVICE_TYPE`: `adb`, `hdc`, or `ios`
- `PHONE_AGENT_LANG`: `cn` or `en`

**Python API**:
```python
from phone_agent import PhoneAgent
from phone_agent.model import ModelConfig
from phone_agent.agent import AgentConfig

model_config = ModelConfig(
    base_url="http://localhost:8000/v1",
    model_name="autoglm-phone-9b",
    api_key="EMPTY",
)

agent_config = AgentConfig(
    max_steps=100,
    device_id=None,  # auto-detect
    lang="cn",
    verbose=True,
)

agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
result = agent.run("Open Chrome and search for AI news")
```

## Model Deployment

The project requires a running vision-language model service compatible with OpenAI API format.

**Third-party services** (recommended):
- Zhipu BigModel: `--base-url https://open.bigmodel.cn/api/paas/v4 --model autoglm-phone`
- ModelScope: `--base-url https://api-inference.modelscope.cn/v1 --model ZhipuAI/AutoGLM-Phone-9B`

**Local deployment** (requires 24GB+ GPU):
```bash
# vLLM
python3 -m vllm.entrypoints.openai.api_server \
  --served-model-name autoglm-phone-9b \
  --model zai-org/AutoGLM-Phone-9B \
  --max-model-len 25480 \
  --port 8000 \
  # ... additional params in README
```

## Device Prerequisites

**Android**: ADB installed, USB debugging enabled, ADB Keyboard app installed
**HarmonyOS**: HDC installed, USB debugging enabled
**iOS**: WebDriverAgent running, libimobiledevice installed

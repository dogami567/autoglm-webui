# AutoGLM WebUI

A lightweight local WebUI for **Open-AutoGLM / AutoGLM Phone Agent**: connect your phone (ADB) → run connectivity checks → enter a natural language task → watch steps/logs in real time (with an optional Monitor loop).

## Features

- ADB device list & device selector
- Connectivity check: ADB / device online / screenshot / ADB Keyboard / input injection hints
- Two run modes:
  - **direct**: executor runs your task end-to-end
  - **monitor**: a Monitor agent breaks the goal into short delegate tasks for the executor (separate base_url/model/api_key supported)
- Realtime logs via SSE: separate **Monitor** and **Executor** panels
- Sampling controls: `temperature` (executor) and `monitor_temperature` (monitor)
- Phone preview:
  - Web preview (ADB screenshot polling)
  - scrcpy controls (optional, smoother desktop window)

## Quickstart (Windows)

1. Install Python 3.10+
2. Install ADB (platform-tools) and make sure `adb` works in your terminal
3. Enable Developer Options + USB debugging on your Android phone
4. Verify: `adb devices` shows your device as `device`

Install dependencies:

- Run `setup.bat`

Start WebUI:

- Run `webui_start.bat`
- Open `http://127.0.0.1:7860/`

## Cloud models (API key auto-switch)

The WebUI talks to OpenAI-compatible APIs. When **API Key** is set (non-empty and not `EMPTY`), it switches to a cloud preset by default (base_url/model are editable).

## scrcpy (optional)

Resolution order:

1. `SCRCPY_EXE`
2. `scrcpy` in `PATH`
3. `SCRCPY_DIR` (`<dir>/scrcpy.exe` or `<dir>/dist/**/scrcpy.exe`)

## Security notes

- WebUI binds to `127.0.0.1` by default
- API keys are stored only in browser localStorage; server logs are masked
- Do not commit `env.bat` / `docker.env` / `docker.model.env` (already in `.gitignore`)

## Credits

Based on `zai-org/Open-AutoGLM`, repackaged with a focus on WebUI and local debugging.

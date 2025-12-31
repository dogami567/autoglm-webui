@echo off
REM Copy this file to env.bat and fill in your own values (env.bat is git-ignored).
REM Then run start.bat.
REM
REM -----------------------
REM Model service options
REM -----------------------
REM Option A (recommended): use a hosted model service (no GPU needed).
REM Example: Zhipu BigModel
set PHONE_AGENT_BASE_URL=https://open.bigmodel.cn/api/paas/v4
set PHONE_AGENT_MODEL=autoglm-phone
set PHONE_AGENT_API_KEY=your-bigmodel-api-key
REM
REM Example: z.ai
REM set PHONE_AGENT_BASE_URL=https://api.z.ai/api/paas/v4
REM set PHONE_AGENT_MODEL=autoglm-phone-multilingual
REM set PHONE_AGENT_API_KEY=your-zai-api-key
REM
REM Option B: your own OpenAI-compatible model service.
REM set PHONE_AGENT_BASE_URL=http://127.0.0.1:8000/v1
REM set PHONE_AGENT_MODEL=autoglm-phone-9b
REM set PHONE_AGENT_API_KEY=EMPTY
REM
REM -----------------------
REM Device options
REM -----------------------
REM adb = Android, hdc = HarmonyOS, ios = iPhone
REM set PHONE_AGENT_DEVICE_TYPE=adb
REM set PHONE_AGENT_DEVICE_ID=
REM set PHONE_AGENT_LANG=cn
REM set PHONE_AGENT_MAX_STEPS=100
REM
REM -----------------------
REM Performance options (optional)
REM -----------------------
REM Downscale screenshots before sending to the model to reduce latency.
REM Default in code: 1600. Set 0 to disable downscaling.
REM set PHONE_AGENT_IMAGE_MAX_SIDE=1600
REM
REM -----------------------
REM iOS options (if needed)
REM -----------------------
REM set PHONE_AGENT_WDA_URL=http://localhost:8100

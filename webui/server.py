from __future__ import annotations

import math
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import traceback
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import Body
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.responses import Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
STATIC_DIR = APP_ROOT / "static"
INDEX_HTML = STATIC_DIR / "index.html"


def _find_adb() -> str | None:
    adb = shutil.which("adb")
    if adb:
        return adb

    candidates = [
        REPO_ROOT / "platform-tools" / "adb.exe",
        REPO_ROOT / "tools" / "platform-tools" / "adb.exe",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _run_cmd(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _run_cmd_bytes(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(cmd, capture_output=True, text=False, timeout=timeout)


def _clamp_float(value: Any, default: float, min_value: float, max_value: float) -> float:
    try:
        v = float(value)
    except Exception:
        return default
    if not math.isfinite(v):
        return default
    return max(min_value, min(max_value, v))


def _list_adb_devices(adb: str) -> list[dict[str, Any]]:
    cp = _run_cmd([adb, "devices"], timeout=10)
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout or "").strip() or "adb devices failed")

    devices: list[dict[str, Any]] = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("list of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append({"device_id": parts[0], "state": parts[1]})
    return devices


def _check_adb_keyboard(adb: str, device_id: str) -> tuple[bool, str]:
    cp = _run_cmd([adb, "-s", device_id, "shell", "ime", "list", "-s"], timeout=10)
    if cp.returncode != 0:
        return (
            False,
            (cp.stderr or cp.stdout or "").strip() or "adb shell ime list failed",
        )

    ime_list = (cp.stdout or "").strip()
    if "com.android.adbkeyboard/.AdbIME" in ime_list:
        return True, "ADB Keyboard 已安装/可用"

    return (
        False,
        "ADB Keyboard 未检测到：请安装 APK 并在系统设置中启用（或执行 adb shell ime enable com.android.adbkeyboard/.AdbIME）",
    )


def _check_adb_input_injection(adb: str, device_id: str) -> tuple[bool, str]:
    """
    Some OEM ROMs block input injection (adb shell input tap/swipe) unless the
    user enables additional developer options (e.g. 'USB debugging (Security settings)').
    """

    cp = _run_cmd([adb, "-s", device_id, "shell", "input", "tap", "1", "1"], timeout=10)
    if cp.returncode == 0:
        return True, "ADB input tap OK"

    output = ((cp.stderr or "") + (cp.stdout or "")).strip()
    if "SecurityException" in output or "INJECT_EVENTS" in output:
        return (
            False,
            "ADB input 被系统拦截：请在开发者选项开启 USB 调试（安全设置）/允许模拟点击（不同品牌名称不同），并重新授权 USB 调试",
        )
    return False, output or "adb input tap failed"


def _check_screenshot(adb: str, device_id: str) -> tuple[bool, str]:
    remote = f"/sdcard/_autoglm_check_{uuid.uuid4().hex}.png"
    local = Path(tempfile.gettempdir()) / f"autoglm_check_{uuid.uuid4().hex}.png"

    try:
        cp = _run_cmd([adb, "-s", device_id, "shell", "screencap", "-p", remote], timeout=15)
        output = (cp.stdout or "") + (cp.stderr or "")
        if cp.returncode != 0:
            return False, output.strip() or "screencap failed"
        if "Status: -1" in output or "Failed" in output:
            return False, "截图失败：可能在敏感页面（支付/隐私/权限弹窗），请返回到普通界面重试"

        cp2 = _run_cmd([adb, "-s", device_id, "pull", remote, str(local)], timeout=15)
        if cp2.returncode != 0:
            return False, (cp2.stderr or cp2.stdout or "").strip() or "adb pull failed"

        if not local.exists() or local.stat().st_size <= 0:
            return False, "截图文件为空，请重试"

        return True, f"截图 OK（{local.stat().st_size} bytes）"
    finally:
        try:
            _run_cmd([adb, "-s", device_id, "shell", "rm", "-f", remote], timeout=5)
        except Exception:
            pass
        try:
            if local.exists():
                local.unlink()
        except Exception:
            pass


def _choose_adb_device(adb: str, wanted: str) -> tuple[str, list[dict[str, Any]]]:
    devices = _list_adb_devices(adb)
    online = [d for d in devices if d.get("state") == "device"]
    chosen = None
    wanted = (wanted or "").strip()
    if wanted:
        chosen = next((d for d in devices if d.get("device_id") == wanted), None)
    else:
        chosen = online[0] if online else (devices[0] if devices else None)

    if not devices:
        raise RuntimeError("未检测到任何 adb 设备")
    if not chosen:
        raise RuntimeError(f"device_id 未找到: {wanted}")
    if chosen.get("state") != "device":
        raise RuntimeError(f"设备状态异常: {chosen.get('device_id')} ({chosen.get('state')})")

    return chosen["device_id"], devices


def _capture_screencap_png(adb: str, device_id: str, timeout: int = 15) -> bytes:
    """
    Capture PNG bytes via `adb exec-out screencap -p`.

    Compared with `adb shell screencap -p` + pull, this avoids writing files on the
    device and is fast enough for a lightweight WebUI preview.
    """
    cp = _run_cmd_bytes([adb, "-s", device_id, "exec-out", "screencap", "-p"], timeout=timeout)
    if cp.returncode != 0:
        err = b"".join([cp.stderr or b"", cp.stdout or b""]).decode("utf-8", errors="ignore").strip()
        raise RuntimeError(err or "screencap failed")

    data = cp.stdout or b""
    # Some Windows adb builds may return CRLF artifacts; normalize if present.
    if b"\r\r\n" in data:
        data = data.replace(b"\r\r\n", b"\r\n")
    if not data:
        raise RuntimeError("empty screenshot bytes")

    return data


def _find_scrcpy_exe() -> tuple[str | None, str]:
    """
    Return (scrcpy_exe_path, hint_message).

    Resolution order:
    1) SCRCPY_EXE env
    2) scrcpy in PATH
    3) SCRCPY_DIR env (search scrcpy.exe / dist/**/scrcpy.exe)
    """
    env_exe = (os.getenv("SCRCPY_EXE") or "").strip()
    if env_exe:
        p = Path(env_exe)
        if p.exists():
            return str(p), f"SCRCPY_EXE={env_exe}"
        return None, f"SCRCPY_EXE not found: {env_exe}"

    path_exe = shutil.which("scrcpy")
    if path_exe:
        return path_exe, "PATH=scrcpy"

    roots: list[Path] = []
    env_dir = (os.getenv("SCRCPY_DIR") or "").strip()
    if env_dir:
        roots.append(Path(env_dir))

    for root in roots:
        direct = root / "scrcpy.exe"
        if direct.exists():
            return str(direct), f"SCRCPY_DIR={root}"

        candidates = sorted(root.glob("dist/**/scrcpy.exe"))
        if candidates:
            # Pick the last candidate (often highest version in lexical order).
            chosen = candidates[-1]
            return str(chosen), f"SCRCPY_DIR={root}"

    msg = "scrcpy.exe not found. Install scrcpy and add to PATH, or set SCRCPY_EXE / SCRCPY_DIR."
    return None, msg


_scrcpy_lock = threading.Lock()
_scrcpy_proc: subprocess.Popen[bytes] | None = None
_scrcpy_exe_cache: str | None = None


app = FastAPI(title="Open-AutoGLM WebUI")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    if INDEX_HTML.exists():
        return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Open-AutoGLM WebUI</title></head>"
        "<body><h2>Open-AutoGLM WebUI</h2>"
        "<p>index.html not found.</p></body></html>"
    )


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "time": time.time()}


@app.get("/api/devices")
def devices() -> dict[str, Any]:
    device_type = os.getenv("PHONE_AGENT_DEVICE_TYPE", "adb")
    if device_type != "adb":
        raise HTTPException(status_code=400, detail="Only adb is supported in WebUI for now")

    adb = _find_adb()
    if not adb:
        raise HTTPException(
            status_code=500,
            detail="adb not found. Put adb on PATH or use repo/platform-tools/adb.exe",
        )

    try:
        items = _list_adb_devices(adb)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"device_type": "adb", "count": len(items), "devices": items}


@app.post("/api/connectivity-check")
def connectivity_check(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    """
    Connectivity checks for ADB devices.

    Request JSON (optional):
    - device_id: specify a target device when multiple devices exist.
    """
    device_type = (payload.get("device_type") or os.getenv("PHONE_AGENT_DEVICE_TYPE") or "adb").strip()
    if device_type != "adb":
        raise HTTPException(status_code=400, detail="Only adb is supported in WebUI for now")

    logs: list[str] = []
    checks: list[dict[str, Any]] = []

    adb = _find_adb()
    if not adb:
        checks.append({"name": "adb", "ok": False, "message": "adb not found"})
        return {"overall": "fail", "checks": checks, "logs": logs}

    checks.append({"name": "adb", "ok": True, "message": f"adb: {adb}"})

    try:
        devices = _list_adb_devices(adb)
    except Exception as e:
        checks.append({"name": "devices", "ok": False, "message": str(e)})
        return {"overall": "fail", "checks": checks, "logs": logs}

    wanted = (payload.get("device_id") or os.getenv("PHONE_AGENT_DEVICE_ID") or "").strip()
    online = [d for d in devices if d.get("state") == "device"]
    chosen = None
    if wanted:
        chosen = next((d for d in devices if d.get("device_id") == wanted), None)
        if not chosen:
            checks.append(
                {
                    "name": "devices",
                    "ok": False,
                    "message": f"device_id 未找到: {wanted}",
                }
            )
            return {"overall": "fail", "checks": checks, "logs": logs, "devices": devices}
    else:
        chosen = online[0] if online else (devices[0] if devices else None)

    if not devices:
        checks.append({"name": "devices", "ok": False, "message": "未检测到任何 adb 设备"})
        return {"overall": "fail", "checks": checks, "logs": logs, "devices": devices}

    if chosen and chosen.get("state") != "device":
        checks.append(
            {
                "name": "devices",
                "ok": False,
                "message": f"设备状态异常: {chosen.get('device_id')} ({chosen.get('state')})",
            }
        )
        return {"overall": "fail", "checks": checks, "logs": logs, "devices": devices}

    device_id = chosen["device_id"] if chosen else ""
    checks.append(
        {
            "name": "devices",
            "ok": True,
            "message": f"设备 OK: {device_id}",
        }
    )

    ok_shot, msg_shot = _check_screenshot(adb, device_id)
    checks.append({"name": "screenshot", "ok": ok_shot, "message": msg_shot})

    ok_kb, msg_kb = _check_adb_keyboard(adb, device_id)
    checks.append({"name": "adb_keyboard", "ok": ok_kb, "message": msg_kb})

    ok_input, msg_input = _check_adb_input_injection(adb, device_id)
    checks.append({"name": "adb_input", "ok": ok_input, "message": msg_input})

    overall = "pass" if all(c["ok"] for c in checks) else "fail"
    return {"overall": overall, "device_id": device_id, "checks": checks, "logs": logs, "devices": devices}


@app.get("/api/screen")
def screen(device_id: str | None = None) -> Response:
    """
    Return a single PNG screenshot for lightweight monitoring in WebUI.

    Query:
    - device_id: optional adb serial; otherwise uses env PHONE_AGENT_DEVICE_ID or auto-pick.
    """
    device_type = os.getenv("PHONE_AGENT_DEVICE_TYPE", "adb")
    if device_type != "adb":
        raise HTTPException(status_code=400, detail="Only adb is supported in WebUI for now")

    adb = _find_adb()
    if not adb:
        raise HTTPException(
            status_code=500,
            detail="adb not found. Put adb on PATH or use repo/platform-tools/adb.exe",
        )

    wanted = (device_id or os.getenv("PHONE_AGENT_DEVICE_ID") or "").strip()
    try:
        chosen_id, _devices = _choose_adb_device(adb, wanted)
        png = _capture_screencap_png(adb, chosen_id, timeout=15)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
    }
    return Response(content=png, media_type="image/png", headers=headers)


@app.get("/api/scrcpy/status")
def scrcpy_status() -> dict[str, Any]:
    global _scrcpy_proc, _scrcpy_exe_cache

    with _scrcpy_lock:
        if _scrcpy_proc and _scrcpy_proc.poll() is not None:
            _scrcpy_proc = None

        exe, hint = _find_scrcpy_exe()
        _scrcpy_exe_cache = exe
        return {
            "ok": True,
            "running": bool(_scrcpy_proc),
            "pid": _scrcpy_proc.pid if _scrcpy_proc else None,
            "scrcpy_exe": exe,
            "hint": hint,
        }


@app.post("/api/scrcpy/start")
def scrcpy_start(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    """
    Start scrcpy desktop mirroring (opens a separate window on the server machine).

    Request JSON (optional):
    - device_id: adb serial; defaults to env PHONE_AGENT_DEVICE_ID or auto-pick.
    """
    global _scrcpy_proc, _scrcpy_exe_cache

    with _scrcpy_lock:
        if _scrcpy_proc and _scrcpy_proc.poll() is None:
            raise HTTPException(status_code=409, detail="scrcpy already running")
        _scrcpy_proc = None

        exe, hint = _find_scrcpy_exe()
        _scrcpy_exe_cache = exe
        if not exe:
            raise HTTPException(status_code=500, detail=hint)

        adb = _find_adb()
        if not adb:
            raise HTTPException(status_code=500, detail="adb not found")

        wanted = (payload.get("device_id") or os.getenv("PHONE_AGENT_DEVICE_ID") or "").strip()
        try:
            chosen_id, _devices = _choose_adb_device(adb, wanted)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        cmd = [exe, "--serial", chosen_id]
        try:
            _scrcpy_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(Path(exe).parent),
            )
        except Exception as e:
            _scrcpy_proc = None
            raise HTTPException(status_code=500, detail=f"failed to start scrcpy: {e}") from e

        return {"ok": True, "running": True, "pid": _scrcpy_proc.pid, "device_id": chosen_id, "hint": hint}


@app.post("/api/scrcpy/stop")
def scrcpy_stop() -> dict[str, Any]:
    global _scrcpy_proc

    with _scrcpy_lock:
        if not _scrcpy_proc or _scrcpy_proc.poll() is not None:
            _scrcpy_proc = None
            return {"ok": True, "stopped": False, "message": "scrcpy not running"}

        proc = _scrcpy_proc
        _scrcpy_proc = None

    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    except Exception:
        pass

    return {"ok": True, "stopped": True}


class _RunState:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.queue: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self.cancel_event = threading.Event()
        self.done_event = threading.Event()
        self.started_at = time.time()

    def emit(self, event: dict[str, Any]) -> None:
        self.queue.put(event)

    def finish(self) -> None:
        self.done_event.set()
        self.queue.put(None)


_run_lock = threading.Lock()
_current_run: _RunState | None = None


def _mask_api_key(api_key: str) -> str:
    key = (api_key or "").strip()
    if not key or key.upper() == "EMPTY":
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


_DEFAULT_MONITOR_PROMPT_ZH = """你是“监控AI（Monitor Agent）”，你的职责是把用户的综合性目标拆解为一系列短的、可执行的手机操作子任务，并交给“操控AI（Phone Agent）”去执行。

约束与工作方式：
- 你每一轮只能输出 **一行**，不要输出任何额外解释/文字。
- 你要让操控AI每次最多做 1~3 个动作，用于“推进进度或搜集信息”。如果任务需要更多动作，你应该拆成多轮。
- 你会收到上一轮操控AI的“观察结果（Observation）”（包含动作/结果/当前App等），你必须基于观察结果决定下一步。

输出格式（必须严格遵守其一）：
1) 下达子任务（推荐：直接输出任务文本，无需 do(...) 包裹）：
打开XX应用，点击XX，输入XX并搜索。（最多 1~3 步）

2) 结束整个循环：
end: 结束原因/最终结论/需要用户接管的说明

注意：
- 子任务里不要包含敏感操作（支付/转账/删除/授权）除非用户明确要求，并尽量在需要时请求用户接管。
- 尽量不要在子任务里使用英文双引号 \"\"（容易导致解析失败）；如需强调按钮文案，请用【我的】/《我的》这样的括号。
- 如果观察结果表明点击/输入被系统拦截（例如 ADB input 注入失败），优先结束并提示用户修复环境。"""


def _parse_monitor_output_fallback(raw: str) -> dict[str, Any]:
    """
    Monitor output is less stable across LLM providers (quotes/newlines/etc).

    We accept BOTH:
    - legacy: do(action="Delegate", task="...") / finish(message="end: ...")
    - relaxed: plain task line / "end: ..."
    """
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty monitor output")

    low = text.lower()
    if low.startswith("end:"):
        return {"_metadata": "finish", "message": text}

    # If it looks like a finish call but parsing failed, treat it as finish text.
    if low.startswith("finish(") or "finish(" in low:
        return {"_metadata": "finish", "message": text}

    # If it looks like a Delegate call but parsing failed, try to extract task=...
    idx = text.find("task=")
    if idx != -1:
        val = text[idx + len("task=") :].strip()
        if val.endswith(")"):
            val = val[:-1].rstrip()
        if val and val[0] in "\"'“”‘’":
            q = val[0]
            inner = val[1:]
            if inner.endswith(q):
                inner = inner[:-1]
            else:
                last = inner.rfind(q)
                if last != -1:
                    inner = inner[:last]
            val = inner
        return {"_metadata": "do", "action": "Delegate", "task": val}

    # Relaxed: treat the whole line as delegated task.
    return {"_metadata": "do", "action": "Delegate", "task": text}


def _strip_images_from_monitor_messages(messages: list[dict[str, Any]]) -> None:
    """
    To keep context size manageable, remove image parts from previous messages.

    We keep text-only history, and allow only the latest message to carry an image.
    """

    for m in messages:
        content = m.get("content")
        if not isinstance(content, list):
            continue

        texts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                t = part.get("text")
                if isinstance(t, str) and t.strip():
                    texts.append(t.strip())
        m["content"] = "\n".join(texts).strip()


def _make_monitor_user_message(*, text: str, image_base64: str | None) -> dict[str, Any]:
    if image_base64:
        return {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                {"type": "text", "text": text},
            ],
        }
    return {"role": "user", "content": text}


def _run_agent_in_thread(run: _RunState, payload: dict[str, Any]) -> None:
    try:
        task = (payload.get("task") or "").strip()
        if not task:
            run.emit({"type": "error", "message": "task is required", "ts": time.time()})
            return

        device_type = (payload.get("device_type") or "adb").strip()
        device_id = (payload.get("device_id") or os.getenv("PHONE_AGENT_DEVICE_ID") or "").strip() or None
        lang = (payload.get("lang") or os.getenv("PHONE_AGENT_LANG") or "cn").strip()
        max_steps = int(payload.get("max_steps") or os.getenv("PHONE_AGENT_MAX_STEPS") or 100)

        base_url = (payload.get("base_url") or os.getenv("PHONE_AGENT_BASE_URL") or "http://127.0.0.1:8000/v1").strip()
        model = (payload.get("model") or os.getenv("PHONE_AGENT_MODEL") or "autoglm-phone-9b").strip()
        api_key = (payload.get("api_key") or os.getenv("PHONE_AGENT_API_KEY") or "EMPTY").strip()
        simulate = bool(payload.get("simulate") or payload.get("dry_run") or False)
        temperature = _clamp_float(payload.get("temperature", os.getenv("PHONE_AGENT_TEMPERATURE")), 0.0, 0.0, 2.0)

        run.emit(
            {
                "type": "start",
                "ts": time.time(),
                "run_id": run.run_id,
                "task": task,
                "device_type": device_type,
                "device_id": device_id or "",
                "lang": lang,
                "max_steps": max_steps,
                "base_url": base_url,
                "model": model,
                "api_key_set": bool(api_key and api_key.upper() != "EMPTY"),
                "temperature": temperature,
            }
        )

        if api_key and api_key.upper() != "EMPTY":
            run.emit(
                {
                    "type": "log",
                    "ts": time.time(),
                    "level": "info",
                    "message": f"Using api_key={_mask_api_key(api_key)}",
                }
            )

        if simulate:
            simulate_steps = int(payload.get("simulate_steps") or min(max_steps, 8))
            simulate_delay_ms = int(payload.get("simulate_delay_ms") or 200)
            run.emit(
                {
                    "type": "log",
                    "ts": time.time(),
                    "level": "info",
                    "message": f"Simulate mode enabled: steps={simulate_steps}, delay_ms={simulate_delay_ms}",
                }
            )

            for step_index in range(simulate_steps):
                if run.cancel_event.is_set():
                    run.emit({"type": "log", "ts": time.time(), "level": "warn", "message": "run cancelled"})
                    run.emit({"type": "end", "ts": time.time(), "message": "Stopped"})
                    return

                is_last = step_index == simulate_steps - 1
                run.emit(
                    {
                        "type": "step",
                        "ts": time.time(),
                        "step": step_index,
                        "thinking": f"[simulate] step {step_index}: decide next action",
                        "action": {"action": "Launch" if step_index == 0 else "Tap", "target": "com.example.app"},
                        "success": True,
                        "finished": is_last,
                        "message": "ok",
                    }
                )

                if simulate_delay_ms > 0:
                    time.sleep(simulate_delay_ms / 1000.0)

            run.emit({"type": "end", "ts": time.time(), "message": "Simulated run completed"})
            return

        from phone_agent import PhoneAgent
        from phone_agent.agent import AgentConfig
        from phone_agent.device_factory import DeviceType, set_device_type
        from phone_agent.model.client import ModelConfig

        if device_type == "adb":
            set_device_type(DeviceType.ADB)
        elif device_type == "hdc":
            set_device_type(DeviceType.HDC)
        else:
            run.emit({"type": "error", "message": f"unsupported device_type: {device_type}", "ts": time.time()})
            return

        def confirmation_callback(message: str) -> bool:
            run.emit(
                {
                    "type": "confirm_required",
                    "ts": time.time(),
                    "message": message,
                    "decision": "denied",
                }
            )
            # Default: deny in WebUI (avoid blocking).
            return False

        def takeover_callback(message: str) -> None:
            run.emit({"type": "takeover", "ts": time.time(), "message": message})
            # Default: stop after takeover request to avoid hanging.
            run.cancel_event.set()

        model_config = ModelConfig(
            base_url=base_url,
            api_key=api_key,
            model_name=model,
            lang=lang,
            temperature=temperature,
        )
        agent_config = AgentConfig(
            max_steps=max_steps,
            device_id=device_id,
            verbose=False,
            lang=lang,
        )

        agent = PhoneAgent(
            model_config=model_config,
            agent_config=agent_config,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        step_index = 0
        result = agent.step(task)
        run.emit(
            {
                "type": "step",
                "ts": time.time(),
                "step": step_index,
                "thinking": result.thinking,
                "action": result.action,
                "success": result.success,
                "finished": result.finished,
                "message": result.message,
            }
        )

        while not result.finished and step_index < max_steps - 1:
            if run.cancel_event.is_set():
                run.emit({"type": "log", "ts": time.time(), "level": "warn", "message": "run cancelled"})
                break

            step_index += 1
            result = agent.step()
            run.emit(
                {
                    "type": "step",
                    "ts": time.time(),
                    "step": step_index,
                    "thinking": result.thinking,
                    "action": result.action,
                    "success": result.success,
                    "finished": result.finished,
                    "message": result.message,
                }
            )

        run.emit(
            {
                "type": "end",
                "ts": time.time(),
                "message": result.message or ("Task completed" if result.finished else "Stopped"),
            }
        )

    except Exception as e:
        run.emit(
            {
                "type": "error",
                "ts": time.time(),
                "message": str(e),
                "traceback": traceback.format_exc(),
            }
        )
    finally:
        run.finish()


def _run_executor_burst(
    run: _RunState,
    payload: dict[str, Any],
    *,
    task: str,
    round_index: int,
    max_steps: int,
) -> dict[str, Any]:
    """
    Run PhoneAgent for a short burst (<= max_steps actions) and return an observation dict.

    This does NOT call run.finish(); the monitor loop controls stream lifetime.
    """

    device_type = (payload.get("device_type") or "adb").strip()
    device_id = (payload.get("device_id") or os.getenv("PHONE_AGENT_DEVICE_ID") or "").strip() or None
    lang = (payload.get("lang") or os.getenv("PHONE_AGENT_LANG") or "cn").strip()

    base_url = (payload.get("base_url") or os.getenv("PHONE_AGENT_BASE_URL") or "http://127.0.0.1:8000/v1").strip()
    model = (payload.get("model") or os.getenv("PHONE_AGENT_MODEL") or "autoglm-phone-9b").strip()
    api_key = (payload.get("api_key") or os.getenv("PHONE_AGENT_API_KEY") or "EMPTY").strip()
    temperature = _clamp_float(payload.get("executor_temperature", payload.get("temperature", 0.0)), 0.0, 0.0, 2.0)

    simulate = bool(payload.get("simulate") or payload.get("simulate_executor") or False)

    run.emit(
        {
            "type": "start",
            "scope": "executor",
            "round": round_index,
            "ts": time.time(),
            "task": task,
            "device_type": device_type,
            "device_id": device_id or "",
            "lang": lang,
            "max_steps": max_steps,
            "base_url": base_url,
            "model": model,
            "api_key_set": bool(api_key and api_key.upper() != "EMPTY"),
            "temperature": temperature,
        }
    )

    if api_key and api_key.upper() != "EMPTY":
        run.emit(
            {
                "type": "log",
                "ts": time.time(),
                "level": "info",
                "message": f"[executor] Using api_key={_mask_api_key(api_key)}",
            }
        )

    if simulate:
        steps: list[dict[str, Any]] = []
        simulate_steps = max(1, min(int(payload.get("simulate_steps") or max_steps), max_steps))
        for i in range(simulate_steps):
            if run.cancel_event.is_set():
                break
            steps.append(
                {
                    "step": i,
                    "success": True,
                    "finished": False,
                    "action": {"action": "Tap", "target": "simulate"},
                    "message": "ok",
                }
            )
            run.emit(
                {
                    "type": "step",
                    "scope": "executor",
                    "round": round_index,
                    "ts": time.time(),
                    "step": i,
                    "thinking": f"[simulate] executor step {i}",
                    "action": {"action": "Tap", "target": "simulate"},
                    "success": True,
                    "finished": False,
                    "message": "ok",
                }
            )

        run.emit(
            {
                "type": "burst_end",
                "scope": "executor",
                "round": round_index,
                "ts": time.time(),
                "message": "simulate burst end",
            }
        )
        return {
            "round": round_index,
            "task": task,
            "finished": False,
            "message": "simulate",
            "steps": steps,
        }

    from phone_agent import PhoneAgent
    from phone_agent.agent import AgentConfig
    from phone_agent.device_factory import DeviceType, set_device_type
    from phone_agent.model.client import ModelConfig

    if device_type == "adb":
        set_device_type(DeviceType.ADB)
    elif device_type == "hdc":
        set_device_type(DeviceType.HDC)
    else:
        raise ValueError(f"unsupported device_type: {device_type}")

    def confirmation_callback(message: str) -> bool:
        run.emit(
            {
                "type": "confirm_required",
                "scope": "executor",
                "round": round_index,
                "ts": time.time(),
                "message": message,
                "decision": "denied",
            }
        )
        return False

    def takeover_callback(message: str) -> None:
        run.emit(
            {
                "type": "takeover",
                "scope": "executor",
                "round": round_index,
                "ts": time.time(),
                "message": message,
            }
        )
        run.cancel_event.set()

    model_config = ModelConfig(
        base_url=base_url,
        api_key=api_key,
        model_name=model,
        lang=lang,
        temperature=temperature,
    )
    agent_config = AgentConfig(max_steps=max_steps, device_id=device_id, verbose=False, lang=lang)

    agent = PhoneAgent(
        model_config=model_config,
        agent_config=agent_config,
        confirmation_callback=confirmation_callback,
        takeover_callback=takeover_callback,
    )

    steps: list[dict[str, Any]] = []
    step_index = 0
    result = agent.step(task)
    steps.append(
        {
            "step": step_index,
            "success": result.success,
            "finished": result.finished,
            "action": result.action,
            "message": result.message,
        }
    )
    run.emit(
        {
            "type": "step",
            "scope": "executor",
            "round": round_index,
            "ts": time.time(),
            "step": step_index,
            "thinking": result.thinking,
            "action": result.action,
            "success": result.success,
            "finished": result.finished,
            "message": result.message,
        }
    )

    while not result.finished and step_index < max_steps - 1:
        if run.cancel_event.is_set():
            break
        step_index += 1
        result = agent.step()
        steps.append(
            {
                "step": step_index,
                "success": result.success,
                "finished": result.finished,
                "action": result.action,
                "message": result.message,
            }
        )
        run.emit(
            {
                "type": "step",
                "scope": "executor",
                "round": round_index,
                "ts": time.time(),
                "step": step_index,
                "thinking": result.thinking,
                "action": result.action,
                "success": result.success,
                "finished": result.finished,
                "message": result.message,
            }
        )

    try:
        from phone_agent.device_factory import get_device_factory

        current_app = get_device_factory().get_current_app(device_id)
    except Exception:
        current_app = ""

    run.emit(
        {
            "type": "burst_end",
            "scope": "executor",
            "round": round_index,
            "ts": time.time(),
            "message": result.message or ("finished" if result.finished else "burst limit reached"),
        }
    )
    return {
        "round": round_index,
        "task": task,
        "finished": bool(result.finished),
        "success": bool(result.success),
        "message": result.message or "",
        "current_app": current_app,
        "steps": steps,
    }


def _run_monitor_in_thread(run: _RunState, payload: dict[str, Any]) -> None:
    """
    Monitor loop:
    - Ask monitor LLM to output do(action="Delegate", task="...") or finish(message="end: ...")
    - Run executor burst (<=3 steps by default) for each delegate task
    - Feed observations back to monitor LLM
    """

    try:
        goal = (payload.get("goal") or payload.get("task") or "").strip()
        if not goal:
            run.emit({"type": "error", "message": "goal is required", "ts": time.time()})
            return

        device_type = (payload.get("device_type") or os.getenv("PHONE_AGENT_DEVICE_TYPE") or "adb").strip()
        device_id = (payload.get("device_id") or os.getenv("PHONE_AGENT_DEVICE_ID") or "").strip() or None

        lang = (payload.get("lang") or os.getenv("PHONE_AGENT_LANG") or "cn").strip()

        executor_base_url = (payload.get("base_url") or os.getenv("PHONE_AGENT_BASE_URL") or "http://127.0.0.1:8000/v1").strip()
        executor_model = (payload.get("model") or os.getenv("PHONE_AGENT_MODEL") or "autoglm-phone-9b").strip()
        executor_api_key = (payload.get("api_key") or os.getenv("PHONE_AGENT_API_KEY") or "EMPTY").strip()

        monitor_base_url = (
            payload.get("monitor_base_url")
            or payload.get("monitor_baseurl")
            or executor_base_url
        )
        monitor_base_url = (monitor_base_url or "").strip() or executor_base_url

        monitor_model = (
            payload.get("monitor_model")
            or payload.get("monitor_model_name")
            or executor_model
        )
        monitor_model = (monitor_model or "").strip() or executor_model

        monitor_api_key = (
            payload.get("monitor_api_key")
            or payload.get("monitor_apikey")
            or executor_api_key
            or "EMPTY"
        )
        monitor_api_key = (monitor_api_key or "").strip() or "EMPTY"
        executor_max_steps = int(payload.get("executor_max_steps") or 3)
        max_rounds = int(payload.get("max_rounds") or payload.get("monitor_max_rounds") or 30)
        executor_temperature = _clamp_float(payload.get("executor_temperature", payload.get("temperature", 0.0)), 0.0, 0.0, 2.0)
        monitor_temperature = _clamp_float(payload.get("monitor_temperature", payload.get("temperature", 0.0)), 0.0, 0.0, 2.0)

        monitor_prompt = (payload.get("monitor_prompt") or "").strip()
        if not monitor_prompt:
            monitor_prompt = _DEFAULT_MONITOR_PROMPT_ZH

        monitor_use_screenshot = bool(
            payload.get("monitor_use_screenshot")
            or payload.get("monitor_use_screen")
            or payload.get("monitor_screenshot")
            or False
        )

        device_factory = None
        if monitor_use_screenshot:
            try:
                from phone_agent.device_factory import DeviceType, get_device_factory, set_device_type

                if device_type == "adb":
                    set_device_type(DeviceType.ADB)
                elif device_type == "hdc":
                    set_device_type(DeviceType.HDC)
                device_factory = get_device_factory()
            except Exception as e:
                monitor_use_screenshot = False
                run.emit(
                    {
                        "type": "log",
                        "ts": time.time(),
                        "level": "warn",
                        "message": f"[monitor] screenshot disabled (init failed): {e}",
                    }
                )

        run.emit(
            {
                "type": "monitor_start",
                "ts": time.time(),
                "goal": goal,
                "lang": lang,
                # Backward-compatible fields (treat as monitor LLM config).
                "base_url": monitor_base_url,
                "model": monitor_model,
                "executor_max_steps": executor_max_steps,
                "max_rounds": max_rounds,
                "api_key_set": bool(monitor_api_key and monitor_api_key.upper() != "EMPTY"),
                # Explicit fields
                "monitor_base_url": monitor_base_url,
                "monitor_model": monitor_model,
                "monitor_api_key_set": bool(monitor_api_key and monitor_api_key.upper() != "EMPTY"),
                "executor_base_url": executor_base_url,
                "executor_model": executor_model,
                "executor_api_key_set": bool(executor_api_key and executor_api_key.upper() != "EMPTY"),
                "monitor_temperature": monitor_temperature,
                "executor_temperature": executor_temperature,
                "monitor_use_screenshot": monitor_use_screenshot,
            }
            )

        simulate_monitor = bool(payload.get("simulate_monitor") or payload.get("monitor_simulate") or False)
        if simulate_monitor:
            run.emit(
                {
                    "type": "log",
                    "ts": time.time(),
                    "level": "info",
                    "message": "[monitor] Simulate monitor enabled (no LLM call)",
                }
            )
            forced = dict(payload)
            forced["simulate"] = True
            rounds = min(max_rounds, 3)
            for round_index in range(rounds):
                if run.cancel_event.is_set():
                    run.emit({"type": "end", "ts": time.time(), "message": "Stopped"})
                    return
                delegated = f"[simulate monitor] round {round_index}: {goal}"
                run.emit({"type": "monitor_delegate", "ts": time.time(), "round": round_index, "task": delegated})
                _run_executor_burst(
                    run,
                    forced,
                    task=delegated,
                    round_index=round_index,
                    max_steps=max(1, min(executor_max_steps, 10)),
                )
            run.emit({"type": "end", "ts": time.time(), "message": "end: simulate monitor completed"})
            return

        if monitor_api_key and monitor_api_key.upper() != "EMPTY":
            run.emit(
                {
                    "type": "log",
                    "ts": time.time(),
                    "level": "info",
                    "message": f"[monitor] Using api_key={_mask_api_key(monitor_api_key)}",
                }
            )

        from openai import OpenAI
        from phone_agent.actions.handler import parse_action

        client = OpenAI(base_url=monitor_base_url, api_key=monitor_api_key, timeout=60.0)

        messages: list[dict[str, Any]] = [{"role": "system", "content": monitor_prompt}]

        goal_text = f"用户目标（Goal）：{goal}\n\n请输出下一步子任务（<=3步）或 end: ...。"
        if monitor_use_screenshot and device_factory:
            try:
                shot = device_factory.get_screenshot(device_id)
                current_app = ""
                try:
                    current_app = device_factory.get_current_app(device_id)
                except Exception:
                    current_app = ""
                messages.append(
                    _make_monitor_user_message(
                        text=f"{goal_text}\n\nCurrentApp: {current_app}",
                        image_base64=getattr(shot, "base64_data", None),
                    )
                )
            except Exception as e:
                run.emit(
                    {
                        "type": "log",
                        "ts": time.time(),
                        "level": "warn",
                        "message": f"[monitor] screenshot capture failed (start): {e}",
                    }
                )
                messages.append({"role": "user", "content": goal_text})
        else:
            messages.append({"role": "user", "content": goal_text})

        # NOTE: We deliberately use non-streaming chat completions for Monitor.
        # The monitor output is parsed as a single "decision" each round, and
        # streaming partial tokens can cause truncated / malformed commands.
        monitor_max_tokens_raw = payload.get("monitor_max_tokens", 800)
        try:
            monitor_max_tokens = int(monitor_max_tokens_raw)
        except Exception:
            monitor_max_tokens = 800
        monitor_max_tokens = max(50, min(4000, monitor_max_tokens))

        for round_index in range(max_rounds):
            if run.cancel_event.is_set():
                run.emit({"type": "end", "ts": time.time(), "message": "Stopped"})
                return

            try:
                resp = client.chat.completions.create(
                    model=monitor_model,
                    messages=messages,
                    max_tokens=monitor_max_tokens,
                    temperature=monitor_temperature,
                    stream=False,
                )
            except Exception as e:
                # Some OpenAI-compatible providers don't support image parts in Chat Completions.
                if monitor_use_screenshot:
                    run.emit(
                        {
                            "type": "log",
                            "ts": time.time(),
                            "level": "warn",
                            "message": f"[monitor] vision request failed, retry text-only: {e}",
                        }
                    )
                    monitor_use_screenshot = False
                    _strip_images_from_monitor_messages(messages)
                    resp = client.chat.completions.create(
                        model=monitor_model,
                        messages=messages,
                        max_tokens=monitor_max_tokens,
                        temperature=monitor_temperature,
                        stream=False,
                    )
                else:
                    raise
            content = (resp.choices[0].message.content or "").strip() if resp.choices else ""
            finish_reason = ""
            try:
                finish_reason = (resp.choices[0].finish_reason or "").strip() if resp.choices else ""
            except Exception:
                finish_reason = ""
            if finish_reason == "length":
                run.emit(
                    {
                        "type": "log",
                        "ts": time.time(),
                        "level": "warn",
                        "message": f"[monitor] output truncated (finish_reason=length). Consider increasing monitor_max_tokens (current={monitor_max_tokens}).",
                    }
                )
            run.emit(
                {
                    "type": "monitor_decision",
                    "ts": time.time(),
                    "round": round_index,
                    "raw": content,
                    "finish_reason": finish_reason,
                }
            )

            try:
                act = parse_action(content)
            except Exception as e:
                run.emit(
                    {
                        "type": "log",
                        "ts": time.time(),
                        "level": "warn",
                        "message": f"[monitor] parse failed, fallback to relaxed mode: {e}",
                    }
                )
                act = _parse_monitor_output_fallback(content)

            messages.append({"role": "assistant", "content": content})

            if act.get("_metadata") == "finish":
                msg = (act.get("message") or "").strip()
                run.emit({"type": "end", "ts": time.time(), "message": msg or "end"})
                return

            # Relaxed mode: if act is `do` but not Delegate, treat it as task text.
            if act.get("_metadata") != "do":
                run.emit(
                    {
                        "type": "error",
                        "ts": time.time(),
                        "message": f"monitor must output Delegate/task or end, got: {act}",
                    }
                )
                return

            if act.get("action") != "Delegate":
                delegated = (content or "").strip()
                act = {"_metadata": "do", "action": "Delegate", "task": delegated}

            delegated = (act.get("task") or "").strip()
            if not delegated:
                run.emit({"type": "error", "ts": time.time(), "message": "monitor Delegate missing task"})
                return

            run.emit({"type": "monitor_delegate", "ts": time.time(), "round": round_index, "task": delegated})

            try:
                obs = _run_executor_burst(
                    run,
                    payload,
                    task=delegated,
                    round_index=round_index,
                    max_steps=max(1, min(executor_max_steps, 10)),
                )
            except Exception as e:
                run.emit(
                    {
                        "type": "error",
                        "ts": time.time(),
                        "message": f"executor burst failed: {e}",
                        "traceback": traceback.format_exc(),
                    }
                )
                return

            obs_text = f"Observation (round {round_index}): {obs}"
            if monitor_use_screenshot and device_factory:
                # Keep only the latest image in the whole monitor context.
                _strip_images_from_monitor_messages(messages)
                try:
                    shot = device_factory.get_screenshot(device_id)
                    current_app = ""
                    try:
                        current_app = device_factory.get_current_app(device_id)
                    except Exception:
                        current_app = ""
                    messages.append(
                        _make_monitor_user_message(
                            text=f"{obs_text}\n\nCurrentApp: {current_app}",
                            image_base64=getattr(shot, "base64_data", None),
                        )
                    )
                except Exception as e:
                    run.emit(
                        {
                            "type": "log",
                            "ts": time.time(),
                            "level": "warn",
                            "message": f"[monitor] screenshot capture failed (round {round_index}): {e}",
                        }
                    )
                    messages.append({"role": "user", "content": obs_text})
            else:
                messages.append({"role": "user", "content": obs_text})

        run.emit({"type": "end", "ts": time.time(), "message": f"end: reached max_rounds={max_rounds}"})

    except Exception as e:
        run.emit({"type": "error", "ts": time.time(), "message": str(e), "traceback": traceback.format_exc()})
    finally:
        run.finish()


@app.post("/api/run")
def run_task(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    global _current_run

    with _run_lock:
        if _current_run and not _current_run.done_event.is_set():
            raise HTTPException(status_code=409, detail="A run is already in progress")
        _current_run = _RunState(run_id=uuid.uuid4().hex)
        run = _current_run

        mode = (payload.get("mode") or "direct").strip().lower()
        if mode in ("monitor", "supervisor"):
            thread = threading.Thread(target=_run_monitor_in_thread, args=(run, payload), daemon=True)
        else:
            thread = threading.Thread(target=_run_agent_in_thread, args=(run, payload), daemon=True)
        thread.start()

    return {"ok": True, "run_id": run.run_id}


@app.post("/api/run/stop")
def stop_run() -> dict[str, Any]:
    if not _current_run or _current_run.done_event.is_set():
        return {"ok": True, "stopped": False, "message": "no active run"}
    _current_run.cancel_event.set()
    return {"ok": True, "stopped": True}


@app.get("/api/run/stream")
def stream(run_id: str | None = None) -> StreamingResponse:
    if not _current_run:
        raise HTTPException(status_code=404, detail="no run")
    if run_id and run_id != _current_run.run_id:
        raise HTTPException(status_code=404, detail="run_id not found")

    run = _current_run

    def gen():
        # SSE stream
        yield ": stream-start\n\n"
        while True:
            try:
                item = run.queue.get(timeout=1)
            except queue.Empty:
                if run.done_event.is_set():
                    break
                yield ": keep-alive\n\n"
                continue

            if item is None:
                break

            import json

            payload = json.dumps(item, ensure_ascii=False)
            yield f"data: {payload}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)

"""Action handler for processing AI model outputs."""

import ast
import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.config.timing import TIMING_CONFIG
from phone_agent.device_factory import get_device_factory


@dataclass
class ActionResult:
    """Result of an action execution."""

    success: bool
    should_finish: bool
    message: str | None = None
    requires_confirmation: bool = False


class ActionHandler:
    """
    Handles execution of actions from AI model output.

    Args:
        device_id: Optional ADB device ID for multi-device setups.
        confirmation_callback: Optional callback for sensitive action confirmation.
            Should return True to proceed, False to cancel.
        takeover_callback: Optional callback for takeover requests (login, captcha).
    """

    def __init__(
        self,
        device_id: str | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.device_id = device_id
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        self.takeover_callback = takeover_callback or self._default_takeover

    def execute(
        self, action: dict[str, Any], screen_width: int, screen_height: int
    ) -> ActionResult:
        """
        Execute an action from the AI model.

        Args:
            action: The action dictionary from the model.
            screen_width: Current screen width in pixels.
            screen_height: Current screen height in pixels.

        Returns:
            ActionResult indicating success and whether to finish.
        """
        action_type = action.get("_metadata")

        if action_type == "finish":
            return ActionResult(
                success=True, should_finish=True, message=action.get("message")
            )

        if action_type != "do":
            return ActionResult(
                success=False,
                should_finish=True,
                message=f"Unknown action type: {action_type}",
            )

        action_name = action.get("action")
        handler_method = self._get_handler(action_name)

        if handler_method is None:
            return ActionResult(
                success=False,
                should_finish=False,
                message=f"Unknown action: {action_name}",
            )

        try:
            return handler_method(action, screen_width, screen_height)
        except Exception as e:
            return ActionResult(
                success=False, should_finish=False, message=f"Action failed: {e}"
            )

    def _get_handler(self, action_name: str) -> Callable | None:
        """Get the handler method for an action."""
        handlers = {
            "Launch": self._handle_launch,
            "Tap": self._handle_tap,
            "Type": self._handle_type,
            "Type_Name": self._handle_type,
            "Paste": self._handle_paste,
            "Paste_Stream": self._handle_paste_stream,
            "Swipe": self._handle_swipe,
            "Back": self._handle_back,
            "Home": self._handle_home,
            "Double Tap": self._handle_double_tap,
            "Long Press": self._handle_long_press,
            "Wait": self._handle_wait,
            "Take_over": self._handle_takeover,
            "Note": self._handle_note,
            "Call_API": self._handle_call_api,
            "Interact": self._handle_interact,
        }
        return handlers.get(action_name)

    def _convert_relative_to_absolute(
        self, element: list[int], screen_width: int, screen_height: int
    ) -> tuple[int, int]:
        """
        Convert model coordinates to absolute screen pixels.

        Supported input formats:
        - Relative floats in [0.0, 1.0] (e.g. 0.5, 0.5 for center)
        - Relative ints in [0, 1000] (project convention: 0-999, 0-1000 tolerated)
        - Absolute pixel ints (e.g. 540, 1200)
        """

        if not isinstance(element, (list, tuple)) or len(element) < 2:
            raise ValueError(f"Invalid element coordinates: {element!r}")

        try:
            x_value = float(element[0])
            y_value = float(element[1])
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid element coordinates: {element!r}") from e

        # 0-1 relative (common in some toolchains)
        if 0.0 <= x_value <= 1.0 and 0.0 <= y_value <= 1.0:
            x = int(x_value * screen_width)
            y = int(y_value * screen_height)
        # 0-1000 relative (project convention)
        elif 0.0 <= x_value <= 1000.0 and 0.0 <= y_value <= 1000.0:
            x = int(x_value / 1000.0 * screen_width)
            y = int(y_value / 1000.0 * screen_height)
        # already in pixels
        else:
            x = int(x_value)
            y = int(y_value)

        # Clamp to screen bounds to avoid out-of-range taps.
        max_x = max(0, int(screen_width) - 1)
        max_y = max(0, int(screen_height) - 1)
        x = max(0, min(max_x, x))
        y = max(0, min(max_y, y))
        return x, y

    def _handle_launch(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle app launch action."""
        app_name = action.get("app")
        if not app_name:
            return ActionResult(False, False, "No app name specified")

        device_factory = get_device_factory()
        success = device_factory.launch_app(app_name, self.device_id)
        if success:
            return ActionResult(True, False)
        return ActionResult(False, False, f"App not found: {app_name}")

    def _handle_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle tap action."""
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)

        # Check for sensitive operation
        if "message" in action:
            if not self.confirmation_callback(action["message"]):
                return ActionResult(
                    success=False,
                    should_finish=True,
                    message="User cancelled sensitive operation",
                )

        device_factory = get_device_factory()
        device_factory.tap(x, y, self.device_id)
        return ActionResult(True, False)

    def _handle_type(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle text input action."""
        text = action.get("text", "")

        device_factory = get_device_factory()

        # Switch to ADB keyboard
        original_ime = device_factory.detect_and_set_adb_keyboard(self.device_id)
        time.sleep(TIMING_CONFIG.action.keyboard_switch_delay)

        # Clear existing text and type new text
        device_factory.clear_text(self.device_id)
        time.sleep(TIMING_CONFIG.action.text_clear_delay)

        # Handle multiline text by splitting on newlines
        device_factory.type_text(text, self.device_id)
        time.sleep(TIMING_CONFIG.action.text_input_delay)

        # Restore original keyboard
        device_factory.restore_keyboard(original_ime, self.device_id)
        time.sleep(TIMING_CONFIG.action.keyboard_restore_delay)

        return ActionResult(True, False)

    def _handle_paste(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle paste via clipboard (fallback for apps that block ADB Keyboard)."""
        text = action.get("text", "")
        if text is None:
            text = ""
        text = str(text)

        clear_first = action.get("clear_first")
        if clear_first is None:
            clear_first = True
        clear_first = bool(clear_first)

        delay = action.get("delay")
        try:
            delay_s = float(delay) if delay is not None else 0.15
        except (TypeError, ValueError):
            delay_s = 0.15
        delay_s = max(0.0, min(2.0, delay_s))

        device_factory = get_device_factory()

        if clear_first:
            device_factory.clear_text(self.device_id)
            time.sleep(min(TIMING_CONFIG.action.text_clear_delay, 0.8))

        device_factory.set_clipboard(text, self.device_id)
        time.sleep(delay_s)
        device_factory.paste_clipboard(self.device_id)
        time.sleep(delay_s)

        return ActionResult(True, False)

    def _handle_paste_stream(self, action: dict, width: int, height: int) -> ActionResult:
        """
        Paste text in chunks via clipboard.

        Useful when apps/IME behave better with short pieces. If `chunks` is provided,
        it will be used as-is; otherwise we do a best-effort split by punctuation.
        """
        text = action.get("text", "")
        if text is None:
            text = ""
        text = str(text)

        clear_first = action.get("clear_first")
        if clear_first is None:
            clear_first = True
        clear_first = bool(clear_first)

        max_chunk_len = action.get("max_chunk_len") or 6
        try:
            max_chunk_len = int(max_chunk_len)
        except (TypeError, ValueError):
            max_chunk_len = 6
        max_chunk_len = max(1, min(50, max_chunk_len))

        delay = action.get("delay")
        try:
            delay_s = float(delay) if delay is not None else 0.15
        except (TypeError, ValueError):
            delay_s = 0.15
        delay_s = max(0.0, min(2.0, delay_s))

        chunks = action.get("chunks")
        pieces: list[str] = []
        if isinstance(chunks, list) and chunks:
            for c in chunks:
                if c is None:
                    continue
                pieces.append(str(c))
        else:
            # Split by punctuation and further chunk by max length.
            tokens = re.split(r"([，,。.!！?？；;：:、\\n])", text)
            merged: list[str] = []
            for tok in tokens:
                if tok == "":
                    continue
                if tok in {"，", ",", "。", ".", "!", "！", "?", "？", "；", ";", "：", ":", "、"}:
                    if merged:
                        merged[-1] += tok
                    else:
                        merged.append(tok)
                    continue
                if tok == "\\n" or tok == "\n":
                    # Keep newlines as-is; many inputs accept them.
                    merged.append("\n")
                    continue
                merged.append(tok)

            for seg in merged:
                if seg == "\n":
                    pieces.append(seg)
                    continue
                s = seg
                while len(s) > max_chunk_len:
                    pieces.append(s[:max_chunk_len])
                    s = s[max_chunk_len:]
                if s:
                    pieces.append(s)

        device_factory = get_device_factory()

        if clear_first:
            device_factory.clear_text(self.device_id)
            time.sleep(min(TIMING_CONFIG.action.text_clear_delay, 0.8))

        for piece in pieces:
            if piece == "":
                continue
            device_factory.set_clipboard(piece, self.device_id)
            time.sleep(delay_s)
            device_factory.paste_clipboard(self.device_id)
            time.sleep(delay_s)

        return ActionResult(True, False)

    def _handle_swipe(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle swipe action."""
        start = action.get("start")
        end = action.get("end")

        if not start or not end:
            return ActionResult(False, False, "Missing swipe coordinates")

        start_x, start_y = self._convert_relative_to_absolute(start, width, height)
        end_x, end_y = self._convert_relative_to_absolute(end, width, height)

        device_factory = get_device_factory()
        device_factory.swipe(start_x, start_y, end_x, end_y, device_id=self.device_id)
        return ActionResult(True, False)

    def _handle_back(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle back button action."""
        device_factory = get_device_factory()
        device_factory.back(self.device_id)
        return ActionResult(True, False)

    def _handle_home(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle home button action."""
        device_factory = get_device_factory()
        device_factory.home(self.device_id)
        return ActionResult(True, False)

    def _handle_double_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle double tap action."""
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)
        device_factory = get_device_factory()
        device_factory.double_tap(x, y, self.device_id)
        return ActionResult(True, False)

    def _handle_long_press(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle long press action."""
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)
        device_factory = get_device_factory()
        device_factory.long_press(x, y, device_id=self.device_id)
        return ActionResult(True, False)

    def _handle_wait(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle wait action."""
        duration_str = action.get("duration", "1 seconds")
        try:
            duration = float(duration_str.replace("seconds", "").strip())
        except ValueError:
            duration = 1.0

        time.sleep(duration)
        return ActionResult(True, False)

    def _handle_takeover(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle takeover request (login, captcha, etc.)."""
        message = action.get("message", "User intervention required")
        self.takeover_callback(message)
        return ActionResult(True, False)

    def _handle_note(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle note action (placeholder for content recording)."""
        # This action is typically used for recording page content
        # Implementation depends on specific requirements
        return ActionResult(True, False)

    def _handle_call_api(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle API call action (placeholder for summarization)."""
        # This action is typically used for content summarization
        # Implementation depends on specific requirements
        return ActionResult(True, False)

    def _handle_interact(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle interaction request (user choice needed)."""
        # This action signals that user input is needed
        return ActionResult(True, False, message="User interaction required")

    def _send_keyevent(self, keycode: str) -> None:
        """Send a keyevent to the device."""
        from phone_agent.device_factory import DeviceType, get_device_factory
        from phone_agent.hdc.connection import _run_hdc_command

        device_factory = get_device_factory()

        # Handle HDC devices with HarmonyOS-specific keyEvent command
        if device_factory.device_type == DeviceType.HDC:
            hdc_prefix = ["hdc", "-t", self.device_id] if self.device_id else ["hdc"]
            
            # Map common keycodes to HarmonyOS keyEvent codes
            # KEYCODE_ENTER (66) -> 2054 (HarmonyOS Enter key code)
            if keycode == "KEYCODE_ENTER" or keycode == "66":
                _run_hdc_command(
                    hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", "2054"],
                    capture_output=True,
                    text=True,
                )
            else:
                # For other keys, try to use the numeric code directly
                # If keycode is a string like "KEYCODE_ENTER", convert it
                try:
                    # Try to extract numeric code from string or use as-is
                    if keycode.startswith("KEYCODE_"):
                        # For now, only handle ENTER, other keys may need mapping
                        if "ENTER" in keycode:
                            _run_hdc_command(
                                hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", "2054"],
                                capture_output=True,
                                text=True,
                            )
                        else:
                            # Fallback to ADB-style command for unsupported keys
                            subprocess.run(
                                hdc_prefix + ["shell", "input", "keyevent", keycode],
                                capture_output=True,
                                text=True,
                            )
                    else:
                        # Assume it's a numeric code
                        _run_hdc_command(
                            hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", str(keycode)],
                            capture_output=True,
                            text=True,
                        )
                except Exception:
                    # Fallback to ADB-style command
                    subprocess.run(
                        hdc_prefix + ["shell", "input", "keyevent", keycode],
                        capture_output=True,
                        text=True,
                    )
        else:
            # ADB devices use standard input keyevent command
            cmd_prefix = ["adb", "-s", self.device_id] if self.device_id else ["adb"]
            subprocess.run(
                cmd_prefix + ["shell", "input", "keyevent", keycode],
                capture_output=True,
                text=True,
            )

    @staticmethod
    def _default_confirmation(message: str) -> bool:
        """Default confirmation callback using console input."""
        response = input(f"Sensitive operation: {message}\nConfirm? (Y/N): ")
        return response.upper() == "Y"

    @staticmethod
    def _default_takeover(message: str) -> None:
        """Default takeover callback using console input."""
        input(f"{message}\nPress Enter after completing manual operation...")


def parse_action(response: str) -> dict[str, Any]:
    """
    Parse action from model response.

    Args:
        response: Raw response string from the model.

    Returns:
        Parsed action dictionary.

    Raises:
        ValueError: If the response cannot be parsed.
    """

    def _normalize_action_text(text: str) -> str:
        # Normalize common full-width punctuation that may break parsing.
        #
        # NOTE: Do NOT normalize smart quotes to ASCII quotes here. Smart quotes
        # (e.g. “我的”) are often used inside string values; converting them to `"`
        # can break otherwise valid Python-like calls by introducing unescaped quotes.
        return text.replace("（", "(").replace("）", ")").replace("，", ",")

    def _extract_first_call_expression(text: str) -> str:
        """
        Extract the first `do(...)` or `finish(...)` call-like snippet.

        This helps when the model returns extra narration around the call.
        """
        text = text.strip()
        if not text:
            return text

        starts = []
        for needle in ("do(", "finish("):
            idx = text.find(needle)
            if idx != -1:
                starts.append(idx)
        if not starts:
            return text

        s = text[min(starts) :].lstrip()
        # Best-effort: cut at the matching closing parenthesis.
        depth = 0
        in_str: str | None = None
        escape = False
        for i, ch in enumerate(s):
            if in_str is not None:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == in_str:
                    in_str = None
                continue

            if ch in ("'", '"'):
                in_str = ch
                continue

            if ch == "(":
                depth += 1
                continue

            if ch == ")":
                depth -= 1
                if depth == 0:
                    return s[: i + 1]

        return s

    def _try_parse_with_ast(text: str) -> dict[str, Any]:
        # Escape control characters for valid Python syntax.
        text = text.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")

        tree = ast.parse(text, mode="eval")
        if not isinstance(tree.body, ast.Call):
            raise ValueError("Expected a function call")

        call = tree.body
        if not isinstance(call.func, ast.Name):
            raise ValueError("Expected a named function call")

        func_name = call.func.id
        if func_name not in ("do", "finish"):
            raise ValueError(f"Unexpected function: {func_name}")

        action: dict[str, Any] = {"_metadata": "do" if func_name == "do" else "finish"}
        for keyword in call.keywords:
            key = keyword.arg
            if key is None:
                raise ValueError("Positional kwargs are not supported")
            action[key] = ast.literal_eval(keyword.value)

        return action

    def _infer_app_name(text: str) -> str | None:
        try:
            from phone_agent.config.apps import APP_PACKAGES

            # Prefer longer names first to avoid partial matches.
            for name in sorted(APP_PACKAGES.keys(), key=len, reverse=True):
                if name and name in text:
                    return name
        except Exception:
            return None
        return None

    def _try_parse_with_regex(text: str) -> dict[str, Any] | None:
        """
        Fallback parser for slightly malformed model outputs.

        The official parser expects Python-like `do(action="...", ...)` strings.
        Some deployments may produce extra narration, full-width punctuation, or
        unescaped quotes in unused fields. This regex fallback extracts the
        essential arguments for supported actions.
        """
        text = text.strip()

        if "finish(" in text and text.lstrip().startswith("finish"):
            # Best-effort: extract message without requiring valid quoting.
            msg_idx = text.find("message=")
            if msg_idx != -1:
                msg = text[msg_idx + len("message=") :].strip()
                # Trim trailing ')'
                if msg.endswith(")"):
                    msg = msg[:-1].strip()
                # Strip surrounding quotes if present.
                if (msg.startswith('"') and msg.endswith('"')) or (
                    msg.startswith("'") and msg.endswith("'")
                ):
                    msg = msg[1:-1]
                return {"_metadata": "finish", "message": msg}
            return {"_metadata": "finish", "message": text}

        if "do(" not in text or not text.lstrip().startswith("do"):
            return None

        quote_chars = "\"'“”‘’"
        m_action = re.search(
            rf'action\s*=\s*[{quote_chars}]([^{quote_chars}]+)[{quote_chars}]',
            text,
        )
        if not m_action:
            return None
        action_name = m_action.group(1)

        action: dict[str, Any] = {"_metadata": "do", "action": action_name}

        if action_name == "Launch":
            m_app = re.search(
                rf'app\s*=\s*[{quote_chars}]([^{quote_chars}]+)[{quote_chars}]',
                text,
            )
            app_name = m_app.group(1) if m_app else _infer_app_name(text)
            if not app_name:
                return None
            action["app"] = app_name
            return action

        if action_name in ("Back", "Home"):
            return action

        if action_name == "Wait":
            m_duration = re.search(r'duration\s*=\s*["\']([^"\']+)["\']', text)
            if m_duration:
                action["duration"] = m_duration.group(1)
            return action

        if action_name in ("Tap", "Double Tap", "Long Press"):
            m_el = re.search(
                r"element\s*=\s*\[\s*(\d{1,4})\s*[,，]\s*(\d{1,4})\s*\]",
                text,
            )
            if not m_el:
                return None
            action["element"] = [int(m_el.group(1)), int(m_el.group(2))]

            # Only Tap uses message as a confirmation trigger; keep it if clean.
            if action_name == "Tap":
                m_msg = re.search(r'message\s*=\s*["\'](.*?)["\']', text, flags=re.S)
                if m_msg:
                    action["message"] = m_msg.group(1)
            return action

        if action_name == "Swipe":
            m_start = re.search(
                r"start\s*=\s*\[\s*(\d{1,4})\s*[,，]\s*(\d{1,4})\s*\]", text
            )
            m_end = re.search(
                r"end\s*=\s*\[\s*(\d{1,4})\s*[,，]\s*(\d{1,4})\s*\]", text
            )
            if not (m_start and m_end):
                return None
            action["start"] = [int(m_start.group(1)), int(m_start.group(2))]
            action["end"] = [int(m_end.group(1)), int(m_end.group(2))]
            return action

        if action_name == "Delegate":
            # Monitor-only action. Be forgiving about quoting (nested quotes are common).
            idx = text.find("task=")
            if idx == -1:
                return None
            val = text[idx + len("task=") :].strip()
            if val.endswith(")"):
                val = val[:-1].rstrip()
            if val:
                # Strip one layer of wrapping quotes if present; keep nested quotes.
                if val[0] in quote_chars:
                    q = val[0]
                    inner = val[1:]
                    if inner.endswith(q):
                        inner = inner[:-1]
                    else:
                        last = inner.rfind(q)
                        if last != -1:
                            inner = inner[:last]
                    val = inner
            action["task"] = val
            return action

        if action_name in ("Type", "Type_Name", "Paste", "Paste_Stream"):
            idx = text.find("text=")
            if idx == -1:
                return None
            val = text[idx + len("text=") :].strip()
            if val.endswith(")"):
                val = val[:-1].rstrip()
            if val and val[0] in quote_chars:
                q = val[0]
                inner = val[1:]
                if inner.endswith(q):
                    inner = inner[:-1]
                else:
                    last = inner.rfind(q)
                    if last != -1:
                        inner = inner[:last]
                val = inner
            action["text"] = val
            return action

        if action_name in ("Take_over", "Note", "Call_API", "Interact"):
            m_msg = re.search(r'message\s*=\s*["\'](.*?)["\']', text, flags=re.S)
            if m_msg:
                action["message"] = m_msg.group(1)
            m_instruction = re.search(
                r'instruction\s*=\s*["\'](.*?)["\']', text, flags=re.S
            )
            if m_instruction:
                action["instruction"] = m_instruction.group(1)
            return action

        return None

    try:
        response = _normalize_action_text(response)
        response = _extract_first_call_expression(response)

        if os.getenv("PHONE_AGENT_DEBUG_PARSE", "").strip() == "1":
            print(f"Parsing action: {response}")

        response = response.strip()
        if not response:
            raise ValueError("Empty action")

        # Try strict parsing first.
        try:
            return _try_parse_with_ast(response)
        except Exception:
            pass

        # Fallback to regex-based recovery.
        recovered = _try_parse_with_regex(response)
        if recovered is not None:
            return recovered

        raise ValueError(f"Failed to parse action: {response}")
    except Exception as e:
        raise ValueError(f"Failed to parse action: {e}")


def do(**kwargs) -> dict[str, Any]:
    """Helper function for creating 'do' actions."""
    kwargs["_metadata"] = "do"
    return kwargs


def finish(**kwargs) -> dict[str, Any]:
    """Helper function for creating 'finish' actions."""
    kwargs["_metadata"] = "finish"
    return kwargs

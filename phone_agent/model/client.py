"""Model client for AI inference using OpenAI-compatible API."""

import ast
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from phone_agent.config.i18n import get_message


@dataclass
class ModelConfig:
    """Configuration for the AI model."""

    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "autoglm-phone-9b"
    max_tokens: int = 3000
    temperature: float = 0.0
    top_p: float = 0.85
    frequency_penalty: float = 0.2
    extra_body: dict[str, Any] = field(default_factory=dict)
    fallback_models: list[str] = field(default_factory=list)
    lang: str = "cn"  # Language for UI messages: 'cn' or 'en'


@dataclass
class ModelResponse:
    """Response from the AI model."""

    thinking: str
    action: str
    raw_content: str
    # Performance metrics
    time_to_first_token: float | None = None  # Time to first token (seconds)
    time_to_thinking_end: float | None = None  # Time to thinking end (seconds)
    total_time: float | None = None  # Total inference time (seconds)


class ModelClient:
    """
    Client for interacting with OpenAI-compatible vision-language models.

    Args:
        config: Model configuration.
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        self.client = OpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            timeout=60.0,
            max_retries=2,
        )

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """
        Send a request to the model.

        Args:
            messages: List of message dictionaries in OpenAI format.

        Returns:
            ModelResponse containing thinking and action.

        Raises:
            ValueError: If the response cannot be parsed.
        """
        errors: list[dict[str, str | int | None]] = []
        candidates = self._resolve_model_candidates()

        for model_name in candidates:
            for attempt in range(self._resolve_attempt_limit(model_name)):
                try:
                    response = self._request_once(messages, model_name)
                    if model_name != self.config.model_name:
                        print(
                            f"[model-fallback] switched from {self.config.model_name} to {model_name}",
                            flush=True,
                        )
                        self.config.model_name = model_name
                    return response
                except Exception as error:
                    info = self._extract_error_info(error)
                    errors.append(
                        {
                            "model": model_name,
                            "code": info.get("code"),
                            "status": info.get("status"),
                            "message": info.get("message"),
                        }
                    )
                    if self._should_retry_error(info) and attempt + 1 < self._resolve_attempt_limit(model_name):
                        time.sleep(self._retry_delay_seconds(attempt))
                        continue
                    break

        raise RuntimeError(self._format_request_failure(errors))

    def _request_once(self, messages: list[dict[str, Any]], model_name: str) -> ModelResponse:
        start_time = time.time()
        time_to_first_token = None
        time_to_thinking_end = None

        stream = self.client.chat.completions.create(
            messages=messages,
            model=model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            extra_body=self.config.extra_body,
            stream=True,
        )

        raw_content = ""
        buffer = ""
        action_markers = ["finish(message=", "do(action="]
        in_action_phase = False
        first_token_received = False

        for chunk in stream:
            if len(chunk.choices) == 0:
                continue
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                raw_content += content

                if not first_token_received:
                    time_to_first_token = time.time() - start_time
                    first_token_received = True

                if in_action_phase:
                    continue

                buffer += content
                marker_found = False
                for marker in action_markers:
                    if marker in buffer:
                        thinking_part = buffer.split(marker, 1)[0]
                        print(thinking_part, end="", flush=True)
                        print()
                        in_action_phase = True
                        marker_found = True
                        if time_to_thinking_end is None:
                            time_to_thinking_end = time.time() - start_time
                        break

                if marker_found:
                    continue

                is_potential_marker = False
                for marker in action_markers:
                    for i in range(1, len(marker)):
                        if buffer.endswith(marker[:i]):
                            is_potential_marker = True
                            break
                    if is_potential_marker:
                        break

                if not is_potential_marker:
                    print(buffer, end="", flush=True)
                    buffer = ""

        total_time = time.time() - start_time
        thinking, action = self._parse_response(raw_content)

        lang = self.config.lang
        print()
        print("=" * 50)
        print(f"[timing] {get_message('performance_metrics', lang)}:")
        print("-" * 50)
        if time_to_first_token is not None:
            print(
                f"{get_message('time_to_first_token', lang)}: {time_to_first_token:.3f}s"
            )
        if time_to_thinking_end is not None:
            print(
                f"{get_message('time_to_thinking_end', lang)}:        {time_to_thinking_end:.3f}s"
            )
        print(
            f"{get_message('total_inference_time', lang)}:          {total_time:.3f}s"
        )
        print("=" * 50)

        return ModelResponse(
            thinking=thinking,
            action=action,
            raw_content=raw_content,
            time_to_first_token=time_to_first_token,
            time_to_thinking_end=time_to_thinking_end,
            total_time=total_time,
        )

    def _resolve_model_candidates(self) -> list[str]:
        candidates: list[str] = [self.config.model_name]
        if self.config.fallback_models:
            candidates.extend(self.config.fallback_models)

        if "api.z.ai" in (self.config.base_url or "") and self.config.model_name == "autoglm-phone-multilingual":
            candidates.extend(["glm-4.6v-flash", "glm-4.5v", "glm-4.6v-flashx"])

        deduped: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            candidate = candidate.strip()
            if not candidate or candidate in seen:
                continue
            deduped.append(candidate)
            seen.add(candidate)
        return deduped

    def _resolve_attempt_limit(self, model_name: str) -> int:
        if "api.z.ai" in (self.config.base_url or "") and model_name != self.config.model_name:
            return 2
        return 2

    def _extract_error_info(self, error: Exception) -> dict[str, str | int | None]:
        status = getattr(error, "status_code", None)
        body = getattr(error, "body", None)
        code = None
        message = str(error).strip()

        if isinstance(body, dict):
            err = body.get("error") if isinstance(body.get("error"), dict) else body
            if isinstance(err, dict):
                code = err.get("code")
                body_message = err.get("message")
                if isinstance(body_message, str) and body_message.strip():
                    message = body_message.strip()

        if code is None or not message:
            match = re.search(r"Error code:\s*(\d+)\s*-\s*(\{.*\})", str(error))
            if match:
                if code is None:
                    status = status or int(match.group(1))
                try:
                    parsed = ast.literal_eval(match.group(2))
                except (SyntaxError, ValueError):
                    parsed = None
                if isinstance(parsed, dict):
                    err = parsed.get("error")
                    if isinstance(err, dict):
                        code = err.get("code", code)
                        body_message = err.get("message")
                        if isinstance(body_message, str) and body_message.strip():
                            message = body_message.strip()

        normalized_code = str(code).strip() if code is not None else None
        normalized_message = message or "unknown error"

        if "Bad gateway" in normalized_message and status is None:
            status = 502

        return {
            "status": status if isinstance(status, int) else None,
            "code": normalized_code,
            "message": normalized_message,
        }

    def _should_retry_error(self, info: dict[str, str | int | None]) -> bool:
        code = str(info.get("code") or "").strip()
        status = info.get("status")
        message = str(info.get("message") or "").lower()

        if code == "1302":
            return True
        if isinstance(status, int) and status >= 500:
            return True
        return "bad gateway" in message or "timed out" in message

    def _retry_delay_seconds(self, attempt: int) -> float:
        return float(min(6, 2 * (attempt + 1)))

    def _format_request_failure(self, errors: list[dict[str, str | int | None]]) -> str:
        if not errors:
            return "Model request failed"

        parts: list[str] = []
        for item in errors:
            model = str(item.get("model") or "unknown-model")
            code = str(item.get("code") or "").strip()
            status = item.get("status")
            message = str(item.get("message") or "unknown error").strip()

            detail = message
            if code:
                detail = f"{code}: {detail}"
            elif isinstance(status, int):
                detail = f"HTTP {status}: {detail}"

            parts.append(f"{model} -> {detail}")

        if "api.z.ai" in (self.config.base_url or ""):
            parts.append(
                "z.ai 当前 key 对目标视觉模型可能未开通、已限流，或余额/资源包不足；可更换可用 key 或充值后重试"
            )

        return "Model request failed. Tried: " + "; ".join(parts)

    def _parse_response(self, content: str) -> tuple[str, str]:
        """
        Parse the model response into thinking and action parts.

        Parsing rules:
        1. If content contains 'finish(message=', everything before is thinking,
           everything from 'finish(message=' onwards is action.
        2. If rule 1 doesn't apply but content contains 'do(action=',
           everything before is thinking, everything from 'do(action=' onwards is action.
        3. Fallback: If content contains '<answer>', use legacy parsing with XML tags.
        4. Otherwise, return empty thinking and full content as action.

        Args:
            content: Raw response content.

        Returns:
            Tuple of (thinking, action).
        """
        # Rule 1: Check for finish(message=
        if "finish(message=" in content:
            parts = content.split("finish(message=", 1)
            thinking = parts[0].strip()
            action = "finish(message=" + parts[1]
            return thinking, action

        # Rule 2: Check for do(action=
        if "do(action=" in content:
            parts = content.split("do(action=", 1)
            thinking = parts[0].strip()
            action = "do(action=" + parts[1]
            return thinking, action

        # Rule 3: Fallback to legacy XML tag parsing
        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = parts[0].replace("<think>", "").replace("</think>", "").strip()
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action

        # Rule 4: No markers found, return content as action
        return "", content


class MessageBuilder:
    """Helper class for building conversation messages."""

    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        """Create a system message."""
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(
        text: str, image_base64: str | None = None
    ) -> dict[str, Any]:
        """
        Create a user message with optional image.

        Args:
            text: Text content.
            image_base64: Optional base64-encoded image.

        Returns:
            Message dictionary.
        """
        content = []

        if image_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                }
            )

        content.append({"type": "text", "text": text})

        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        """Create an assistant message."""
        return {"role": "assistant", "content": content}

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        """
        Remove image content from a message to save context space.

        Args:
            message: Message dictionary.

        Returns:
            Message with images removed.
        """
        if isinstance(message.get("content"), list):
            message["content"] = [
                item for item in message["content"] if item.get("type") == "text"
            ]
        return message

    @staticmethod
    def build_screen_info(current_app: str, **extra_info) -> str:
        """
        Build screen info string for the model.

        Args:
            current_app: Current app name.
            **extra_info: Additional info to include.

        Returns:
            JSON string with screen info.
        """
        info = {"current_app": current_app, **extra_info}
        return json.dumps(info, ensure_ascii=False)

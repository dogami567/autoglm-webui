"""Screenshot utilities for capturing Android device screen."""

import base64
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from io import BytesIO

from PIL import Image


@dataclass
class Screenshot:
    """Represents a captured screenshot."""

    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False


def _get_image_max_side() -> int:
    """
    Get the maximum image side length (pixels) used for model input.

    Large full-resolution phone screenshots can make multimodal inference
    extremely slow on some runtimes. We downscale the image before sending it
    to the model while keeping the original screen width/height for accurate
    coordinate mapping when executing actions.

    Set PHONE_AGENT_IMAGE_MAX_SIDE=0 to disable downscaling.
    """
    raw = os.getenv("PHONE_AGENT_IMAGE_MAX_SIDE", "1600").strip()
    try:
        return int(raw)
    except ValueError:
        return 1600


def _resize_for_model(img: Image.Image) -> Image.Image:
    """Resize image to speed up model inference while preserving aspect ratio."""
    max_side = _get_image_max_side()
    if max_side <= 0:
        return img

    width, height = img.size
    current_max_side = max(width, height)
    if current_max_side <= max_side:
        return img

    scale = max_side / float(current_max_side)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))

    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:  # Pillow<9.1
        resample = Image.LANCZOS

    return img.resize(new_size, resample=resample)


def get_screenshot(device_id: str | None = None, timeout: int = 10) -> Screenshot:
    """
    Capture a screenshot from the connected Android device.

    Args:
        device_id: Optional ADB device ID for multi-device setups.
        timeout: Timeout in seconds for screenshot operations.

    Returns:
        Screenshot object containing base64 data and dimensions.

    Note:
        If the screenshot fails (e.g., on sensitive screens like payment pages),
        a black fallback image is returned with is_sensitive=True.
    """
    temp_path = os.path.join(tempfile.gettempdir(), f"screenshot_{uuid.uuid4()}.png")
    adb_prefix = _get_adb_prefix(device_id)

    try:
        # Execute screenshot command
        result = subprocess.run(
            adb_prefix + ["shell", "screencap", "-p", "/sdcard/tmp.png"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Check for screenshot failure (sensitive screen)
        output = result.stdout + result.stderr
        if "Status: -1" in output or "Failed" in output:
            return _create_fallback_screenshot(is_sensitive=True)

        # Pull screenshot to local temp path
        subprocess.run(
            adb_prefix + ["pull", "/sdcard/tmp.png", temp_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if not os.path.exists(temp_path):
            return _create_fallback_screenshot(is_sensitive=False)

        # Read and encode image
        img = Image.open(temp_path)
        original_width, original_height = img.size
        img_for_model = _resize_for_model(img)

        buffered = BytesIO()
        img_for_model.save(buffered, format="PNG")
        base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Cleanup
        os.remove(temp_path)

        return Screenshot(
            base64_data=base64_data,
            width=original_width,
            height=original_height,
            is_sensitive=False,
        )

    except Exception as e:
        print(f"Screenshot error: {e}")
        return _create_fallback_screenshot(is_sensitive=False)


def _get_adb_prefix(device_id: str | None) -> list:
    """Get ADB command prefix with optional device specifier."""
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]


def _create_fallback_screenshot(is_sensitive: bool) -> Screenshot:
    """Create a black fallback image when screenshot fails."""
    default_width, default_height = 1080, 2400

    black_img = Image.new("RGB", (default_width, default_height), color="black")
    buffered = BytesIO()
    black_img.save(buffered, format="PNG")
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return Screenshot(
        base64_data=base64_data,
        width=default_width,
        height=default_height,
        is_sensitive=is_sensitive,
    )

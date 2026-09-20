from __future__ import annotations

import mss
from PIL import Image

from src.exceptions import CaptureError
from src.utils.geometry import Rect

from .screen_capture import ScreenCapture


class MSSScreenCapture(ScreenCapture):
    def capture_region(self, region: Rect) -> Image.Image:
        region = region.normalized()
        if not region.is_valid:
            raise CaptureError("The selected screen region is empty.")

        monitor = {
            "left": region.x,
            "top": region.y,
            "width": region.width,
            "height": region.height,
        }

        try:
            with mss.mss() as capture:
                shot = capture.grab(monitor)
                return Image.frombytes("RGB", shot.size, shot.rgb)
        except Exception as exc:
            raise CaptureError(f"Unable to capture the selected region: {exc}") from exc

from __future__ import annotations

import logging

import mss
from PIL import Image

from src.exceptions import CaptureError
from src.utils.geometry import Rect

from .screen_capture import ScreenCapture


class MSSScreenCapture(ScreenCapture):
    def __init__(self) -> None:
        self._logger = logging.getLogger("screen_translator.capture")

    def capture_region(self, region: Rect) -> Image.Image:
        region = region.normalized()
        if not region.is_valid:
            raise CaptureError("The selected screen region is empty.")

        try:
            with mss.mss() as capture:
                virtual = capture.monitors[0]
                bounds = Rect(
                    int(virtual["left"]),
                    int(virtual["top"]),
                    int(virtual["width"]),
                    int(virtual["height"]),
                )

                clamped = region.clamp(bounds)
                self._logger.info(
                    "MSS virtual desktop=(%d,%d %dx%d) requested=(%d,%d %dx%d) "
                    "capture=(%d,%d %dx%d)",
                    bounds.x,
                    bounds.y,
                    bounds.width,
                    bounds.height,
                    region.x,
                    region.y,
                    region.width,
                    region.height,
                    clamped.x,
                    clamped.y,
                    clamped.width,
                    clamped.height,
                )

                if not clamped.is_valid:
                    raise CaptureError(
                        "The selected region is outside the active Windows desktop. "
                        "The monitor configuration may have changed."
                    )

                monitor = {
                    "left": clamped.x,
                    "top": clamped.y,
                    "width": clamped.width,
                    "height": clamped.height,
                }

                shot = capture.grab(monitor)
                image = Image.frombytes("RGB", shot.size, shot.rgb)

                self._logger.info(
                    "Captured image size=%dx%d",
                    image.width,
                    image.height,
                )
                return image
        except CaptureError:
            raise
        except Exception as exc:
            raise CaptureError(f"Unable to capture the selected region: {exc}") from exc

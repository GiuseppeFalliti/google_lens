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

    @staticmethod
    def _bounds_from_monitor(monitor: dict) -> Rect:
        return Rect(
            int(monitor["left"]),
            int(monitor["top"]),
            int(monitor["width"]),
            int(monitor["height"]),
        )

    @staticmethod
    def _image_from_shot(shot) -> Image.Image:
        return Image.frombytes("RGB", shot.size, shot.rgb)

    def capture_region(self, region: Rect) -> Image.Image:
        region = region.normalized()
        if not region.is_valid:
            raise CaptureError("The selected screen region is empty.")

        try:
            with mss.mss() as capture:
                bounds = self._bounds_from_monitor(capture.monitors[0])
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

                shot = capture.grab(
                    {
                        "left": clamped.x,
                        "top": clamped.y,
                        "width": clamped.width,
                        "height": clamped.height,
                    }
                )
                image = self._image_from_shot(shot)
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

    def capture_virtual_desktop(self) -> tuple[Image.Image, Rect]:
        try:
            with mss.mss() as capture:
                monitor = capture.monitors[0]
                bounds = self._bounds_from_monitor(monitor)
                shot = capture.grab(monitor)
                image = self._image_from_shot(shot)

                self._logger.info(
                    "Captured virtual desktop bounds=(%d,%d %dx%d) image=%dx%d",
                    bounds.x,
                    bounds.y,
                    bounds.width,
                    bounds.height,
                    image.width,
                    image.height,
                )
                return image, bounds
        except Exception as exc:
            raise CaptureError(f"Unable to capture the full desktop: {exc}") from exc

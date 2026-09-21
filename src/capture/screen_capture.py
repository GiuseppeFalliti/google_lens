from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from src.utils.geometry import Rect


class ScreenCapture(ABC):
    @abstractmethod
    def capture_region(self, region: Rect) -> Image.Image:
        """Capture a desktop region using absolute physical desktop coordinates."""
        raise NotImplementedError

    @abstractmethod
    def capture_virtual_desktop(self) -> tuple[Image.Image, Rect]:
        """Capture all active monitors and return image plus physical desktop bounds."""
        raise NotImplementedError

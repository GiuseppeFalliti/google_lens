from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from src.utils.geometry import Rect


class ScreenCapture(ABC):
    @abstractmethod
    def capture_region(self, region: Rect) -> Image.Image:
        """Capture a desktop region using absolute virtual-desktop coordinates."""
        raise NotImplementedError

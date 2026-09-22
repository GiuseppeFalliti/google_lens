from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from .models import OCRResult


class OCREngine(ABC):
    @abstractmethod
    def set_language(self, language: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def recognize(self, image: Image.Image) -> OCRResult:
        raise NotImplementedError

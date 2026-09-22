from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np
from PIL import Image

from src.exceptions import OCRError

from .base_ocr import OCREngine
from .models import OCRResult, OCRTextBlock


_PADDLE_LANG_MAP = {
    "en": "en",
    "it": "it",
    "fr": "fr",
    "de": "german",
    "es": "es",
    "pt": "pt",
}


class PaddleOCREngine(OCREngine):
    """Lazy PaddleOCR 2.10 adapter.

    PaddleOCR 2.x is intentionally used for the Windows MVP because its direct
    OCR API does not import PaddleX/ModelScope/PyTorch in the OCR process.
    """

    def __init__(self, language: str = "en", min_confidence: float = 0.35) -> None:
        self._language = language.strip().lower()
        self._min_confidence = min_confidence
        self._engines: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger("screen_translator.ocr")

    def set_language(self, language: str) -> None:
        self._language = language.strip().lower()

    def _get_engine(self) -> Any:
        paddle_language = _PADDLE_LANG_MAP.get(self._language, self._language)

        with self._lock:
            if paddle_language in self._engines:
                return self._engines[paddle_language]

            try:
                # Windows workaround: PaddleOCR 2.10 imports Albumentations,
                # which imports PyTorch. Loading Paddle/PaddleOCR before Torch
                # can trigger WinError 127 on torch\\lib\\shm.dll.
                # Import Torch first so its native DLLs are resolved before
                # PaddlePaddle initializes.
                import torch  # noqa: F401
                from paddleocr import PaddleOCR

                self._logger.info(
                    "Initializing PaddleOCR 2.x language=%s device=cpu mkldnn=off",
                    paddle_language,
                )
                engine = PaddleOCR(
                    lang=paddle_language,
                    use_angle_cls=False,
                    use_gpu=False,
                    enable_mkldnn=False,
                    show_log=False,
                )
            except Exception as exc:
                self._logger.exception(
                    "PaddleOCR initialization failed for language=%s",
                    paddle_language,
                )
                raise OCRError(
                    "Unable to initialize PaddleOCR. "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

            self._engines[paddle_language] = engine
            return engine

    @staticmethod
    def _looks_like_line(value: Any) -> bool:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return False
        box, recognition = value
        if not isinstance(box, (list, tuple)):
            return False
        if not isinstance(recognition, (list, tuple)) or len(recognition) < 2:
            return False
        return isinstance(recognition[0], str)

    @classmethod
    def _iter_lines(cls, value: Any):
        if cls._looks_like_line(value):
            yield value
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                yield from cls._iter_lines(item)

    @staticmethod
    def _normalise_box(raw_box: Any) -> list[tuple[float, float]]:
        if hasattr(raw_box, "tolist"):
            raw_box = raw_box.tolist()

        points: list[tuple[float, float]] = []
        try:
            for point in raw_box:
                if hasattr(point, "tolist"):
                    point = point.tolist()
                if len(point) >= 2:
                    points.append((float(point[0]), float(point[1])))
        except Exception:
            return []
        return points

    def recognize(self, image: Image.Image) -> OCRResult:
        try:
            array = np.asarray(image.convert("RGB"))
            # PaddleOCR/OpenCV uses BGR internally for ndarray input.
            bgr = array[:, :, ::-1].copy()
            raw_result = self._get_engine().ocr(bgr, cls=False)
        except OCRError:
            raise
        except Exception as exc:
            self._logger.exception("PaddleOCR inference failed.")
            raise OCRError(
                f"PaddleOCR inference failed. {type(exc).__name__}: {exc}"
            ) from exc

        blocks: list[OCRTextBlock] = []

        for line in self._iter_lines(raw_result):
            raw_box, recognition = line
            text = " ".join(str(recognition[0]).split()).strip()
            if not text:
                continue

            try:
                confidence = float(recognition[1])
            except (TypeError, ValueError, IndexError):
                confidence = 0.0

            if confidence < self._min_confidence:
                continue

            blocks.append(
                OCRTextBlock(
                    text=text,
                    confidence=confidence,
                    box=self._normalise_box(raw_box),
                )
            )

        blocks.sort(key=lambda block: (round(block.top / 8) * 8, block.left))
        full_text = "\n".join(block.text for block in blocks).strip()
        self._logger.debug("OCR detected %d text blocks.", len(blocks))
        return OCRResult(blocks=blocks, full_text=full_text)

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
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
    """Lazy, reusable PaddleOCR adapter compatible with the v3 predict API."""

    def __init__(self, language: str = "en", min_confidence: float = 0.35) -> None:
        self._language = language
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
                from paddleocr import PaddleOCR

                engine = PaddleOCR(
                    lang=paddle_language,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                )
            except Exception as exc:
                raise OCRError(
                    "Unable to initialize PaddleOCR. Verify PaddleOCR/PaddlePaddle "
                    f"installation and the language model '{paddle_language}'."
                ) from exc

            self._engines[paddle_language] = engine
            return engine

    @staticmethod
    def _to_mapping(result: Any) -> Mapping[str, Any]:
        if isinstance(result, Mapping):
            return result

        for attr_name in ("json", "to_dict"):
            attr = getattr(result, attr_name, None)
            if attr is None:
                continue
            try:
                value = attr() if callable(attr) else attr
            except Exception:
                continue
            if isinstance(value, Mapping):
                return value

        try:
            value = dict(result)
            if isinstance(value, Mapping):
                return value
        except Exception:
            pass

        return {}

    @staticmethod
    def _normalise_box(raw_box: Any) -> list[tuple[float, float]]:
        if raw_box is None:
            return []

        if hasattr(raw_box, "tolist"):
            raw_box = raw_box.tolist()

        try:
            if (
                len(raw_box) == 4
                and all(isinstance(value, (int, float, np.number)) for value in raw_box)
            ):
                x1, y1, x2, y2 = (float(value) for value in raw_box)
                return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

            points: list[tuple[float, float]] = []
            for point in raw_box:
                if hasattr(point, "tolist"):
                    point = point.tolist()
                if len(point) >= 2:
                    points.append((float(point[0]), float(point[1])))
            return points
        except Exception:
            return []

    def recognize(self, image: Image.Image) -> OCRResult:
        try:
            array = np.asarray(image.convert("RGB"))
            raw_results = list(self._get_engine().predict(array))
        except OCRError:
            raise
        except Exception as exc:
            raise OCRError(f"PaddleOCR inference failed: {exc}") from exc

        blocks: list[OCRTextBlock] = []

        for raw_result in raw_results:
            data = self._to_mapping(raw_result)
            if "res" in data and isinstance(data["res"], Mapping):
                data = data["res"]

            def pick(*keys: str):
                for key in keys:
                    value = data.get(key)
                    if value is not None:
                        return value
                return []

            texts = pick("rec_texts", "texts")
            scores = pick("rec_scores", "scores")
            boxes = pick("rec_polys", "rec_boxes", "dt_polys")

            if hasattr(texts, "tolist"):
                texts = texts.tolist()
            if hasattr(scores, "tolist"):
                scores = scores.tolist()
            if hasattr(boxes, "tolist"):
                boxes = boxes.tolist()

            for index, text in enumerate(texts):
                cleaned = " ".join(str(text).split()).strip()
                if not cleaned:
                    continue

                try:
                    confidence = float(scores[index]) if index < len(scores) else 1.0
                except (TypeError, ValueError):
                    confidence = 0.0

                if confidence < self._min_confidence:
                    continue

                raw_box = boxes[index] if index < len(boxes) else []
                blocks.append(
                    OCRTextBlock(
                        text=cleaned,
                        confidence=confidence,
                        box=self._normalise_box(raw_box),
                    )
                )

        blocks.sort(key=lambda block: (round(block.top / 8) * 8, block.left))
        full_text = "\n".join(block.text for block in blocks).strip()
        self._logger.debug("OCR detected %d text blocks.", len(blocks))
        return OCRResult(blocks=blocks, full_text=full_text)

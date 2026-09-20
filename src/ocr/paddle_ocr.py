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


# PP-OCRv5 mobile models are intentionally used for the desktop MVP.
# They are considerably lighter than PP-OCRv6 medium and avoid current
# Windows/CPU issues seen in the default PaddleOCR 3.7 static/oneDNN path.
_REC_MODEL_MAP = {
    "en": "en_PP-OCRv5_mobile_rec",
    "it": "latin_PP-OCRv5_mobile_rec",
    "fr": "latin_PP-OCRv5_mobile_rec",
    "de": "latin_PP-OCRv5_mobile_rec",
    "es": "latin_PP-OCRv5_mobile_rec",
    "pt": "latin_PP-OCRv5_mobile_rec",
}

_DET_MODEL = "PP-OCRv5_mobile_det"


class PaddleOCREngine(OCREngine):
    """Lazy, reusable PaddleOCR adapter for Windows desktop OCR."""

    def __init__(self, language: str = "en", min_confidence: float = 0.35) -> None:
        self._language = language.strip().lower()
        self._min_confidence = min_confidence
        self._engines: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger("screen_translator.ocr")

    def set_language(self, language: str) -> None:
        self._language = language.strip().lower()

    def _recognition_model(self) -> str:
        return _REC_MODEL_MAP.get(self._language, "latin_PP-OCRv5_mobile_rec")

    def _get_engine(self) -> Any:
        recognition_model = self._recognition_model()
        cache_key = f"{_DET_MODEL}:{recognition_model}"

        with self._lock:
            if cache_key in self._engines:
                return self._engines[cache_key]

            try:
                from paddleocr import PaddleOCR

                self._logger.info(
                    "Initializing PaddleOCR detection=%s recognition=%s "
                    "engine=paddle_dynamic device=cpu mkldnn=off",
                    _DET_MODEL,
                    recognition_model,
                )

                engine = PaddleOCR(
                    text_detection_model_name=_DET_MODEL,
                    text_recognition_model_name=recognition_model,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    device="cpu",
                    engine="paddle_dynamic",
                    enable_mkldnn=False,
                )
            except Exception as exc:
                self._logger.exception(
                    "PaddleOCR initialization failed for detection=%s recognition=%s",
                    _DET_MODEL,
                    recognition_model,
                )
                raise OCRError(
                    "Unable to initialize PaddleOCR. "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

            self._engines[cache_key] = engine
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
            self._logger.exception("PaddleOCR inference failed.")
            raise OCRError(
                f"PaddleOCR inference failed. {type(exc).__name__}: {exc}"
            ) from exc

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

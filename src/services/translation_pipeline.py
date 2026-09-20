from __future__ import annotations

from dataclasses import dataclass
import logging
import statistics
import threading
import time
from collections.abc import Callable

from src.capture.screen_capture import ScreenCapture
from src.exceptions import NoTextDetectedError, OCRError, OperationCancelled
from src.ocr.base_ocr import OCREngine
from src.ocr.models import OCRResult, OCRTextBlock
from src.translation.translation_service import TranslationService
from src.utils.geometry import Rect
from src.utils.image_utils import OCRImageVariant, build_ocr_variants


StatusCallback = Callable[[str], None]


@dataclass(slots=True)
class TranslationResult:
    source_text: str
    translated_text: str
    region: Rect
    ocr_result: OCRResult
    provider: str
    capture_seconds: float
    ocr_seconds: float
    translation_seconds: float


class TranslationPipeline:
    def __init__(
        self,
        screen_capture: ScreenCapture,
        ocr_engine: OCREngine,
        translation_service: TranslationService,
    ) -> None:
        self._capture = screen_capture
        self._ocr = ocr_engine
        self._translations = translation_service
        self._cancelled = threading.Event()
        self._logger = logging.getLogger("screen_translator.pipeline")

    def cancel(self) -> None:
        self._cancelled.set()

    def reset_cancelled(self) -> None:
        self._cancelled.clear()

    def _check_cancelled(self) -> None:
        if self._cancelled.is_set():
            raise OperationCancelled("Translation was cancelled.")

    @staticmethod
    def build_translation_text(ocr_result: OCRResult) -> str:
        """Build natural text for the translator from OCR line/block output."""
        block_texts = [
            " ".join(block.text.split())
            for block in ocr_result.blocks
            if block.text and block.text.strip()
        ]

        if block_texts:
            return " ".join(block_texts).strip()

        return " ".join(ocr_result.full_text.split()).strip()

    @staticmethod
    def score_ocr_result(ocr_result: OCRResult) -> float:
        """Score an OCR candidate using confidence plus useful text coverage.

        Confidence remains the dominant factor, while a modest coverage bonus
        prevents a very short, high-confidence fragment from beating a more
        complete reading of the selected sentence.
        """
        if ocr_result.is_empty or not ocr_result.blocks:
            return -1.0

        confidences = [
            max(0.0, min(1.0, float(block.confidence)))
            for block in ocr_result.blocks
        ]
        average_confidence = sum(confidences) / len(confidences)
        median_confidence = statistics.median(confidences)

        normalized_text = " ".join(ocr_result.full_text.split())
        alphanumeric_chars = sum(character.isalnum() for character in normalized_text)
        coverage = min(1.0, alphanumeric_chars / 80.0)
        block_coverage = min(1.0, len(ocr_result.blocks) / 5.0)

        return (
            average_confidence * 0.60
            + median_confidence * 0.25
            + coverage * 0.10
            + block_coverage * 0.05
        )

    @staticmethod
    def rescale_ocr_result(ocr_result: OCRResult, scale: float) -> OCRResult:
        """Map OCR boxes from an upscaled variant back to the selected region."""
        if scale == 1.0:
            return ocr_result

        blocks = [
            OCRTextBlock(
                text=block.text,
                confidence=block.confidence,
                box=[
                    (point_x / scale, point_y / scale)
                    for point_x, point_y in block.box
                ],
            )
            for block in ocr_result.blocks
        ]
        return OCRResult(blocks=blocks, full_text=ocr_result.full_text)

    def _recognize_best_variant(
        self,
        variants: list[OCRImageVariant],
        status_callback: StatusCallback | None = None,
    ) -> OCRResult:
        best_result: OCRResult | None = None
        best_score = -1.0
        best_variant = ""
        last_error: OCRError | None = None

        for index, variant in enumerate(variants, start=1):
            self._check_cancelled()
            if status_callback:
                status_callback(
                    f"Recognizing text... ({index}/{len(variants)})"
                )

            try:
                result = self._ocr.recognize(variant.image)
            except OCRError as exc:
                last_error = exc
                self._logger.warning(
                    "OCR variant %s failed: %s",
                    variant.name,
                    exc,
                )
                continue

            score = self.score_ocr_result(result)
            self._logger.debug(
                "OCR candidate variant=%s score=%.4f blocks=%d text=%r",
                variant.name,
                score,
                len(result.blocks),
                result.full_text,
            )

            if score > best_score:
                best_result = self.rescale_ocr_result(result, variant.scale)
                best_score = score
                best_variant = variant.name

        if best_result is None:
            if last_error is not None:
                raise last_error
            return OCRResult(blocks=[], full_text="")

        self._logger.info(
            "Selected OCR variant=%s score=%.4f",
            best_variant,
            best_score,
        )
        return best_result

    def translate_region(
        self,
        region: Rect,
        source_language: str,
        target_language: str,
        provider_name: str,
        status_callback: StatusCallback | None = None,
    ) -> TranslationResult:
        self._check_cancelled()
        if status_callback:
            status_callback("Capturing selected region...")

        started = time.perf_counter()
        image = self._capture.capture_region(region)
        capture_seconds = time.perf_counter() - started

        self._check_cancelled()
        if status_callback:
            status_callback("Preparing OCR variants...")

        self._ocr.set_language(source_language)
        variants = build_ocr_variants(image)
        del image

        started = time.perf_counter()
        try:
            ocr_result = self._recognize_best_variant(
                variants,
                status_callback=status_callback,
            )
        finally:
            for variant in variants:
                variant.image.close()
        ocr_seconds = time.perf_counter() - started

        self._check_cancelled()

        if ocr_result.is_empty:
            raise NoTextDetectedError("No text detected in the selected area.")

        translation_text = self.build_translation_text(ocr_result)
        if not translation_text:
            raise NoTextDetectedError("No usable text detected in the selected area.")

        self._logger.debug("OCR raw text: %r", ocr_result.full_text)
        self._logger.debug("OCR normalized text: %r", translation_text)

        if status_callback:
            status_callback("Translating...")

        started = time.perf_counter()
        translated = self._translations.translate(
            text=translation_text,
            source_language=source_language,
            target_language=target_language,
            provider_name=provider_name,
        )
        translation_seconds = time.perf_counter() - started

        self._check_cancelled()
        return TranslationResult(
            source_text=translation_text,
            translated_text=translated,
            region=region,
            ocr_result=ocr_result,
            provider=provider_name,
            capture_seconds=capture_seconds,
            ocr_seconds=ocr_seconds,
            translation_seconds=translation_seconds,
        )

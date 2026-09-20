from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import statistics
import threading
import time
from collections.abc import Callable

from wordfreq import zipf_frequency

from src.capture.screen_capture import ScreenCapture
from src.exceptions import NoTextDetectedError, OCRError, OperationCancelled
from src.ocr.base_ocr import OCREngine
from src.ocr.models import OCRResult, OCRTextBlock
from src.translation.translation_service import TranslationService
from src.utils.geometry import Rect
from src.utils.image_utils import OCRImageVariant, build_ocr_variants


StatusCallback = Callable[[str], None]

_WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)
_WORDFREQ_LANG_MAP = {
    "en": "en",
    "it": "it",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "pt": "pt",
}


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
        block_texts = [
            " ".join(block.text.split())
            for block in ocr_result.blocks
            if block.text and block.text.strip()
        ]
        if block_texts:
            return " ".join(block_texts).strip()
        return " ".join(ocr_result.full_text.split()).strip()

    @staticmethod
    def lexical_quality(text: str, language: str) -> float:
        """Estimate whether recognized tokens look like real words.

        This is not used to rewrite OCR output. It only helps choose between
        competing OCR readings, e.g. preferring ABSENCE over ABSne when their
        visual confidence is otherwise similar.
        """
        lang = _WORDFREQ_LANG_MAP.get(language.lower())
        if lang is None:
            return 0.5

        words = _WORD_RE.findall(text)
        words = [word for word in words if len(word) > 1]
        if not words:
            return 0.0

        scores: list[float] = []
        for word in words:
            frequency = zipf_frequency(word.casefold(), lang)
            # Typical real words are mostly in Zipf 2-7. Normalize that useful
            # range while still allowing uncommon game/dialogue vocabulary.
            scores.append(max(0.0, min(1.0, (frequency - 1.0) / 5.0)))

        return sum(scores) / len(scores)

    @staticmethod
    def suspicious_case_penalty(text: str) -> float:
        penalty = 0.0
        words = _WORD_RE.findall(text)
        for word in words:
            if len(word) < 4:
                continue
            if word.islower() or word.isupper() or word.istitle():
                continue
            # OCR artifacts often create tokens such as ABSne / SUPPosED.
            penalty += 0.025
        return min(0.10, penalty)

    @classmethod
    def score_ocr_result(
        cls,
        ocr_result: OCRResult,
        source_language: str = "en",
    ) -> float:
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
        coverage = min(1.0, alphanumeric_chars / 90.0)
        block_coverage = min(1.0, len(ocr_result.blocks) / 5.0)
        lexical = cls.lexical_quality(normalized_text, source_language)
        case_penalty = cls.suspicious_case_penalty(normalized_text)

        return (
            average_confidence * 0.42
            + median_confidence * 0.18
            + coverage * 0.16
            + lexical * 0.19
            + block_coverage * 0.05
            - case_penalty
        )

    @staticmethod
    def rescale_ocr_result(ocr_result: OCRResult, scale: float) -> OCRResult:
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
        source_language: str,
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

            score = self.score_ocr_result(result, source_language)
            lexical = self.lexical_quality(result.full_text, source_language)
            self._logger.info(
                "OCR candidate variant=%s score=%.4f lexical=%.4f blocks=%d text=%r",
                variant.name,
                score,
                lexical,
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
            "Selected OCR variant=%s score=%.4f text=%r",
            best_variant,
            best_score,
            best_result.full_text,
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
                source_language=source_language,
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

        self._logger.info("OCR normalized text: %r", translation_text)

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

        self._logger.info("Translation output: %r", translated)

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

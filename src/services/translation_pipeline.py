from __future__ import annotations

from dataclasses import dataclass
import logging
import threading
import time
from collections.abc import Callable

from src.capture.screen_capture import ScreenCapture
from src.exceptions import NoTextDetectedError, OperationCancelled
from src.ocr.base_ocr import OCREngine
from src.ocr.models import OCRResult
from src.translation.translation_service import TranslationService
from src.utils.geometry import Rect
from src.utils.image_utils import preprocess_for_ocr


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
        """Build natural text for the translator from OCR line/block output.

        OCR engines often return one block per visual line. Passing those
        newlines directly to lightweight translators such as Argos can make
        each line look like a separate sentence, producing poor translations.

        Keep the original OCRResult untouched for coordinates/debugging, but
        collapse its blocks into a single whitespace-normalized sentence for
        translation.
        """
        block_texts = [
            " ".join(block.text.split())
            for block in ocr_result.blocks
            if block.text and block.text.strip()
        ]

        if block_texts:
            return " ".join(block_texts).strip()

        # Defensive fallback for OCR engines that only populate full_text.
        return " ".join(ocr_result.full_text.split()).strip()

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
            status_callback("Recognizing text...")

        self._ocr.set_language(source_language)
        image = preprocess_for_ocr(image)
        started = time.perf_counter()
        ocr_result = self._ocr.recognize(image)
        ocr_seconds = time.perf_counter() - started

        del image
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

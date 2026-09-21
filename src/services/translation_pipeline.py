from __future__ import annotations

from dataclasses import dataclass
import logging
import math
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
from src.utils.image_utils import (
    OCRImageVariant,
    build_ocr_variants,
    preprocess_for_ocr,
)


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


@dataclass(slots=True)
class ScreenTranslationItem:
    source_text: str
    translated_text: str
    region: Rect
    confidence: float


@dataclass(slots=True)
class FullScreenTranslationResult:
    items: list[ScreenTranslationItem]
    provider: str
    capture_seconds: float
    ocr_seconds: float
    translation_seconds: float
    desktop_region: Rect


@dataclass(slots=True)
class _OCRGroup:
    blocks: list[OCRTextBlock]
    rect: Rect


class TranslationPipeline:
    MAX_FULLSCREEN_REGIONS = 60

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
    def normalize_case_for_translation(text: str, source_language: str) -> str:
        normalized = " ".join(text.split()).strip()
        if not normalized:
            return normalized

        alphabetic = [char for char in normalized if char.isalpha()]
        if not alphabetic:
            return normalized

        uppercase_ratio = sum(char.isupper() for char in alphabetic) / len(alphabetic)
        words = _WORD_RE.findall(normalized)
        suspicious_mixed_case = any(
            len(word) >= 4
            and not word.islower()
            and not word.isupper()
            and not word.istitle()
            for word in words
        )

        if uppercase_ratio < 0.65 and not suspicious_mixed_case:
            return normalized

        lowered = normalized.lower()
        if source_language.lower() == "en":
            lowered = re.sub(r"\bi\b", "I", lowered)

        def capitalize_sentence(match: re.Match[str]) -> str:
            return match.group(1) + match.group(2).upper()

        return re.sub(
            r"(^|[.!?]\s+)([a-zà-öø-ÿ])",
            capitalize_sentence,
            lowered,
        )

    @staticmethod
    def lexical_quality(text: str, language: str) -> float:
        lang = _WORDFREQ_LANG_MAP.get(language.lower())
        if lang is None:
            return 0.5

        words = [word for word in _WORD_RE.findall(text) if len(word) > 1]
        if not words:
            return 0.0

        scores: list[float] = []
        for word in words:
            frequency = zipf_frequency(word.casefold(), lang)
            scores.append(max(0.0, min(1.0, (frequency - 1.0) / 5.0)))
        return sum(scores) / len(scores)

    @staticmethod
    def suspicious_case_penalty(text: str) -> float:
        penalty = 0.0
        for word in _WORD_RE.findall(text):
            if len(word) < 4:
                continue
            if word.islower() or word.isupper() or word.istitle():
                continue
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
                status_callback(f"Recognizing text... ({index}/{len(variants)})")

            try:
                result = self._ocr.recognize(variant.image)
            except OCRError as exc:
                last_error = exc
                self._logger.warning("OCR variant %s failed: %s", variant.name, exc)
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

    @staticmethod
    def _block_rect(block: OCRTextBlock) -> Rect | None:
        if not block.box:
            return None
        xs = [point[0] for point in block.box]
        ys = [point[1] for point in block.box]
        left = math.floor(min(xs))
        top = math.floor(min(ys))
        right = math.ceil(max(xs))
        bottom = math.ceil(max(ys))
        rect = Rect(left, top, right - left, bottom - top)
        return rect if rect.is_valid else None

    @staticmethod
    def _union_rect(first: Rect, second: Rect) -> Rect:
        left = min(first.x, second.x)
        top = min(first.y, second.y)
        right = max(first.right, second.right)
        bottom = max(first.bottom, second.bottom)
        return Rect(left, top, right - left, bottom - top)

    @staticmethod
    def _should_merge(group_rect: Rect, block_rect: Rect) -> bool:
        vertical_gap = block_rect.y - group_rect.bottom
        reference_height = max(1, min(group_rect.height, block_rect.height))

        overlap = max(
            0,
            min(group_rect.right, block_rect.right)
            - max(group_rect.x, block_rect.x),
        )
        min_width = max(1, min(group_rect.width, block_rect.width))
        horizontal_overlap_ratio = overlap / min_width

        center_a = group_rect.x + group_rect.width / 2.0
        center_b = block_rect.x + block_rect.width / 2.0
        center_distance = abs(center_a - center_b)
        horizontal_near = center_distance <= max(group_rect.width, block_rect.width) * 0.55

        return (
            -reference_height * 0.45 <= vertical_gap <= reference_height * 1.65
            and (horizontal_overlap_ratio >= 0.18 or horizontal_near)
        )

    @classmethod
    def _group_ocr_blocks(cls, blocks: list[OCRTextBlock]) -> list[_OCRGroup]:
        entries: list[tuple[OCRTextBlock, Rect]] = []
        for block in blocks:
            rect = cls._block_rect(block)
            if rect is not None and block.text.strip():
                entries.append((block, rect))

        entries.sort(key=lambda item: (item[1].y, item[1].x))
        groups: list[_OCRGroup] = []

        for block, rect in entries:
            target: _OCRGroup | None = None
            for group in reversed(groups[-8:]):
                if cls._should_merge(group.rect, rect):
                    target = group
                    break

            if target is None:
                groups.append(_OCRGroup(blocks=[block], rect=rect))
            else:
                target.blocks.append(block)
                target.rect = cls._union_rect(target.rect, rect)

        groups.sort(key=lambda group: (group.rect.y, group.rect.x))
        return groups

    @staticmethod
    def _group_text(group: _OCRGroup) -> str:
        blocks = sorted(group.blocks, key=lambda block: (block.top, block.left))
        return " ".join(
            " ".join(block.text.split())
            for block in blocks
            if block.text.strip()
        ).strip()

    @staticmethod
    def _group_confidence(group: _OCRGroup) -> float:
        if not group.blocks:
            return 0.0
        return sum(float(block.confidence) for block in group.blocks) / len(group.blocks)

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
        image.close()

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
        translation_input = self.normalize_case_for_translation(
            translation_text,
            source_language,
        )
        self._logger.info("Translation input: %r", translation_input)

        if status_callback:
            status_callback("Translating...")

        started = time.perf_counter()
        translated = self._translations.translate(
            text=translation_input,
            source_language=source_language,
            target_language=target_language,
            provider_name=provider_name,
        )
        translation_seconds = time.perf_counter() - started

        self._logger.info("Translation output: %r", translated)
        self._check_cancelled()

        return TranslationResult(
            source_text=translation_input,
            translated_text=translated,
            region=region,
            ocr_result=ocr_result,
            provider=provider_name,
            capture_seconds=capture_seconds,
            ocr_seconds=ocr_seconds,
            translation_seconds=translation_seconds,
        )

    def translate_full_screen(
        self,
        source_language: str,
        target_language: str,
        provider_name: str,
        status_callback: StatusCallback | None = None,
    ) -> FullScreenTranslationResult:
        self._check_cancelled()
        if status_callback:
            status_callback("Capturing full screen...")

        started = time.perf_counter()
        image, desktop_region = self._capture.capture_virtual_desktop()
        capture_seconds = time.perf_counter() - started

        self._ocr.set_language(source_language)
        if status_callback:
            status_callback("Recognizing screen text...")

        started = time.perf_counter()
        try:
            ocr_result = self._ocr.recognize(image)

            # Full-screen upscaling would consume a large amount of memory.
            # Retry once with a same-size enhanced image only when the normal
            # pass found nothing.
            if ocr_result.is_empty:
                enhanced = preprocess_for_ocr(
                    image,
                    grayscale=True,
                    autocontrast=True,
                    contrast=1.25,
                    sharpness=1.35,
                )
                try:
                    ocr_result = self._ocr.recognize(enhanced)
                finally:
                    enhanced.close()
        finally:
            image.close()
        ocr_seconds = time.perf_counter() - started

        self._check_cancelled()
        if ocr_result.is_empty:
            raise NoTextDetectedError("No text detected on the screen.")

        groups = self._group_ocr_blocks(ocr_result.blocks)
        if not groups:
            raise NoTextDetectedError("No positioned text regions detected on the screen.")

        if len(groups) > self.MAX_FULLSCREEN_REGIONS:
            self._logger.warning(
                "Full-screen OCR produced %d groups; limiting overlays to %d.",
                len(groups),
                self.MAX_FULLSCREEN_REGIONS,
            )
            groups = groups[: self.MAX_FULLSCREEN_REGIONS]

        prepared: list[tuple[_OCRGroup, str]] = []
        for group in groups:
            text = self._group_text(group)
            if len(text) < 2:
                continue
            text = self.normalize_case_for_translation(text, source_language)
            if text:
                prepared.append((group, text))

        if not prepared:
            raise NoTextDetectedError("No usable text detected on the screen.")

        self._logger.info(
            "Full-screen OCR blocks=%d groups=%d translated_regions=%d",
            len(ocr_result.blocks),
            len(groups),
            len(prepared),
        )

        if status_callback:
            status_callback(f"Translating {len(prepared)} screen regions...")

        translation_inputs = [text for _, text in prepared]
        started = time.perf_counter()
        translations = self._translations.translate_many(
            texts=translation_inputs,
            source_language=source_language,
            target_language=target_language,
            provider_name=provider_name,
        )
        translation_seconds = time.perf_counter() - started

        self._check_cancelled()
        items: list[ScreenTranslationItem] = []

        for (group, source_text), translated_text in zip(prepared, translations):
            relative = group.rect
            physical = Rect(
                desktop_region.x + relative.x,
                desktop_region.y + relative.y,
                relative.width,
                relative.height,
            ).clamp(desktop_region)

            if not physical.is_valid:
                continue

            items.append(
                ScreenTranslationItem(
                    source_text=source_text,
                    translated_text=translated_text,
                    region=physical,
                    confidence=self._group_confidence(group),
                )
            )

        if not items:
            raise NoTextDetectedError("No valid translated regions could be positioned.")

        self._logger.info(
            "Full-screen translation completed provider=%s regions=%d capture=%.3fs "
            "ocr=%.3fs translation=%.3fs",
            provider_name,
            len(items),
            capture_seconds,
            ocr_seconds,
            translation_seconds,
        )

        return FullScreenTranslationResult(
            items=items,
            provider=provider_name,
            capture_seconds=capture_seconds,
            ocr_seconds=ocr_seconds,
            translation_seconds=translation_seconds,
            desktop_region=desktop_region,
        )

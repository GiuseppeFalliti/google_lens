from __future__ import annotations

from PySide6.QtWidgets import QWidget

from src.utils.geometry import Rect

from .multi_translation_overlay import MultiTranslationOverlay
from .translation_overlay import TranslationOverlay


class OverlayManager:
    def __init__(self) -> None:
        self._overlay: QWidget | None = None

    @property
    def is_visible(self) -> bool:
        return self._overlay is not None and self._overlay.isVisible()

    def show_translation(self, text: str, region: Rect, opacity: float) -> None:
        self.close()
        overlay = TranslationOverlay(text=text, region=region, opacity=opacity)
        overlay.closed.connect(self._clear_if_current)
        self._overlay = overlay
        overlay.show_overlay()

    def show_translations(
        self,
        translations: list[tuple[str, Rect]],
        opacity: float,
    ) -> None:
        if isinstance(self._overlay, MultiTranslationOverlay):
            self._overlay.update_translations(translations)
            if not self._overlay.isVisible():
                self._overlay.show_overlay()
            return

        self.close()
        overlay = MultiTranslationOverlay(
            translations=translations,
            opacity=opacity,
        )
        overlay.closed.connect(self._clear_if_current)
        self._overlay = overlay
        overlay.show_overlay()

    def _clear_if_current(self) -> None:
        if self._overlay is not None and not self._overlay.isVisible():
            self._overlay.deleteLater()
            self._overlay = None

    def close(self) -> None:
        overlay = self._overlay
        self._overlay = None
        if overlay is not None:
            overlay.close()
            overlay.deleteLater()

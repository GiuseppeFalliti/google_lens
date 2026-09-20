from __future__ import annotations

from src.utils.geometry import Rect

from .translation_overlay import TranslationOverlay


class OverlayManager:
    def __init__(self) -> None:
        self._overlay: TranslationOverlay | None = None

    @property
    def is_visible(self) -> bool:
        return self._overlay is not None and self._overlay.isVisible()

    def show_translation(self, text: str, region: Rect, opacity: float) -> None:
        self.close()
        overlay = TranslationOverlay(text=text, region=region, opacity=opacity)
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

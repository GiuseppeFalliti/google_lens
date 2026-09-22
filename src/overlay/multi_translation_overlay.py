from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QWidget

from src.utils.display_geometry import physical_region_to_qt_logical
from src.utils.geometry import Rect
from src.utils.window_capture import exclude_widget_from_capture


class MultiTranslationOverlay(QWidget):
    closed = Signal()

    def __init__(
        self,
        translations: list[tuple[str, Rect]],
        opacity: float = 0.82,
    ) -> None:
        super().__init__(None)
        self._opacity = min(1.0, max(0.30, opacity))
        self._logger = logging.getLogger("screen_translator.overlay")
        self._labels: list[QLabel] = []

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        screens = QGuiApplication.screens()
        if not screens:
            raise RuntimeError("No active display was found.")

        desktop = screens[0].geometry()
        for screen in screens[1:]:
            desktop = desktop.united(screen.geometry())
        self._desktop = desktop
        self.setGeometry(desktop)

        self.update_translations(translations)

    def _stylesheet(self) -> str:
        alpha = int(self._opacity * 255)
        return (
            "QLabel {"
            f"background-color: rgba(0, 0, 0, {alpha});"
            "color: white;"
            "border-radius: 6px;"
            "padding: 7px;"
            "font-size: 13px;"
            "}"
        )

    def update_translations(
        self,
        translations: list[tuple[str, Rect]],
    ) -> None:
        for label in self._labels:
            label.deleteLater()
        self._labels.clear()

        stylesheet = self._stylesheet()

        for text, physical_region in translations:
            logical_region = physical_region_to_qt_logical(physical_region)
            label = QLabel(text, self)
            label.setWordWrap(True)
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            label.setStyleSheet(stylesheet)
            self._position_label(label, logical_region)
            label.show()
            self._labels.append(label)

            self._logger.debug(
                "Live overlay physical=(%d,%d %dx%d) -> qt=(%d,%d %dx%d)",
                physical_region.x,
                physical_region.y,
                physical_region.width,
                physical_region.height,
                logical_region.x,
                logical_region.y,
                logical_region.width,
                logical_region.height,
            )

        self.update()

    def _position_label(self, label: QLabel, region: Rect) -> None:
        x = region.x - self._desktop.x()
        y = region.y - self._desktop.y()

        width = max(110, region.width)
        width = min(width, 460)
        width = min(width, max(90, self._desktop.width() - max(0, x)))

        label.setFixedWidth(width)
        label.adjustSize()

        height = max(region.height, label.sizeHint().height(), 34)
        height = min(height, max(34, self._desktop.height() - max(0, y)))

        x = min(max(0, x), max(0, self._desktop.width() - width))
        y = min(max(0, y), max(0, self._desktop.height() - height))
        label.setGeometry(x, y, width, height)

    def show_overlay(self) -> None:
        self.show()
        exclude_widget_from_capture(self)
        self.raise_()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.closed.emit()
        super().closeEvent(event)

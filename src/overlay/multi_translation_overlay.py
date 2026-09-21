from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QLabel, QWidget

from src.utils.display_geometry import physical_region_to_qt_logical
from src.utils.geometry import Rect


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
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        screens = QGuiApplication.screens()
        if not screens:
            raise RuntimeError("No active display was found.")

        desktop = screens[0].geometry()
        for screen in screens[1:]:
            desktop = desktop.united(screen.geometry())
        self._desktop = desktop
        self.setGeometry(desktop)

        alpha = int(self._opacity * 255)
        stylesheet = (
            "QLabel {"
            f"background-color: rgba(0, 0, 0, {alpha});"
            "color: white;"
            "border-radius: 6px;"
            "padding: 7px;"
            "font-size: 13px;"
            "}"
        )

        for text, physical_region in translations:
            logical_region = physical_region_to_qt_logical(physical_region)
            label = QLabel(text, self)
            label.setWordWrap(True)
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            label.setStyleSheet(stylesheet)
            self._position_label(label, logical_region)
            self._labels.append(label)

            self._logger.info(
                "Full-screen overlay physical=(%d,%d %dx%d) -> qt=(%d,%d %dx%d)",
                physical_region.x,
                physical_region.y,
                physical_region.width,
                physical_region.height,
                logical_region.x,
                logical_region.y,
                logical_region.width,
                logical_region.height,
            )

    def _position_label(self, label: QLabel, region: Rect) -> None:
        x = region.x - self._desktop.x()
        y = region.y - self._desktop.y()

        width = max(120, region.width)
        width = min(width, 460)
        width = min(width, max(100, self._desktop.width() - max(0, x)))

        label.setFixedWidth(width)
        label.adjustSize()

        height = max(region.height, label.sizeHint().height(), 38)
        height = min(height, max(38, self._desktop.height() - max(0, y)))

        x = min(max(0, x), max(0, self._desktop.width() - width))
        y = min(max(0, y), max(0, self._desktop.height() - height))
        label.setGeometry(x, y, width, height)

    def show_overlay(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        point = event.position().toPoint()
        if not any(label.geometry().contains(point) for label in self._labels):
            self.close()
            return
        super().mousePressEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.closed.emit()
        super().closeEvent(event)

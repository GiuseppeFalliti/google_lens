from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QLabel, QWidget

from src.utils.display_geometry import physical_region_to_qt_logical
from src.utils.geometry import Rect


class TranslationOverlay(QWidget):
    closed = Signal()

    def __init__(self, text: str, region: Rect, opacity: float = 0.82) -> None:
        super().__init__(None)
        self._capture_region = region
        self._region = physical_region_to_qt_logical(region)
        self._opacity = min(1.0, max(0.30, opacity))
        self._logger = logging.getLogger("screen_translator.overlay")

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

        self._logger.info(
            "Overlay mapping physical=(%d,%d %dx%d) -> qt=(%d,%d %dx%d) "
            "qt_desktop=(%d,%d %dx%d)",
            self._capture_region.x,
            self._capture_region.y,
            self._capture_region.width,
            self._capture_region.height,
            self._region.x,
            self._region.y,
            self._region.width,
            self._region.height,
            self._desktop.x(),
            self._desktop.y(),
            self._desktop.width(),
            self._desktop.height(),
        )

        self._label = QLabel(text, self)
        self._label.setWordWrap(True)
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        alpha = int(self._opacity * 255)
        self._label.setStyleSheet(
            "QLabel {"
            f"background-color: rgba(0, 0, 0, {alpha});"
            "color: white;"
            "border-radius: 8px;"
            "padding: 12px;"
            "font-size: 15px;"
            "}"
        )

        self._position_label()

    def _position_label(self) -> None:
        x = self._region.x - self._desktop.x()
        y = self._region.y - self._desktop.y()

        width = max(220, self._region.width)
        width = min(width, max(220, self._desktop.width() - max(0, x)))

        self._label.setFixedWidth(width)
        self._label.adjustSize()
        height = max(self._region.height, self._label.sizeHint().height(), 64)
        height = min(height, max(64, self._desktop.height() - max(0, y)))

        x = min(max(0, x), max(0, self._desktop.width() - width))
        y = min(max(0, y), max(0, self._desktop.height() - height))
        self._label.setGeometry(x, y, width, height)

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
        if not self._label.geometry().contains(event.position().toPoint()):
            self.close()
            return
        super().mousePressEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.closed.emit()
        super().closeEvent(event)

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import sys

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from src.utils.geometry import Rect


class RegionSelector(QWidget):
    region_selected = Signal(object)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__(None)
        self._start: QPoint | None = None
        self._current: QPoint | None = None
        self._capture_start: tuple[int, int] | None = None
        self._logger = logging.getLogger("screen_translator.selector")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        screens = QGuiApplication.screens()
        if not screens:
            raise RuntimeError("No active display was found.")

        geometry = screens[0].geometry()
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())

        self._desktop_geometry = geometry
        self.setGeometry(geometry)

        for screen in screens:
            screen_geometry = screen.geometry()
            self._logger.info(
                "Qt screen name=%s geometry=(%d,%d %dx%d) dpr=%.3f logical_dpi=%.2f",
                screen.name(),
                screen_geometry.x(),
                screen_geometry.y(),
                screen_geometry.width(),
                screen_geometry.height(),
                screen.devicePixelRatio(),
                screen.logicalDotsPerInch(),
            )

    @staticmethod
    def _native_cursor_position() -> tuple[int, int] | None:
        """Return Windows physical desktop coordinates for the cursor.

        Qt mouse positions are device-independent pixels. MSS expects Windows
        physical desktop pixels. On a laptop display using 125/150% scaling,
        using Qt coordinates directly captures the wrong part of the screen.
        """
        if sys.platform != "win32":
            return None

        point = wintypes.POINT()
        if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
            return None
        return int(point.x), int(point.y)

    def begin(self) -> None:
        self._start = None
        self._current = None
        self._capture_start = None
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def selection_rect(self) -> QRect:
        if self._start is None or self._current is None:
            return QRect()
        return QRect(self._start, self._current).normalized()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        selected = self.selection_rect()
        if selected.isValid() and not selected.isEmpty():
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selected, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(80, 170, 255), 2))
            painter.drawRect(selected)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._current = self._start
            self._capture_start = self._native_cursor_position()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._start is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or self._start is None:
            return

        self._current = event.position().toPoint()
        selected = self.selection_rect()
        capture_end = self._native_cursor_position()
        self.hide()

        if selected.width() < 2 or selected.height() < 2:
            self._start = None
            self._current = None
            self._capture_start = None
            self.cancelled.emit()
            return

        if self._capture_start is not None and capture_end is not None:
            region = Rect.from_points(
                self._capture_start[0],
                self._capture_start[1],
                capture_end[0],
                capture_end[1],
            )
            coordinate_source = "win32-physical"
        else:
            # Non-Windows/fallback path using Qt logical coordinates.
            global_x = self._desktop_geometry.x() + selected.x()
            global_y = self._desktop_geometry.y() + selected.y()
            region = Rect(global_x, global_y, selected.width(), selected.height())
            coordinate_source = "qt-logical-fallback"

        self._logger.info(
            "Selected capture region source=%s region=(%d,%d %dx%d) "
            "qt_selection=(%d,%d %dx%d)",
            coordinate_source,
            region.x,
            region.y,
            region.width,
            region.height,
            selected.x(),
            selected.y(),
            selected.width(),
            selected.height(),
        )

        self._start = None
        self._current = None
        self._capture_start = None
        QTimer.singleShot(100, lambda: self.region_selected.emit(region))

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self._start = None
            self._current = None
            self._capture_start = None
            self.cancelled.emit()
            return
        super().keyPressEvent(event)

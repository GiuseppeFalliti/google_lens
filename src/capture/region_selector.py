from __future__ import annotations

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

    def begin(self) -> None:
        self._start = None
        self._current = None
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
        self.hide()

        if selected.width() < 2 or selected.height() < 2:
            self._start = None
            self._current = None
            self.cancelled.emit()
            return

        global_x = self._desktop_geometry.x() + selected.x()
        global_y = self._desktop_geometry.y() + selected.y()
        region = Rect(global_x, global_y, selected.width(), selected.height())

        self._start = None
        self._current = None
        QTimer.singleShot(80, lambda: self.region_selected.emit(region))

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self._start = None
            self._current = None
            self.cancelled.emit()
            return
        super().keyPressEvent(event)

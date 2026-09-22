from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon


class TrayManager(QObject):
    translate_requested = Signal()
    live_scan_requested = Signal()
    stop_live_scan_requested = Signal()
    open_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.tray = QSystemTrayIcon(parent)
        icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray.setIcon(icon)
        self.tray.setToolTip("Screen Translator")

        menu = QMenu()

        translate_action = QAction("Translate region", menu)
        translate_action.triggered.connect(self.translate_requested)
        menu.addAction(translate_action)

        live_action = QAction("Start / reselect live scan area", menu)
        live_action.triggered.connect(self.live_scan_requested)
        menu.addAction(live_action)

        self.stop_live_action = QAction("Stop live scan", menu)
        self.stop_live_action.setEnabled(False)
        self.stop_live_action.triggered.connect(self.stop_live_scan_requested)
        menu.addAction(self.stop_live_action)

        menu.addSeparator()

        open_action = QAction("Open", menu)
        open_action.triggered.connect(self.open_requested)
        menu.addAction(open_action)

        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self.settings_requested)
        menu.addAction(settings_action)

        menu.addSeparator()

        exit_action = QAction("Exit", menu)
        exit_action.triggered.connect(self.exit_requested)
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_requested.emit()

    def set_live_mode(self, active: bool) -> None:
        self.stop_live_action.setEnabled(active)

    def show(self) -> None:
        self.tray.show()

    def notify(self, title: str, message: str, milliseconds: int = 3500) -> None:
        self.tray.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            milliseconds,
        )

    def hide(self) -> None:
        self.tray.hide()

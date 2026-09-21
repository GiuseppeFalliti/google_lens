from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import AppSettings
from src.utils.window_capture import exclude_widget_from_capture

from .settings_page import SettingsPage
from .status_widget import StatusWidget


class MainWindow(QMainWindow):
    translate_requested = Signal()
    live_scan_requested = Signal()
    stop_live_scan_requested = Signal()
    settings_saved = Signal(object)
    install_argos_requested = Signal(str, str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._allow_close = False
        self._live_mode = False

        self.setWindowTitle("Screen Translator")
        self.resize(720, 610)

        central = QWidget()
        layout = QVBoxLayout(central)

        title = QLabel("Screen Translator")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Translate one selected region, or select a larger reading area and "
            "keep it translated automatically while the content changes or scrolls."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.settings_page = SettingsPage(settings)
        self.settings_page.install_argos_requested.connect(
            self.install_argos_requested
        )
        layout.addWidget(self.settings_page, 1)

        translate_actions = QHBoxLayout()

        self.translate_button = QPushButton("Translate selected region")
        self.translate_button.setToolTip(
            "Select one rectangular area and translate it once."
        )
        self.translate_button.clicked.connect(self.translate_requested)
        translate_actions.addWidget(self.translate_button)

        self.live_scan_button = QPushButton("Start live scan area")
        self.live_scan_button.setToolTip(
            "Select a large reading area. Text inside it is re-scanned automatically "
            "when the content changes, for example while scrolling a manga."
        )
        self.live_scan_button.clicked.connect(self.live_scan_requested)
        translate_actions.addWidget(self.live_scan_button)

        self.stop_live_button = QPushButton("Stop live scan")
        self.stop_live_button.setEnabled(False)
        self.stop_live_button.clicked.connect(self.stop_live_scan_requested)
        translate_actions.addWidget(self.stop_live_button)

        layout.addLayout(translate_actions)

        save_actions = QHBoxLayout()
        save_actions.addStretch(1)
        self.save_button = QPushButton("Save settings")
        self.save_button.clicked.connect(self._save)
        save_actions.addWidget(self.save_button)
        layout.addLayout(save_actions)

        self.status = StatusWidget()
        layout.addWidget(self.status)

        self.setCentralWidget(central)

        # Keep our own GUI out of MSS captures while still leaving it visible
        # and usable during live scan mode.
        exclude_widget_from_capture(self)

    def _save(self) -> None:
        try:
            settings = self.settings_page.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid settings", str(exc))
            return
        self.settings_saved.emit(settings)

    def set_status(self, text: str) -> None:
        self.status.set_status(text)

    def set_processing(self, processing: bool) -> None:
        self.translate_button.setEnabled(not processing)
        self.live_scan_button.setEnabled(not processing or self._live_mode)

    def set_live_mode(self, active: bool) -> None:
        self._live_mode = active
        self.stop_live_button.setEnabled(active)
        self.live_scan_button.setText(
            "Reselect live scan area" if active else "Start live scan area"
        )
        self.translate_button.setEnabled(True)
        self.live_scan_button.setEnabled(True)

    def show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Screen Translator", message)

    def show_information(self, message: str) -> None:
        QMessageBox.information(self, "Screen Translator", message)

    def allow_close(self) -> None:
        self._allow_close = True

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        self.hide()

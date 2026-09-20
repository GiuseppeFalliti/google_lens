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

from .settings_page import SettingsPage
from .status_widget import StatusWidget


class MainWindow(QMainWindow):
    translate_requested = Signal()
    settings_saved = Signal(object)
    install_argos_requested = Signal(str, str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._allow_close = False

        self.setWindowTitle("Screen Translator")
        self.resize(620, 560)

        central = QWidget()
        layout = QVBoxLayout(central)

        title = QLabel("Screen Translator")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Select a screen region, extract its text locally, and translate it."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.settings_page = SettingsPage(settings)
        self.settings_page.install_argos_requested.connect(
            self.install_argos_requested
        )
        layout.addWidget(self.settings_page, 1)

        actions = QHBoxLayout()
        self.translate_button = QPushButton("Translate screen region")
        self.translate_button.clicked.connect(self.translate_requested)
        actions.addWidget(self.translate_button)

        self.save_button = QPushButton("Save settings")
        self.save_button.clicked.connect(self._save)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)

        self.status = StatusWidget()
        layout.addWidget(self.status)

        self.setCentralWidget(central)

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

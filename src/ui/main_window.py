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
    full_screen_translate_requested = Signal()
    settings_saved = Signal(object)
    install_argos_requested = Signal(str, str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._allow_close = False

        self.setWindowTitle("Screen Translator")
        self.resize(680, 590)

        central = QWidget()
        layout = QVBoxLayout(central)

        title = QLabel("Screen Translator")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Translate a selected region or scan the whole screen and place "
            "translations over detected text."
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
            "Select one rectangular area and translate it."
        )
        self.translate_button.clicked.connect(self.translate_requested)
        translate_actions.addWidget(self.translate_button)

        self.full_screen_button = QPushButton("Translate full screen")
        self.full_screen_button.setToolTip(
            "Scan the entire desktop and create translation boxes over detected text."
        )
        self.full_screen_button.clicked.connect(
            self.full_screen_translate_requested
        )
        translate_actions.addWidget(self.full_screen_button)

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
        self.full_screen_button.setEnabled(not processing)

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

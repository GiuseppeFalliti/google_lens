from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import AppSettings, LANGUAGES, PROVIDERS


class SettingsPage(QWidget):
    install_argos_requested = Signal(str, str)

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.load(settings)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        translation_group = QGroupBox("Translation")
        translation_form = QFormLayout(translation_group)

        self.source_combo = QComboBox()
        self.target_combo = QComboBox()
        for label, code in LANGUAGES.items():
            self.source_combo.addItem(label, code)
            self.target_combo.addItem(label, code)

        self.provider_combo = QComboBox()
        for label, code in PROVIDERS.items():
            self.provider_combo.addItem(label, code)

        translation_form.addRow("From:", self.source_combo)
        translation_form.addRow("To:", self.target_combo)
        translation_form.addRow("Provider:", self.provider_combo)

        self.provider_stack = QStackedWidget()
        self.provider_stack.addWidget(self._create_argos_panel())
        self.provider_stack.addWidget(self._create_azure_panel())
        self.provider_stack.addWidget(self._create_deepl_panel())
        self.provider_stack.addWidget(self._create_libre_panel())
        translation_form.addRow("Provider settings:", self.provider_stack)

        root.addWidget(translation_group)

        general_group = QGroupBox("General")
        general_form = QFormLayout(general_group)

        self.hotkey_edit = QLineEdit()
        self.hotkey_edit.setPlaceholderText("CTRL+SHIFT+T")
        general_form.addRow("Hotkey:", self.hotkey_edit)

        opacity_container = QWidget()
        opacity_layout = QHBoxLayout(opacity_container)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_label = QLabel()
        self.opacity_slider.valueChanged.connect(
            lambda value: self.opacity_label.setText(f"{value}%")
        )
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        general_form.addRow("Overlay opacity:", opacity_container)

        self.start_minimized = QCheckBox("Start minimized to tray")
        general_form.addRow("", self.start_minimized)

        root.addWidget(general_group)
        root.addStretch(1)

        self.provider_combo.currentIndexChanged.connect(self._sync_provider_panel)

    def _create_argos_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.argos_status = QLabel("Offline translation model")
        self.argos_download = QPushButton("Download selected model")
        self.argos_download.clicked.connect(
            lambda: self.install_argos_requested.emit(
                str(self.source_combo.currentData()),
                str(self.target_combo.currentData()),
            )
        )
        layout.addWidget(self.argos_status, 1)
        layout.addWidget(self.argos_download)
        return panel

    def _create_azure_panel(self) -> QWidget:
        panel = QWidget()
        form = QFormLayout(panel)
        form.setContentsMargins(0, 0, 0, 0)

        self.azure_key = QLineEdit()
        self.azure_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.azure_key.setPlaceholderText("Azure Translator key")

        self.azure_region = QLineEdit()
        self.azure_region.setPlaceholderText(
            "Optional for global Translator resources"
        )

        self.azure_endpoint = QLineEdit()
        self.azure_endpoint.setPlaceholderText(
            "https://api.cognitive.microsofttranslator.com"
        )

        form.addRow("API key:", self.azure_key)
        form.addRow("Region:", self.azure_region)
        form.addRow("Endpoint:", self.azure_endpoint)
        return panel

    def _create_deepl_panel(self) -> QWidget:
        panel = QWidget()
        form = QFormLayout(panel)
        form.setContentsMargins(0, 0, 0, 0)
        self.deepl_key = QLineEdit()
        self.deepl_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepl_url = QLineEdit()
        form.addRow("API key:", self.deepl_key)
        form.addRow("Endpoint:", self.deepl_url)
        return panel

    def _create_libre_panel(self) -> QWidget:
        panel = QWidget()
        form = QFormLayout(panel)
        form.setContentsMargins(0, 0, 0, 0)
        self.libre_url = QLineEdit()
        self.libre_key = QLineEdit()
        self.libre_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Base URL:", self.libre_url)
        form.addRow("API key (optional):", self.libre_key)
        return panel

    def _sync_provider_panel(self) -> None:
        code = str(self.provider_combo.currentData())
        index = {
            "argos": 0,
            "azure": 1,
            "deepl": 2,
            "libretranslate": 3,
        }.get(code, 0)
        self.provider_stack.setCurrentIndex(index)

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def load(self, settings: AppSettings) -> None:
        self._set_combo_data(self.source_combo, settings.source_language)
        self._set_combo_data(self.target_combo, settings.target_language)
        self._set_combo_data(self.provider_combo, settings.translation_provider)

        self.hotkey_edit.setText(settings.global_hotkey)
        self.opacity_slider.setValue(round(settings.overlay_opacity * 100))
        self.start_minimized.setChecked(settings.start_minimized)

        self.azure_key.setText(settings.azure_api_key)
        self.azure_region.setText(settings.azure_region)
        self.azure_endpoint.setText(settings.azure_endpoint)

        self.libre_url.setText(settings.libretranslate_url)
        self.libre_key.setText(settings.libretranslate_api_key)
        self.deepl_key.setText(settings.deepl_api_key)
        self.deepl_url.setText(settings.deepl_api_url)
        self._sync_provider_panel()

    def values(self) -> AppSettings:
        return AppSettings(
            source_language=str(self.source_combo.currentData()),
            target_language=str(self.target_combo.currentData()),
            translation_provider=str(self.provider_combo.currentData()),
            global_hotkey=self.hotkey_edit.text(),
            overlay_opacity=self.opacity_slider.value() / 100.0,
            start_minimized=self.start_minimized.isChecked(),

            azure_api_key=self.azure_key.text(),
            azure_region=self.azure_region.text(),
            azure_endpoint=self.azure_endpoint.text(),

            libretranslate_url=self.libre_url.text(),
            libretranslate_api_key=self.libre_key.text(),
            deepl_api_key=self.deepl_key.text(),
            deepl_api_url=self.deepl_url.text(),
        ).validated()

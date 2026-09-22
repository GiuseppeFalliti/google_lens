from __future__ import annotations

from PySide6.QtCore import QSettings

from .settings import AppSettings


class SettingsManager:
    def __init__(self, qsettings: QSettings | None = None) -> None:
        self._settings = qsettings or QSettings("ScreenTranslator", "ScreenTranslator")

    @staticmethod
    def _as_bool(value: object, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def load(self) -> AppSettings:
        defaults = AppSettings()
        settings = AppSettings(
            source_language=str(
                self._settings.value("translation/source_language", defaults.source_language)
            ),
            target_language=str(
                self._settings.value("translation/target_language", defaults.target_language)
            ),
            translation_provider=str(
                self._settings.value("translation/provider", defaults.translation_provider)
            ),
            global_hotkey=str(
                self._settings.value("general/global_hotkey", defaults.global_hotkey)
            ),
            overlay_opacity=float(
                self._settings.value("overlay/opacity", defaults.overlay_opacity)
            ),
            start_minimized=self._as_bool(
                self._settings.value("general/start_minimized", defaults.start_minimized),
                defaults.start_minimized,
            ),
            azure_api_key=str(self._settings.value("azure/api_key", "")),
            azure_region=str(self._settings.value("azure/region", "")),
            azure_endpoint=str(
                self._settings.value("azure/endpoint", defaults.azure_endpoint)
            ),
            libretranslate_url=str(
                self._settings.value(
                    "libretranslate/base_url", defaults.libretranslate_url
                )
            ),
            libretranslate_api_key=str(
                self._settings.value("libretranslate/api_key", "")
            ),
            deepl_api_key=str(self._settings.value("deepl/api_key", "")),
            deepl_api_url=str(
                self._settings.value("deepl/api_url", defaults.deepl_api_url)
            ),
            ocr_min_confidence=float(
                self._settings.value(
                    "ocr/min_confidence", defaults.ocr_min_confidence
                )
            ),
        )
        try:
            return settings.validated()
        except ValueError:
            return defaults

    def save(self, settings: AppSettings) -> AppSettings:
        settings = settings.validated()
        self._settings.setValue("translation/source_language", settings.source_language)
        self._settings.setValue("translation/target_language", settings.target_language)
        self._settings.setValue("translation/provider", settings.translation_provider)
        self._settings.setValue("general/global_hotkey", settings.global_hotkey)
        self._settings.setValue("overlay/opacity", settings.overlay_opacity)
        self._settings.setValue("general/start_minimized", settings.start_minimized)

        self._settings.setValue("azure/api_key", settings.azure_api_key)
        self._settings.setValue("azure/region", settings.azure_region)
        self._settings.setValue("azure/endpoint", settings.azure_endpoint)

        self._settings.setValue("libretranslate/base_url", settings.libretranslate_url)
        self._settings.setValue(
            "libretranslate/api_key", settings.libretranslate_api_key
        )
        self._settings.setValue("deepl/api_key", settings.deepl_api_key)
        self._settings.setValue("deepl/api_url", settings.deepl_api_url)
        self._settings.setValue("ocr/min_confidence", settings.ocr_min_confidence)
        self._settings.sync()
        return settings

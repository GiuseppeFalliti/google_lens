import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QSettings

from src.config.settings import AppSettings
from src.config.settings_manager import SettingsManager


def test_settings_round_trip(tmp_path):
    qsettings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = SettingsManager(qsettings)
    expected = AppSettings(
        source_language="en",
        target_language="it",
        translation_provider="azure",
        global_hotkey="CTRL+SHIFT+T",
        overlay_opacity=0.75,
        azure_api_key="secret",
        azure_region="westeurope",
        azure_endpoint="https://api.cognitive.microsofttranslator.com",
    )

    manager.save(expected)
    actual = manager.load()

    assert actual.source_language == "en"
    assert actual.target_language == "it"
    assert actual.translation_provider == "azure"
    assert actual.overlay_opacity == pytest.approx(0.75)
    assert actual.azure_api_key == "secret"
    assert actual.azure_region == "westeurope"
    assert actual.azure_endpoint == "https://api.cognitive.microsofttranslator.com"

def test_gemini_settings_round_trip(tmp_path):
    qsettings = QSettings(str(tmp_path / "gemini.ini"), QSettings.Format.IniFormat)
    manager = SettingsManager(qsettings)
    manager.save(
        AppSettings(
            translation_provider="gemini",
            gemini_api_key="test-key",
            gemini_model="gemini-3.5-flash-lite",
        )
    )
    actual = manager.load()
    assert actual.translation_provider == "gemini"
    assert actual.gemini_api_key == "test-key"
    assert actual.gemini_model == "gemini-3.5-flash-lite"

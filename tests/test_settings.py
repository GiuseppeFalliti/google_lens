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
        translation_provider="libretranslate",
        global_hotkey="CTRL+SHIFT+T",
        overlay_opacity=0.75,
        libretranslate_url="http://localhost:5000",
    )

    manager.save(expected)
    actual = manager.load()

    assert actual.source_language == "en"
    assert actual.target_language == "it"
    assert actual.translation_provider == "libretranslate"
    assert actual.overlay_opacity == pytest.approx(0.75)

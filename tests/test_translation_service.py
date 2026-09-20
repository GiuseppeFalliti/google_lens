import pytest

from src.exceptions import TranslationConfigurationError
from src.translation.base_translator import TranslationProvider
from src.translation.translation_service import TranslationService


class FakeProvider(TranslationProvider):
    @property
    def name(self) -> str:
        return "fake"

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        return f"{source_language}>{target_language}:{text}"


def test_provider_selection():
    service = TranslationService([FakeProvider()])
    result = service.translate("hello", "en", "it", "fake")
    assert result == "en>it:hello"


def test_missing_provider():
    service = TranslationService()
    with pytest.raises(TranslationConfigurationError):
        service.translate("hello", "en", "it", "missing")


def test_same_language_returns_input_without_provider():
    service = TranslationService()
    assert service.translate(" hello ", "en", "en", "missing") == "hello"

import httpx
import pytest

from src.exceptions import TranslationConfigurationError, TranslationError
from src.translation.azure_translator import AzureTranslator


def test_azure_requires_api_key():
    provider = AzureTranslator(api_key="")
    with pytest.raises(TranslationConfigurationError):
        provider.translate("hello", "en", "it")


def test_azure_requires_endpoint():
    provider = AzureTranslator(api_key="key", endpoint="")
    with pytest.raises(TranslationConfigurationError):
        provider.translate("hello", "en", "it")


def test_azure_provider_name():
    provider = AzureTranslator(api_key="key")
    assert provider.name == "azure"

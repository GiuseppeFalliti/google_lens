from __future__ import annotations

from collections.abc import Iterable

from src.exceptions import TranslationConfigurationError, TranslationError

from .base_translator import TranslationProvider


class TranslationService:
    def __init__(self, providers: Iterable[TranslationProvider] | None = None) -> None:
        self._providers: dict[str, TranslationProvider] = {}
        for provider in providers or []:
            self.register(provider)

    def register(self, provider: TranslationProvider) -> None:
        self._providers[provider.name.lower()] = provider

    def available_providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def get_provider(self, name: str) -> TranslationProvider:
        key = name.strip().lower()
        provider = self._providers.get(key)
        if provider is None:
            raise TranslationConfigurationError(
                f"Translation provider '{name}' is not configured."
            )
        return provider

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        provider_name: str,
    ) -> str:
        cleaned = text.strip()
        if not cleaned:
            raise TranslationError("There is no text to translate.")
        if source_language == target_language:
            return cleaned

        provider = self.get_provider(provider_name)
        try:
            return provider.translate(cleaned, source_language, target_language)
        except (TranslationConfigurationError, TranslationError):
            raise
        except Exception as exc:
            raise TranslationError(
                f"Unexpected error from translation provider '{provider_name}': {exc}"
            ) from exc

    def translate_many(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
        provider_name: str,
    ) -> list[str]:
        cleaned = [text.strip() for text in texts]
        if not cleaned or any(not text for text in cleaned):
            raise TranslationError("One or more text regions are empty.")

        if source_language == target_language:
            return cleaned

        provider = self.get_provider(provider_name)
        try:
            translated = provider.translate_many(
                cleaned,
                source_language,
                target_language,
            )
        except (TranslationConfigurationError, TranslationError):
            raise
        except Exception as exc:
            raise TranslationError(
                f"Unexpected error from translation provider '{provider_name}': {exc}"
            ) from exc

        if len(translated) != len(cleaned):
            raise TranslationError(
                f"Translation provider '{provider_name}' returned an invalid batch."
            )
        return translated

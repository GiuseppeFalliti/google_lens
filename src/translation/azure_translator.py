from __future__ import annotations

import httpx

from src.exceptions import TranslationConfigurationError, TranslationError

from .base_translator import TranslationProvider


class AzureTranslator(TranslationProvider):
    """Microsoft Azure AI Translator Text API v3 provider."""

    _BATCH_SIZE = 25

    def __init__(
        self,
        api_key: str = "",
        region: str = "",
        endpoint: str = "https://api.cognitive.microsofttranslator.com",
    ) -> None:
        self.api_key = api_key.strip()
        self.region = region.strip()
        self.endpoint = endpoint.strip().rstrip("/")

    @property
    def name(self) -> str:
        return "azure"

    def _validate(self) -> None:
        if not self.api_key:
            raise TranslationConfigurationError("Azure Translator API key is missing.")
        if not self.endpoint:
            raise TranslationConfigurationError("Azure Translator endpoint is missing.")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json",
        }
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region
        return headers

    @staticmethod
    def _raise_http_error(exc: httpx.HTTPStatusError) -> None:
        status = exc.response.status_code
        if status in {401, 403}:
            message = (
                "Azure Translator rejected the API key, region, or resource permissions."
            )
        elif status == 429:
            message = "Azure Translator rate limit or quota reached."
        elif status == 400:
            message = "Azure Translator rejected the request or language configuration."
        else:
            message = f"Azure Translator returned HTTP {status}."
        raise TranslationError(message) from exc

    def _translate_batch(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str]:
        params = {
            "api-version": "3.0",
            "from": source_language,
            "to": target_language,
        }
        body = [{"Text": text} for text in texts]

        try:
            with httpx.Client(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
                response = client.post(
                    f"{self.endpoint}/translate",
                    params=params,
                    headers=self._headers(),
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise TranslationError("Azure Translator request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            self._raise_http_error(exc)
        except (httpx.HTTPError, ValueError) as exc:
            raise TranslationError(
                f"Unable to communicate with Azure Translator: {exc}"
            ) from exc

        translations: list[str] = []
        try:
            for item in data:
                translated = str(item["translations"][0]["text"]).strip()
                if not translated:
                    raise TranslationError(
                        "Azure Translator returned an empty translation."
                    )
                translations.append(translated)
        except (IndexError, KeyError, TypeError) as exc:
            raise TranslationError(
                "Azure Translator returned an invalid response."
            ) from exc

        if len(translations) != len(texts):
            raise TranslationError("Azure Translator returned an incomplete batch.")
        return translations

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        return self.translate_many(
            [text],
            source_language,
            target_language,
        )[0]

    def translate_many(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str]:
        self._validate()

        cleaned = [text.strip() for text in texts if text.strip()]
        if len(cleaned) != len(texts):
            raise TranslationError("Azure Translator received an empty text region.")

        translations: list[str] = []
        for start in range(0, len(cleaned), self._BATCH_SIZE):
            chunk = cleaned[start : start + self._BATCH_SIZE]
            translations.extend(
                self._translate_batch(
                    chunk,
                    source_language,
                    target_language,
                )
            )
        return translations

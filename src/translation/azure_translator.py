from __future__ import annotations

import httpx

from src.exceptions import TranslationConfigurationError, TranslationError

from .base_translator import TranslationProvider


class AzureTranslator(TranslationProvider):
    """Microsoft Azure AI Translator Text API v3 provider."""

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

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        if not self.api_key:
            raise TranslationConfigurationError("Azure Translator API key is missing.")
        if not self.endpoint:
            raise TranslationConfigurationError("Azure Translator endpoint is missing.")

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json",
        }
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region

        params = {
            "api-version": "3.0",
            "from": source_language,
            "to": target_language,
        }
        body = [{"Text": text}]

        try:
            with httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
                response = client.post(
                    f"{self.endpoint}/translate",
                    params=params,
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise TranslationError("Azure Translator request timed out.") from exc
        except httpx.HTTPStatusError as exc:
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
        except (httpx.HTTPError, ValueError) as exc:
            raise TranslationError(
                f"Unable to communicate with Azure Translator: {exc}"
            ) from exc

        try:
            translated = data[0]["translations"][0]["text"]
        except (IndexError, KeyError, TypeError) as exc:
            raise TranslationError(
                "Azure Translator returned an invalid response."
            ) from exc

        translated = str(translated).strip()
        if not translated:
            raise TranslationError("Azure Translator returned an empty translation.")
        return translated

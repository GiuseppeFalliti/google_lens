from __future__ import annotations

import httpx

from src.exceptions import TranslationConfigurationError, TranslationError

from .base_translator import TranslationProvider


class DeepLTranslator(TranslationProvider):
    def __init__(
        self,
        api_key: str = "",
        api_url: str = "https://api-free.deepl.com/v2/translate",
    ) -> None:
        self.api_key = api_key.strip()
        self.api_url = api_url.strip()

    @property
    def name(self) -> str:
        return "deepl"

    def translate(
        self, text: str, source_language: str, target_language: str
    ) -> str:
        if not self.api_key:
            raise TranslationConfigurationError("DeepL API key is missing.")
        if not self.api_url:
            raise TranslationConfigurationError("DeepL API endpoint is missing.")

        payload = {
            "text": [text],
            "source_lang": source_language.upper(),
            "target_lang": target_language.upper(),
        }
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
                response = client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise TranslationError("DeepL request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in {401, 403}:
                message = "DeepL rejected the API key or account permissions."
            elif status == 429:
                message = "DeepL rate limit reached."
            elif status == 456:
                message = "DeepL quota exceeded."
            else:
                message = f"DeepL returned HTTP {status}."
            raise TranslationError(message) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise TranslationError(f"Unable to communicate with DeepL: {exc}") from exc

        translations = data.get("translations", [])
        if not translations or not translations[0].get("text"):
            raise TranslationError("DeepL returned an invalid response.")
        return str(translations[0]["text"]).strip()

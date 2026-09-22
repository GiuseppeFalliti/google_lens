from __future__ import annotations

import httpx

from src.exceptions import TranslationConfigurationError, TranslationError

from .base_translator import TranslationProvider


class LibreTranslateTranslator(TranslationProvider):
    def __init__(self, base_url: str, api_key: str = "") -> None:
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()

    @property
    def name(self) -> str:
        return "libretranslate"

    def translate(
        self, text: str, source_language: str, target_language: str
    ) -> str:
        if not self.base_url:
            raise TranslationConfigurationError("LibreTranslate base URL is missing.")

        payload: dict[str, str] = {
            "q": text,
            "source": source_language,
            "target": target_language,
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        try:
            with httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
                response = client.post(f"{self.base_url}/translate", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise TranslationError("LibreTranslate request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                message = "LibreTranslate rate limit reached."
            elif status in {401, 403}:
                message = "LibreTranslate rejected the API key."
            else:
                message = f"LibreTranslate returned HTTP {status}."
            raise TranslationError(message) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise TranslationError(
                f"Unable to connect to LibreTranslate: {exc}"
            ) from exc

        translated = data.get("translatedText")
        if not translated:
            raise TranslationError("LibreTranslate returned an invalid response.")
        return str(translated).strip()

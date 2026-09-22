from __future__ import annotations

from dataclasses import dataclass, replace


LANGUAGES: dict[str, str] = {
    "English": "en",
    "Italian": "it",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Portuguese": "pt",
}

PROVIDERS: dict[str, str] = {
    "Argos Translate": "argos",
    "Azure Translator": "azure",
    "DeepL": "deepl",
    "LibreTranslate": "libretranslate",
}


@dataclass(slots=True)
class AppSettings:
    source_language: str = "en"
    target_language: str = "it"
    translation_provider: str = "argos"
    global_hotkey: str = "CTRL+SHIFT+T"
    overlay_opacity: float = 0.82
    start_minimized: bool = False

    azure_api_key: str = ""
    azure_region: str = ""
    azure_endpoint: str = "https://api.cognitive.microsofttranslator.com"

    libretranslate_url: str = "http://localhost:5000"
    libretranslate_api_key: str = ""
    deepl_api_key: str = ""
    deepl_api_url: str = "https://api-free.deepl.com/v2/translate"
    ocr_min_confidence: float = 0.35

    def validated(self) -> "AppSettings":
        source = self.source_language.strip().lower()
        target = self.target_language.strip().lower()
        provider = self.translation_provider.strip().lower()
        hotkey = self.global_hotkey.strip().upper().replace(" ", "")

        if not source or not target:
            raise ValueError("Source and target languages are required.")
        if source == target:
            raise ValueError("Source and target languages must be different.")
        if provider not in {"argos", "azure", "deepl", "libretranslate"}:
            raise ValueError(f"Unsupported translation provider: {provider}")
        if not 0.30 <= float(self.overlay_opacity) <= 1.0:
            raise ValueError("Overlay opacity must be between 0.30 and 1.0.")
        if not 0.0 <= float(self.ocr_min_confidence) <= 1.0:
            raise ValueError("OCR confidence must be between 0 and 1.")
        if not hotkey:
            raise ValueError("Global hotkey is required.")

        return replace(
            self,
            source_language=source,
            target_language=target,
            translation_provider=provider,
            global_hotkey=hotkey,
            overlay_opacity=float(self.overlay_opacity),
            ocr_min_confidence=float(self.ocr_min_confidence),
            azure_api_key=self.azure_api_key.strip(),
            azure_region=self.azure_region.strip(),
            azure_endpoint=self.azure_endpoint.strip().rstrip("/"),
            libretranslate_url=self.libretranslate_url.strip().rstrip("/"),
            deepl_api_url=self.deepl_api_url.strip(),
        )

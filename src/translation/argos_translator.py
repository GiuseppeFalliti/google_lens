from __future__ import annotations

from src.exceptions import TranslationConfigurationError, TranslationError

from .base_translator import TranslationProvider


class ArgosTranslator(TranslationProvider):
    @property
    def name(self) -> str:
        return "argos"

    @staticmethod
    def _modules():
        try:
            import argostranslate.package as package
            import argostranslate.translate as translate
        except ImportError as exc:
            raise TranslationConfigurationError(
                "Argos Translate is not installed. Run: pip install argostranslate"
            ) from exc
        return package, translate

    def is_model_installed(self, source_language: str, target_language: str) -> bool:
        _, translate = self._modules()
        try:
            languages = {lang.code: lang for lang in translate.get_installed_languages()}
            source = languages.get(source_language)
            target = languages.get(target_language)
            if source is None or target is None:
                return False
            source.get_translation(target)
            return True
        except Exception:
            return False

    def install_language_model(
        self, source_language: str, target_language: str
    ) -> None:
        package, translate = self._modules()
        try:
            package.update_package_index()
            available = package.get_available_packages()
            candidate = next(
                (
                    item
                    for item in available
                    if item.from_code == source_language
                    and item.to_code == target_language
                ),
                None,
            )
            if candidate is None:
                raise TranslationConfigurationError(
                    f"No direct Argos model is available for "
                    f"{source_language} -> {target_language}."
                )
            package.install_from_path(candidate.download())
            try:
                translate.get_installed_languages.cache_clear()
            except AttributeError:
                pass
        except TranslationConfigurationError:
            raise
        except Exception as exc:
            raise TranslationError(
                f"Unable to download/install the Argos language model: {exc}"
            ) from exc

    def translate(
        self, text: str, source_language: str, target_language: str
    ) -> str:
        _, translate = self._modules()

        if not self.is_model_installed(source_language, target_language):
            raise TranslationConfigurationError(
                f"Argos model {source_language} -> {target_language} is not installed."
            )

        try:
            result = translate.translate(text, source_language, target_language)
        except Exception as exc:
            raise TranslationError(f"Argos translation failed: {exc}") from exc

        result = str(result).strip()
        if not result:
            raise TranslationError("Argos returned an empty translation.")
        return result

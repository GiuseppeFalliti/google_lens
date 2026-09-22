from __future__ import annotations

from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        raise NotImplementedError

    def translate_many(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str]:
        """Translate multiple independent text regions.

        Providers can override this with a real batch API. The default keeps
        every existing provider compatible by translating items one at a time.
        """
        return [
            self.translate(text, source_language, target_language)
            for text in texts
        ]

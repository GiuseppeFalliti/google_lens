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

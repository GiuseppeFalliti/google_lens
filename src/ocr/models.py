from __future__ import annotations

from dataclasses import dataclass


Point = tuple[float, float]


@dataclass(slots=True)
class OCRTextBlock:
    text: str
    confidence: float
    box: list[Point]

    @property
    def top(self) -> float:
        return min((point[1] for point in self.box), default=0.0)

    @property
    def left(self) -> float:
        return min((point[0] for point in self.box), default=0.0)


@dataclass(slots=True)
class OCRResult:
    blocks: list[OCRTextBlock]
    full_text: str

    @property
    def is_empty(self) -> bool:
        return not self.full_text.strip()

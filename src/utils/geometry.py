from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_points(cls, x1: int, y1: int, x2: int, y2: int) -> "Rect":
        left = min(x1, x2)
        top = min(y1, y2)
        return cls(left, top, abs(x2 - x1), abs(y2 - y1))

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def is_valid(self) -> bool:
        return self.width > 1 and self.height > 1

    def normalized(self) -> "Rect":
        width = self.width
        height = self.height
        x = self.x
        y = self.y
        if width < 0:
            x += width
            width = -width
        if height < 0:
            y += height
            height = -height
        return Rect(x, y, width, height)

    def clamp(self, bounds: "Rect") -> "Rect":
        current = self.normalized()
        left = max(current.x, bounds.x)
        top = max(current.y, bounds.y)
        right = min(current.right, bounds.right)
        bottom = min(current.bottom, bounds.bottom)
        return Rect(left, top, max(0, right - left), max(0, bottom - top))


def union_rects(rects: list[Rect]) -> Rect:
    if not rects:
        raise ValueError("At least one rectangle is required.")
    left = min(rect.x for rect in rects)
    top = min(rect.y for rect in rects)
    right = max(rect.right for rect in rects)
    bottom = max(rect.bottom for rect in rects)
    return Rect(left, top, right - left, bottom - top)

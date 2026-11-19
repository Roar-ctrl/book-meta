"""Геометрия для правил."""
from __future__ import annotations

from collections.abc import Iterable

from book_meta.models.location import Rect


def overlap_fraction(box: Rect, others: Iterable[Rect]) -> float:
    """Какая доля площади `box` закрыта самым перекрывающим её прямоугольником из `others`."""
    area = max(1e-9, box.w * box.h)
    best = 0.0
    for o in others:
        w = min(box.x1, o.x1) - max(box.x0, o.x0)
        h = min(box.y1, o.y1) - max(box.y0, o.y0)
        if w > 0 and h > 0:
            best = max(best, w * h / area)
    return best

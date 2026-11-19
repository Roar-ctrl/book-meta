"""Стартовые правила над регионами разметки (до распознавания). Пороги - константы вверху, правьте под корпус."""
from __future__ import annotations

from book_meta.rules.base import PageContext, region_rule
from book_meta.rules.geom import overlap_fraction
from book_meta.readers.layout_base import TEXT_LIKE, Region, RegionKind

FORMULA_MIN_CONFIDENCE = 0.5     # уверенность layout-модели для региона formula
MIN_AREA = 1e-4                  # доля площади страницы; меньше - мусорная рамка
INLINE_TEXT_OVERLAP = 0.5        # доля формулы внутри текстового региона => считаем inline
MARGIN_OVERLAP = 0.5             # доля формулы внутри колонтитула => выбрасываем


@region_rule("drop_low_confidence", order=10)
def drop_low_confidence(regions: list[Region], ctx: PageContext) -> list[Region]:
    return [r for r in regions if not (r.kind == RegionKind.FORMULA and r.confidence < FORMULA_MIN_CONFIDENCE)]


@region_rule("drop_degenerate", order=15)
def drop_degenerate(regions: list[Region], ctx: PageContext) -> list[Region]:
    return [r for r in regions if not (r.kind == RegionKind.FORMULA and r.bbox.w * r.bbox.h < MIN_AREA)]


@region_rule("drop_inline_formulas", order=20)
def drop_inline_formulas(regions: list[Region], ctx: PageContext) -> list[Region]:
    """Inline-формула лежит внутри абзаца, выключная - между абзацами.

    Слабое место: если модель нарисовала текстовый регион поверх выключной формулы, она будет потеряна.
    """
    text = [r.bbox for r in regions if r.kind in TEXT_LIKE]
    return [
        r for r in regions
        if not (r.kind == RegionKind.FORMULA and overlap_fraction(r.bbox, text) >= INLINE_TEXT_OVERLAP)
    ]


@region_rule("drop_formulas_in_header_footer", order=30)
def drop_formulas_in_header_footer(regions: list[Region], ctx: PageContext) -> list[Region]:
    margins = [r.bbox for r in regions if r.kind in (RegionKind.PAGE_HEADER, RegionKind.PAGE_FOOTER)]
    return [
        r for r in regions
        if not (r.kind == RegionKind.FORMULA and overlap_fraction(r.bbox, margins) >= MARGIN_OVERLAP)
    ]

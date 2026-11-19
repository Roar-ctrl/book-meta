"""Регионы разметки страницы и интерфейс LayoutAdapter (см. UML, диаграмма 2)."""
from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from book_meta.models.location import Rect


class RegionKind(StrEnum):
    TEXT = "text"
    TITLE = "title"
    SECTION_HEADER = "section_header"
    ABSTRACT = "abstract"
    FORMULA = "formula"
    FORMULA_NUMBER = "formula_number"
    PICTURE = "picture"
    CAPTION = "caption"
    TABLE = "table"
    FOOTNOTE = "footnote"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"
    PAGE_NUMBER = "page_number"
    ALGORITHM = "algorithm"
    REFERENCE = "reference"
    TOC = "toc"
    ASIDE = "aside"
    OTHER = "other"


# Регионы, внутри которых может стоять inline-формула.
TEXT_LIKE = frozenset({
    RegionKind.TEXT, RegionKind.TITLE, RegionKind.SECTION_HEADER, RegionKind.ABSTRACT,
    RegionKind.CAPTION, RegionKind.FOOTNOTE, RegionKind.REFERENCE, RegionKind.TOC, RegionKind.ASIDE,
})


class Region(BaseModel):
    kind: RegionKind
    raw_label: str                  # метка модели как есть
    bbox: Rect                      # нормированный 0..1, начало - левый верхний угол
    page_index: int                 # с 0
    confidence: float


class LayoutAdapter(Protocol):
    def regions(self, pdf_path: str | Path, pages: Iterable[int] | None = None) -> list[Region]: ...

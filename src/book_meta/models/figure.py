from enum import StrEnum

from pydantic import BaseModel

from book_meta.models.location import Location
from book_meta.models.provenance import Provenance


class FigureKind(StrEnum):
    RASTER = "raster"
    VECTOR = "vector"
    MIXED = "mixed"

class FigureAssets(BaseModel):
    original: str | None = None            # исходный растр/SVG как в книге
    svg: str | None = None                 # векторные
    ps: str | None = None                  # PostScript
    eps: str | None = None
    preview_png: str                       # превью всегда (для просмотра/ревью)

class Figure(BaseModel):
    id: str                                # "fig_0001"
    kind: FigureKind
    number: str | None = None              # "2.3" из «Рис. 2.3»
    number_raw: str | None = None          # "Рис. 2.3"
    caption: str | None = None             # полная подпись
    title: str | None = None               # подпись без префикса «Рис. N.»
    alt_text: str | None = None            # EPUB alt
    assets: FigureAssets
    width_px: int | None = None
    height_px: int | None = None
    location: Location                     # zone + page + chapter_path
    prov: Provenance
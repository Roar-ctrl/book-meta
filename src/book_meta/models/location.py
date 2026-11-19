"""Положение элемента: страница + bbox (PDF) или поток (EPUB). Дословно из design §3.1."""
from enum import StrEnum

from pydantic import BaseModel


class Rect(BaseModel):
    """Нормированные координаты 0..1, начало - левый верхний угол страницы."""
    x0: float; y0: float; x1: float; y1: float

    @property
    def cx(self) -> float: return (self.x0 + self.x1) / 2
    @property
    def cy(self) -> float: return (self.y0 + self.y1) / 2
    @property
    def w(self) -> float: return self.x1 - self.x0
    @property
    def h(self) -> float: return self.y1 - self.y0


class Zone(StrEnum):
    TOP_LEFT = "top_left";       TOP = "top";       TOP_RIGHT = "top_right"
    LEFT = "left";               CENTER = "center"; RIGHT = "right"
    BOTTOM_LEFT = "bottom_left"; BOTTOM = "bottom"; BOTTOM_RIGHT = "bottom_right"
    FULL_PAGE = "full_page"


ZONE_RU = {
    Zone.TOP_LEFT: "левый верхний угол", Zone.TOP: "сверху", Zone.TOP_RIGHT: "правый верхний угол",
    Zone.LEFT: "слева", Zone.CENTER: "по центру", Zone.RIGHT: "справа",
    Zone.BOTTOM_LEFT: "левый нижний угол", Zone.BOTTOM: "снизу", Zone.BOTTOM_RIGHT: "правый нижний угол",
    Zone.FULL_PAGE: "на всю страницу",
}


def zone_of(b: Rect, wide: float = 0.7, tall: float = 0.7) -> Zone:
    if b.w > wide and b.h > tall:
        return Zone.FULL_PAGE
    col = 1 if b.w > wide else min(int(b.cx * 3), 2)     # 0=left 1=center 2=right
    row = 1 if b.h > tall else min(int(b.cy * 3), 2)     # 0=top  1=middle 2=bottom
    grid = [[Zone.TOP_LEFT, Zone.TOP, Zone.TOP_RIGHT],
            [Zone.LEFT, Zone.CENTER, Zone.RIGHT],
            [Zone.BOTTOM_LEFT, Zone.BOTTOM, Zone.BOTTOM_RIGHT]]
    return grid[row][col]


class PageAnchor(BaseModel):           # только PDF (и EPUB с page-list)
    page_index: int | None = None      # физический индекс, с 0
    page_label: str | None = None      # печатный номер: "17", "xii"
    bbox: Rect | None = None
    zone: Zone | None = None


class FlowAnchor(BaseModel):           # только EPUB
    spine_index: int
    href: str                          # "text/ch03.xhtml"
    dom_path: str | None = None        # XPath/CSS до элемента
    epub_cfi: str | None = None
    char_offset: int | None = None


class Location(BaseModel):
    order: int                         # сквозной номер среди элементов того же типа
    block_idx: int                     # индекс в BookIR
    chapter_path: list[str] = []       # ["Часть II", "Глава 3", "3.2 Интегралы"]
    page: PageAnchor | None = None
    flow: FlowAnchor | None = None
    progress: float | None = None      # 0..1 относительная позиция в книге

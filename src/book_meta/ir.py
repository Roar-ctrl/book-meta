from enum import StrEnum
from pydantic import BaseModel, Field

from book_meta.models.location import Location

class BlockKind(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    MATH = "math"            # выключная формула (MathML / регион PDF)
    IMAGE = "image"          # растр
    VECTOR = "vector"        # векторная группа (PDF drawings / <svg>)
    CAPTION = "caption"
    TABLE = "table"
    PAGE_BREAK = "page_break"
    FOOTNOTE = "footnote"

class Block(BaseModel):
    idx: int                               # порядковый номер в IR
    kind: BlockKind
    text: str | None = None
    loc: Location                        # см. §3.1
    font_size: float | None = None         # PDF: доминирующий кегль
    fonts: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)  # mathml, xref, svg, dom_path, ...

class TocNode(BaseModel):
    title: str
    level: int
    block_idx: int | None = None
    children: list["TocNode"] = Field(default_factory=list)

class BookIR(BaseModel):
    source_path: str
    format: str                            # "epub" | "pdf"
    container_meta: dict[str, list[str]]   # OPF dc:* / PDF Info+XMP
    toc: list[TocNode]
    blocks: list[Block]
    n_pages: int | None = None             # только PDF
    page_labels: dict[int, str] = Field(default_factory=dict)  # physical idx -> "xii", "17"
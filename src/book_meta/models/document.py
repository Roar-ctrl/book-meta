from pydantic import BaseModel

from book_meta.ir import TocNode
from book_meta.models.bibliography import BibRecord, BookReference
from book_meta.models.figure import Figure
from book_meta.models.formula import Formula


class BookDocument(BaseModel):
    schema_version: str = "1.0"
    book_id: str
    source: dict                           # {"file": ..., "sha256": ..., "format": "epub", "size": ...}
    bibliography: BibRecord
    formulas: list[Formula] = []
    figures: list[Figure] = []
    references: list[BookReference] = []
    toc: list[TocNode] = []
    stats: dict = {}                       # счётчики, время, версии моделей
    warnings: list[str] = []
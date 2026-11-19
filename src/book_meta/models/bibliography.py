from pydantic import BaseModel

from book_meta.models.location import Location
from book_meta.models.provenance import Provenance


class Person(BaseModel):
    family: str
    given: str | None = None               # "Иван Иванович" или "И. И."
    role: str = "author"                   # author | editor | translator | compiler
    raw: str | None = None

class FieldCandidate(BaseModel):
    value: str
    prov: Provenance

class BookIdentifiers(BaseModel):
    isbn: list[str] = []                   # нормализованные, с проверенной контрольной суммой
    issn: list[str] = []
    doi: str | None = None
    udc: list[str] = []                    # УДК
    bbk: list[str] = []                    # ББК
    lcc: str | None = None                 # Library of Congress Classification
    ddc: str | None = None
    author_mark: str | None = None         # авторский знак
    grnti: str | None = None

class BibRecord(BaseModel):
    entry_type: str = "book"               # book | inbook | proceedings | phdthesis | manual
    cite_key: str
    authors: list[Person] = []
    title: str | None = None
    subtitle: str | None = None
    series: str | None = None
    edition: str | None = None
    publisher: str | None = None
    address: str | None = None             # место издания
    year: int | None = None
    pages: int | None = None               # всего страниц
    language: str | None = None            # ISO 639-1
    identifiers: BookIdentifiers = BookIdentifiers()
    annotation: str | None = None          # аннотация
    candidates: dict[str, list[FieldCandidate]] = {}   # поле -> все найденные варианты
    location: Location | None = None       # где найден imprint (начало/конец)
    prov: Provenance | None = None

class BookReference(BaseModel):            # опционально: список литературы внутри книги
    raw: str
    parsed: dict[str, str] = {}
    location: Location
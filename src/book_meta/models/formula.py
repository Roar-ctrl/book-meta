from enum import StrEnum

from pydantic import BaseModel

from book_meta.models.location import Location
from book_meta.models.provenance import Provenance


class FormulaSource(StrEnum):
    MATHML_NATIVE = "mathml_native"        # EPUB: <math>
    TEX_ANNOTATION = "tex_annotation"      # <annotation encoding="application/x-tex">, alt="\frac..."
    IMAGE_MODEL = "image_model"            # кроп → LaTeX через модель
    MANUAL = "manual"

class Formula(BaseModel):
    id: str                                # "eq_0001"
    kind: str = "display"                  # "display" | "inline"
    latex: str | None = None               # основной формат, без $$ и \tag
    mathml: str | None = None
    omml: str | None = None                # Microsoft Office Math, лениво
    number: str | None = None              # "3.14" (нормализовано)
    number_raw: str | None = None          # "(3.14)" как в книге
    title: str | None = None               # «Теорема Пифагора», если нашли
    context_before: str | None = None      # ≤200 симв. предшествующего текста (для title/ручной проверки)
    image_path: str | None = None          # "formulas/eq_0001.png" — кроп-источник
    source: FormulaSource
    location: Location
    prov: Provenance
from pydantic import BaseModel


class Provenance(BaseModel):
    extractor: str                     # "formula.mathml", "formula.docling", "bib.imprint_regex"
    method: str                        # "mathml_native" | "tex_annotation" | "model" | "heuristic" | "container_meta"
    confidence: float = 1.0            # 0..1
    version: str | None = None         # версия модели/экстрактора
    needs_review: bool = False
from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from book_meta.models.formula import Formula, FormulaSource
from book_meta.models.location import Location, PageAnchor, zone_of
from book_meta.models.provenance import Provenance

if TYPE_CHECKING:
    from book_meta.extractors.formulas.image_model import FormulaCandidate


def candidate_to_formula(
    candidate: FormulaCandidate,
    *,
    order: int,
    block_idx: int,
    model_version: str,
    output_dir: str | Path,
    page_label: str | None = None,
) -> Formula:
    formula_id = f"eq_{order:04d}"
    image_path = Path("formulas") / f"{formula_id}.png" if candidate.png else None
    formula = Formula(
        id=formula_id,
        latex=candidate.latex,
        image_path=image_path.as_posix() if image_path else None,
        source=FormulaSource.IMAGE_MODEL,
        location=Location(
            order=order,
            block_idx=block_idx,
            page=PageAnchor(
                page_index=candidate.page_index,
                page_label=page_label,
                bbox=candidate.bbox,
                zone=zone_of(candidate.bbox),
            ),
        ),
        prov=Provenance(
            extractor="formula.image_model",
            method="model",
            version=model_version,
            confidence=candidate.confidence,
            needs_review=bool(candidate.issues),
        ),
    )
    if image_path is not None:
        _save_crop(Path(output_dir) / image_path, candidate.png)
    return formula


def _save_crop(path: Path, png: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = NamedTemporaryFile(dir=path.parent, delete=False)
    temporary_path = Path(stream.name)
    try:
        with stream:
            stream.write(png)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)

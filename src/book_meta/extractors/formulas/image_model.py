"""Шаг 4 каскада формул: PDF -> регионы -> кропы -> модель -> LaTeX -> эвристики.

Здесь только «модельная» часть. Остальное - TODO, делается в cascade.py / numbering.py:
  * превращение `FormulaCandidate` в `Formula` (models/formula.py: Location, Provenance, id, source=IMAGE_MODEL);
  * номер формулы: регионы `formula_number` (их отдаёт layout) + поиск спанов справа;
  * название и контекст формулы (titles.py);
  * MathML / TeX-аннотация и сверка с ними (шаги 1–2 каскада, EPUB);
  * валидация LaTeX через pylatexenc и `needs_review` -> review.md.
"""
from __future__ import annotations

import io
import logging
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from book_meta.extractors.formulas.recognizers import FormulaRecognizer, recognize_many
from book_meta.rules import LatexContext, PageContext, RuleHit, RuleSet, default_rules
from book_meta.rules.latex import confidence_from_issues
from book_meta.models.location import Rect
from book_meta.readers.layout_base import LayoutAdapter, Region, RegionKind
from book_meta.utils.paddle_runtime import PaddleSettings
from book_meta.utils.render import PageRenderer

log = logging.getLogger(__name__)


@dataclass
class FormulaCandidate:
    page_index: int
    bbox: Rect                       # нормированный bbox региона (без полей кропа)
    latex: str                       # после правил
    raw_latex: str                   # как выдала модель
    confidence: float                # оценка по проверкам (модель своей не даёт)
    layout_confidence: float
    issues: list[str]                # что не понравилось проверкам; непусто => на ревью
    hits: list[RuleHit]              # сработавшие правила над LaTeX
    png: bytes = field(repr=False, default=b"")


@dataclass
class ModelRun:
    formulas: list[FormulaCandidate]
    region_hits: dict[int, list[RuleHit]]  # страница -> сработавшие правила над регионами (там же, что и кого убрали)


def crop_png(img: Image.Image, rect: Rect, pad_px: int) -> tuple[bytes, tuple[int, int]] | None:
    w, h = img.size
    box = (
        max(0, int(rect.x0 * w) - pad_px), max(0, int(rect.y0 * h) - pad_px),
        min(w, int(rect.x1 * w) + pad_px), min(h, int(rect.y1 * h) + pad_px),
    )
    if box[2] - box[0] < 2 or box[3] - box[1] < 2:
        return None
    crop = img.crop(box)
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    return buf.getvalue(), crop.size


def recognize_formulas(
    pdf_path: str | Path,
    *,
    layout: LayoutAdapter,
    recognizer: FormulaRecognizer,
    renderer: PageRenderer,
    settings: PaddleSettings | None = None,
    rules: RuleSet | None = None,
    include_inline: bool = False,
    pages: Iterable[int] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> ModelRun:
    """Выключные формулы PDF -> LaTeX. `include_inline=True` отключает правило drop_inline_formulas."""
    s = settings or PaddleSettings()
    if rules is None:
        rules = default_rules(disabled=["drop_inline_formulas"] if include_inline else [])

    by_page: dict[int, list[Region]] = defaultdict(list)
    for r in layout.regions(pdf_path, pages):
        by_page[r.page_index].append(r)

    formulas: list[FormulaCandidate] = []
    region_hits: dict[int, list[RuleHit]] = {}
    for n, (page, raw_regions) in enumerate(sorted(by_page.items()), 1):
        regions, hits = rules.apply_regions(raw_regions, PageContext(page, raw_regions))
        if hits:
            region_hits[page] = hits
        found = [r for r in regions if r.kind == RegionKind.FORMULA]
        if found:
            img = renderer.render_page(pdf_path, page, s.formula_dpi)
            crops = [(r, crop_png(img, r.bbox, s.crop_pad_px)) for r in found]
            crops = [(r, c) for r, c in crops if c is not None]
            results = recognize_many(recognizer, [c[0] for _, c in crops])
            for (r, (png, (w, h))), (raw, _) in zip(crops, results):
                ctx = LatexContext(width_px=w, height_px=h, region=r)
                latex, latex_hits = rules.apply_latex(raw, ctx)
                issues = rules.check_latex(latex, ctx)
                formulas.append(FormulaCandidate(
                    page_index=page, bbox=r.bbox, latex=latex, raw_latex=raw,
                    confidence=confidence_from_issues(issues), layout_confidence=r.confidence,
                    issues=issues, hits=latex_hits, png=png,
                ))
        log.info("page %d: %d formulas", page + 1, len(found))
        if progress:
            progress(n, len(by_page))
    return ModelRun(formulas, region_hits)

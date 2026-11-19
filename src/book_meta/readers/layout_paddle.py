"""LayoutAdapter на PP-DocLayout (PaddleOCR 3.x), работает на CPU.

Страница растеризуется в `layout_dpi`, модель возвращает регионы с метками, мы переводим их в `Region`
с нормированным bbox. Эвристики над регионами - в `book_meta.heuristics.regions` (применяются позже).

TODO: регионы для EPUB не нужны (там DOM).
TODO: пропускать страницы без шансов на формулы/рисунки (например, по шрифтам) - параметр `pages` уже есть.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

from PIL import Image

from book_meta.models.location import Rect
from book_meta.readers.layout_base import Region, RegionKind
from book_meta.utils.paddle_runtime import (
    PaddleSettings,
    common_kwargs,
    import_paddleocr,
    pil_to_bgr,
    result_data,
)
from book_meta.utils.render import PageRenderer, get_renderer

log = logging.getLogger(__name__)

# Метки PP-DocLayout (семейства L/M/S и plus) -> наши виды регионов. Неизвестная метка -> OTHER.
LABEL_MAP: dict[str, RegionKind] = {
    "text": RegionKind.TEXT,
    "doc_title": RegionKind.TITLE,
    "paragraph_title": RegionKind.SECTION_HEADER,
    "abstract": RegionKind.ABSTRACT,
    "content": RegionKind.TOC,
    "formula": RegionKind.FORMULA,
    "formula_number": RegionKind.FORMULA_NUMBER,
    "image": RegionKind.PICTURE,
    "chart": RegionKind.PICTURE,
    "figure_title": RegionKind.CAPTION,
    "table_title": RegionKind.CAPTION,
    "chart_title": RegionKind.CAPTION,
    "figure_table_chart_title": RegionKind.CAPTION,
    "table": RegionKind.TABLE,
    "footnote": RegionKind.FOOTNOTE,
    "header": RegionKind.PAGE_HEADER,
    "footer": RegionKind.PAGE_FOOTER,
    "number": RegionKind.PAGE_NUMBER,
    "algorithm": RegionKind.ALGORITHM,
    "reference": RegionKind.REFERENCE,
    "reference_content": RegionKind.REFERENCE,
    "aside_text": RegionKind.ASIDE,
}


def map_label(label: str) -> RegionKind:
    return LABEL_MAP.get(label, RegionKind.OTHER)


def _clamp(v: float) -> float:
    return min(1.0, max(0.0, v))


class PaddleLayout:
    name = "paddle"

    def __init__(self, settings: PaddleSettings | None = None, renderer: PageRenderer | None = None, detector=None):
        self.settings = settings or PaddleSettings()
        self._renderer = renderer
        self._detector = detector  # можно подставить заглушку в тестах

    @property
    def renderer(self) -> PageRenderer:
        if self._renderer is None:
            self._renderer = get_renderer()
        return self._renderer

    @property
    def detector(self):
        if self._detector is None:
            s = self.settings
            kwargs = {**common_kwargs(s), "model_name": s.layout_model}
            if s.layout_model_dir:
                kwargs["model_dir"] = str(s.layout_model_dir)
            if s.layout_threshold is not None:
                kwargs["threshold"] = s.layout_threshold
            self._detector = import_paddleocr().LayoutDetection(**kwargs)
        return self._detector

    def detect_image(self, img: Image.Image, page_index: int) -> list[Region]:
        """Одна страница (уже растеризованная) -> регионы в порядке сверху вниз, слева направо."""
        w, h = img.size
        res = self.detector.predict(pil_to_bgr(img), batch_size=1)
        boxes = result_data(res[0]).get("boxes", []) if res else []
        out: list[Region] = []
        for b in boxes:
            x0, y0, x1, y1 = b["coordinate"]
            rect = Rect(x0=_clamp(x0 / w), y0=_clamp(y0 / h), x1=_clamp(x1 / w), y1=_clamp(y1 / h))
            out.append(Region(
                kind=map_label(b["label"]), raw_label=b["label"], bbox=rect,
                page_index=page_index, confidence=float(b["score"]),
            ))
        out.sort(key=lambda r: (r.bbox.y0, r.bbox.x0))
        return out

    def regions(self, pdf_path: str | Path, pages: Iterable[int] | None = None) -> list[Region]:
        n = self.renderer.page_count(pdf_path)
        idx = range(n) if pages is None else sorted({p for p in pages if 0 <= p < n})
        out: list[Region] = []
        for i in idx:
            img = self.renderer.render_page(pdf_path, i, self.settings.layout_dpi)
            found = self.detect_image(img, i)
            log.info("layout: page %d/%d -> %d regions", i + 1, n, len(found))
            out.extend(found)
        return out

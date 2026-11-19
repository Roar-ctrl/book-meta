"""Растеризация страниц PDF для моделей. Бэкенд выбирается автоматически (PyMuPDF -> pypdfium2).

TODO: когда будет готов `readers/pdf_*.py`, заменить на `BookReader.render_region`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PIL import Image


class PageRenderer(Protocol):
    def page_count(self, path: str | Path) -> int: ...
    def render_page(self, path: str | Path, page_index: int, dpi: int) -> Image.Image: ...


class PyMuPdfRenderer:
    def __init__(self) -> None:
        try:
            import pymupdf as _fitz  # noqa: PLC0415
        except ImportError:
            import fitz as _fitz  # noqa: PLC0415
        self._fitz = _fitz
        self._path: str | None = None
        self._doc = None

    def _open(self, path):
        if self._path != str(path):
            if self._doc is not None:
                self._doc.close()
            self._doc, self._path = self._fitz.open(str(path)), str(path)
        return self._doc

    def page_count(self, path) -> int:
        return len(self._open(path))

    def render_page(self, path, page_index: int, dpi: int) -> Image.Image:
        page = self._open(path)[page_index]
        pix = page.get_pixmap(dpi=dpi, colorspace=self._fitz.csRGB, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


class PdfiumRenderer:
    def __init__(self) -> None:
        import pypdfium2  # noqa: PLC0415

        self._pdfium = pypdfium2
        self._path: str | None = None
        self._doc = None

    def _open(self, path):
        if self._path != str(path):
            self._doc, self._path = self._pdfium.PdfDocument(str(path)), str(path)
        return self._doc

    def page_count(self, path) -> int:
        return len(self._open(path))

    def render_page(self, path, page_index: int, dpi: int) -> Image.Image:
        bitmap = self._open(path)[page_index].render(scale=dpi / 72)
        return bitmap.to_pil().convert("RGB")


def get_renderer(name: str = "auto") -> PageRenderer:
    """name: auto | pymupdf | pdfium."""
    if name == "pymupdf":
        return PyMuPdfRenderer()
    if name == "pdfium":
        return PdfiumRenderer()
    for cls in (PyMuPdfRenderer, PdfiumRenderer):
        try:
            return cls()
        except ImportError:
            continue
    raise RuntimeError("Нужен PyMuPDF или pypdfium2 для растеризации страниц PDF.")

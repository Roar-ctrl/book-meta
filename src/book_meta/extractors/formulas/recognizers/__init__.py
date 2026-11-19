"""Распознаватели «изображение формулы -> LaTeX» за общим интерфейсом (design §3.3).

Реализует `paddle` (PP-FormulaNet).
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol

from book_meta.utils.paddle_runtime import PaddleSettings

NO_CONFIDENCE = math.nan  # если модель не отдаёт уверенность; итоговую оценку считает heuristics.latex


class FormulaRecognizer(Protocol):
    name: str

    def recognize(self, png: bytes) -> tuple[str, float]:
        """PNG кропа -> (latex, confidence). confidence = NaN, если модель её не даёт."""
        ...


def recognize_many(recognizer: FormulaRecognizer, pngs: Sequence[bytes]) -> list[tuple[str, float]]:
    """Пакетное распознавание, если реализация его умеет, иначе по одному."""
    batch = getattr(recognizer, "recognize_batch", None)
    if batch is not None:
        return list(batch(pngs))
    return [recognizer.recognize(p) for p in pngs]


def get_recognizer(name: str = "paddle", settings: PaddleSettings | None = None) -> FormulaRecognizer:
    if name == "paddle":
        from book_meta.extractors.formulas.recognizers.paddle import PaddleFormulaRecognizer  # noqa: PLC0415

        return PaddleFormulaRecognizer(settings)
    if name in {"docling", "pix2tex", "unimernet"}: # TODO: Я думаю нам одного Paddle достаточно будет.
        raise NotImplementedError(f"TODO: распознаватель {name!r} ещё не реализован")
    if name == "none":
        raise ValueError("formula_recognizer = none: распознавание отключено")
    raise ValueError(f"Неизвестный распознаватель: {name!r}")

"""Общие настройки моделей PaddleOCR и ленивый импорт.

По требованиям задания модели работают на CPU, поэтому по умолчанию `device="cpu"` и включён MKL-DNN.
Модули `readers/layout_paddle.py` и `extractors/formulas/recognizers/paddle.py` берут параметры отсюда.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ModelDependencyError(RuntimeError):
    """PaddleOCR / PaddlePaddle не установлены."""


def _default_threads() -> int:
    return max(1, min(os.cpu_count() or 4, 8))


class PaddleSettings(BaseModel):
    device: str = "cpu"                      # "cpu" | "gpu:0"
    cpu_threads: int = Field(default_factory=_default_threads, ge=1)
    enable_mkldnn: bool = True               # ускорение на Intel/AMD CPU

    layout_model: str = "PP-DocLayout_plus-L"  # быстрее и грубее: PP-DocLayout-M, PP-DocLayout-S
    layout_model_dir: Path | None = None     # папка с весами (офлайн/встраивание); None = автозагрузка
    layout_threshold: float | None = None    # None = значение по умолчанию модели
    layout_dpi: int = 150                    # модель всё равно сжимает вход, больше dpi смысла нет

    formula_model: str = "PP-FormulaNet_plus-S"  # точнее и медленнее: ..._plus-M, ..._plus-L
    formula_model_dir: Path | None = None
    formula_dpi: int = 250
    formula_batch_size: int = 4
    crop_pad_px: int = 6                     # поля вокруг кропа формулы


def import_paddleocr() -> Any:
    try:
        import paddleocr  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover - зависит от окружения
        raise ModelDependencyError(
            "Не установлен PaddleOCR. Для CPU: pip install paddlepaddle paddleocr "
            "(или extra `paddle`: pip install -e \".[paddle]\")."
        ) from e
    return paddleocr


def common_kwargs(s: PaddleSettings) -> dict[str, Any]:
    """Аргументы, общие для всех модулей PaddleOCR 3.x."""
    return {"device": s.device, "cpu_threads": s.cpu_threads, "enable_mkldnn": s.enable_mkldnn}


def result_data(res: Any) -> dict:
    """Результат модуля PaddleOCR -> внутренний словарь (формат слегка отличается между версиями)."""
    data = res.json if hasattr(res, "json") else res
    return data.get("res", data)


def pil_to_bgr(img: Any):
    """PIL.Image -> numpy BGR (PaddleOCR ожидает BGR)."""
    import numpy as np  # noqa: PLC0415

    return np.ascontiguousarray(np.asarray(img.convert("RGB"))[:, :, ::-1])


def png_to_bgr(png: bytes):
    from PIL import Image  # noqa: PLC0415

    return pil_to_bgr(Image.open(io.BytesIO(png)))

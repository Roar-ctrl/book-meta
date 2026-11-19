"""FormulaRecognizer на PP-FormulaNet (PaddleOCR 3.x), работает на CPU."""
from __future__ import annotations

import io
import logging
from collections.abc import Sequence

from PIL import Image

from book_meta.extractors.formulas.recognizers import NO_CONFIDENCE
from book_meta.utils.paddle_runtime import (
    PaddleSettings,
    common_kwargs,
    import_paddleocr,
    png_to_bgr,
    result_data,
)

log = logging.getLogger(__name__)

MIN_SIDE_PX = 8  # кроп меньше - модель на нём не работает, возвращаем пустую строку


class PaddleFormulaRecognizer:
    name = "paddle"

    def __init__(self, settings: PaddleSettings | None = None, model=None):
        self.settings = settings or PaddleSettings()
        self._model = model  # можно подставить заглушку в тестах

    @property
    def model(self):
        if self._model is None:
            s = self.settings
            kwargs = {**common_kwargs(s), "model_name": s.formula_model}
            if s.formula_model_dir:
                kwargs["model_dir"] = str(s.formula_model_dir)
            self._model = import_paddleocr().FormulaRecognition(**kwargs)
        return self._model

    def recognize(self, png: bytes) -> tuple[str, float]:
        return self.recognize_batch([png])[0]

    def recognize_batch(self, pngs: Sequence[bytes]) -> list[tuple[str, float]]:
        out: list[tuple[str, float]] = [("", NO_CONFIDENCE)] * len(pngs)
        todo: list[int] = [] # TODO: Naming a variable `todo` is funny, but impractical
        for i, p in enumerate(pngs):
            w, h = Image.open(io.BytesIO(p)).size
            if min(w, h) >= MIN_SIDE_PX:
                todo.append(i)
            else:
                log.warning("crop %dx%d слишком мал, пропущен", w, h)

        bs = max(1, self.settings.formula_batch_size)
        for start in range(0, len(todo), bs):
            chunk = todo[start:start + bs]
            results = self.model.predict([png_to_bgr(pngs[i]) for i in chunk], batch_size=bs)
            for i, res in zip(chunk, results):
                out[i] = (str(result_data(res).get("rec_formula", "")), NO_CONFIDENCE)
        return out

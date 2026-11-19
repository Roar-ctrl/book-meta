"""Адаптеры PaddleOCR проверяются на заглушке: настоящие веса в тестах не нужны."""
import io
import math
import sys
import types

import pytest
from PIL import Image

from book_meta.extractors.formulas.image_model import recognize_formulas
from book_meta.extractors.formulas.recognizers import get_recognizer, recognize_many
from book_meta.extractors.formulas.recognizers.paddle import PaddleFormulaRecognizer
from book_meta.readers.layout_base import RegionKind
from book_meta.readers.layout_paddle import PaddleLayout, map_label
from book_meta.util import paddle_runtime
from book_meta.util.paddle_runtime import PaddleSettings


class FakeResult:
    def __init__(self, d):
        self.json = {"res": d}


class FakeLayoutDetection:
    instances = []

    def __init__(self, **kw):
        self.kw = kw
        FakeLayoutDetection.instances.append(self)

    def predict(self, arr, batch_size=1):
        assert arr.ndim == 3 and arr.shape[2] == 3
        return [FakeResult({"boxes": [
            {"label": "formula", "score": 0.9, "coordinate": [100, 200, 300, 260]},       # display
            {"label": "formula", "score": 0.9, "coordinate": [150, 40, 190, 60]},         # inline
            {"label": "text", "score": 0.95, "coordinate": [50, 30, 350, 120]},
            {"label": "weird_new_label", "score": 0.7, "coordinate": [0, 0, 10, 10]},
            {"label": "image", "score": 0.8, "coordinate": [-5, 300, 1000, 5000]},        # за границей страницы
        ]})]


class FakeFormulaRecognition:
    instances = []

    def __init__(self, **kw):
        self.kw = kw
        self.calls = []
        FakeFormulaRecognition.instances.append(self)

    def predict(self, arrs, batch_size=1):
        self.calls.append(len(arrs))
        return [FakeResult({"rec_formula": "$$ x^{2} \\tag{1} $$"}) for _ in arrs]


@pytest.fixture
def fake_paddleocr(monkeypatch):
    FakeLayoutDetection.instances.clear()
    FakeFormulaRecognition.instances.clear()
    mod = types.SimpleNamespace(LayoutDetection=FakeLayoutDetection, FormulaRecognition=FakeFormulaRecognition)
    monkeypatch.setattr(paddle_runtime, "import_paddleocr", lambda: mod)
    for m in ("book_meta.readers.layout_paddle", "book_meta.extractors.formulas.recognizers.paddle"):
        monkeypatch.setattr(sys.modules[m], "import_paddleocr", lambda: mod)
    return mod


class FakeRenderer:
    def page_count(self, path):
        return 2

    def render_page(self, path, page_index, dpi):
        return Image.new("RGB", (400, 500), "white")


def png(w=40, h=20):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_label_mapping():
    assert map_label("formula") == RegionKind.FORMULA
    assert map_label("figure_title") == RegionKind.CAPTION
    assert map_label("figure_table_chart_title") == RegionKind.CAPTION
    assert map_label("something_new") == RegionKind.OTHER


def test_layout_passes_cpu_settings_and_normalizes(fake_paddleocr):
    s = PaddleSettings(cpu_threads=3, layout_model="PP-DocLayout-M", layout_model_dir="/models/dl", layout_threshold=0.4)
    layout = PaddleLayout(s, renderer=FakeRenderer())
    regions = layout.regions("x.pdf", pages=[1, 7, -1])      # несуществующие страницы игнорируются
    kw = FakeLayoutDetection.instances[0].kw
    assert kw["device"] == "cpu" and kw["cpu_threads"] == 3 and kw["enable_mkldnn"] is True
    assert kw["model_name"] == "PP-DocLayout-M" and kw["model_dir"] == "/models/dl" and kw["threshold"] == 0.4
    assert {r.page_index for r in regions} == {1}
    display = max((r for r in regions if r.kind == RegionKind.FORMULA), key=lambda r: r.bbox.y0)
    assert display.bbox.x0 == pytest.approx(100 / 400) and display.bbox.y1 == pytest.approx(260 / 500)
    assert all(0 <= r.bbox.x0 <= r.bbox.x1 <= 1 and 0 <= r.bbox.y0 <= r.bbox.y1 <= 1 for r in regions)
    assert [r.bbox.y0 for r in regions] == sorted(r.bbox.y0 for r in regions)
    assert any(r.kind == RegionKind.OTHER and r.raw_label == "weird_new_label" for r in regions)


def test_layout_default_kwargs_have_no_optional_keys(fake_paddleocr):
    PaddleLayout(renderer=FakeRenderer()).regions("x.pdf", pages=[0])
    kw = FakeLayoutDetection.instances[0].kw
    assert "model_dir" not in kw and "threshold" not in kw and kw["device"] == "cpu"


def test_recognizer_batches_and_skips_tiny(fake_paddleocr):
    rec = PaddleFormulaRecognizer(PaddleSettings(formula_batch_size=2, formula_model="PP-FormulaNet_plus-S"))
    out = rec.recognize_batch([png(), png(), png(), png(3, 3), png()])
    assert [bool(o[0]) for o in out] == [True, True, True, False, True]
    assert out[3][0] == "" and math.isnan(out[3][1])
    assert FakeFormulaRecognition.instances[0].calls == [2, 2]
    assert FakeFormulaRecognition.instances[0].kw["model_name"] == "PP-FormulaNet_plus-S"


def test_recognize_many_falls_back_to_single():
    class Single:
        name = "single"

        def recognize(self, p):
            return ("a", 1.0)

    assert recognize_many(Single(), [b"1", b"2"]) == [("a", 1.0), ("a", 1.0)]


def test_factory():
    with pytest.raises(NotImplementedError):
        get_recognizer("pix2tex")
    with pytest.raises(ValueError):
        get_recognizer("nope")


def test_full_model_pipeline(fake_paddleocr):
    s = PaddleSettings()
    run = recognize_formulas(
        "x.pdf", layout=PaddleLayout(s, renderer=FakeRenderer()),
        recognizer=PaddleFormulaRecognizer(s), renderer=FakeRenderer(), settings=s, pages=[0],
    )
    assert len(run.formulas) == 1                       # inline отброшен
    f = run.formulas[0]
    assert f.latex == "x^{2}" and f.raw_latex.startswith("$$")
    assert {h.rule for h in f.hits} == {"strip_math_delimiters", "strip_tag", "collapse_whitespace"}
    assert f.issues == [] and f.confidence == 1.0 and f.png.startswith(b"\x89PNG")
    dropped = [r for h in run.region_hits[0] if h.rule == "drop_inline_formulas" for r in h.removed]
    assert len(dropped) == 1

    run2 = recognize_formulas(
        "x.pdf", layout=PaddleLayout(s, renderer=FakeRenderer()),
        recognizer=PaddleFormulaRecognizer(s), renderer=FakeRenderer(), settings=s, pages=[0], include_inline=True,
    )
    assert len(run2.formulas) == 2

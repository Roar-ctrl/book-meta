import json
import shutil
from dataclasses import replace

import pytest
from PIL import Image

from book_meta.extractors.formulas import mathml
from book_meta.extractors.formulas.cascade import candidate_to_formula
from book_meta.extractors.formulas.image_model import FormulaCandidate, crop_png
from book_meta.models.document import BookDocument
from book_meta.models.location import Rect, Zone


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="Требуется Pandoc в PATH")
def test_mathml_batch_uses_one_process_and_preserves_positions(monkeypatch):
    formulas = [
        "<math><mi>x</mi><mo>+</mo><mn>1</mn></math>",
        "<math><mi>x</math>",
        "<math><unsupported/><mi>x</mi></math>",
        '<m:math xmlns:m="http://www.w3.org/1998/Math/MathML" display="block">'
        "<m:mfrac><m:mi>a</m:mi><m:mi>b</m:mi></m:mfrac></m:math>",
        "<math><semantics><msqrt><mi>α</mi></msqrt>"
        '<annotation encoding="application/x-tex">author-source</annotation></semantics></math>',
        "<math/>",
    ]
    original_run = mathml.subprocess.run
    calls = []

    def run(*args, **kwargs):
        calls.append(args[0])
        return original_run(*args, **kwargs)

    monkeypatch.setattr(mathml.subprocess, "run", run)
    assert mathml.mathml_to_latex_batch(iter(formulas)) == [
        "x + 1", None, None, r"\frac{a}{b}", r"\sqrt{\alpha}", None,
    ]
    assert len(calls) == 1
    assert mathml.mathml_to_latex(formulas[0]) == "x + 1"


def test_mathml_skips_pandoc_for_empty_or_invalid_input():
    assert mathml.mathml_to_latex_batch([], pandoc="missing-pandoc") == []
    assert mathml.mathml_to_latex("<p>text</p>", pandoc="missing-pandoc") is None


def test_candidate_to_formula_saves_crop_and_only_exports_formula_fields(tmp_path):
    bbox = Rect(x0=0.7, y0=0.0, x1=0.9, y1=0.2)
    png, _ = crop_png(Image.new("RGB", (100, 100), "white"), bbox, pad_px=0)
    candidate = FormulaCandidate(
        page_index=3, bbox=bbox, latex="x^2", raw_latex="$$ x^2 $$",
        confidence=0.8, layout_confidence=0.9, issues=["unbalanced braces"], hits=[], png=png,
    )
    formula = candidate_to_formula(
        candidate, order=1, block_idx=12, model_version="PP-FormulaNet_plus-S",
        output_dir=tmp_path, page_label="4",
    )
    assert formula.id == "eq_0001"
    assert formula.location.order == 1 and formula.location.block_idx == 12
    assert formula.location.page.page_index == 3 and formula.location.page.page_label == "4"
    assert formula.location.page.bbox == bbox and formula.location.page.zone == Zone.TOP_RIGHT
    assert formula.image_path == "formulas/eq_0001.png"
    assert (tmp_path / formula.image_path).read_bytes() == png

    document = BookDocument(book_id="book", source={}, bibliography={"cite_key": "book"}, formulas=[formula])
    exported = json.loads(document.model_dump_json())["formulas"][0]
    assert exported["latex"] == "x^2" and exported["source"] == "image_model"
    assert exported["prov"] == {
        "extractor": "formula.image_model", "method": "model", "version": "PP-FormulaNet_plus-S",
        "confidence": 0.8, "needs_review": True,
    }
    assert not {"raw_latex", "hits", "layout_confidence", "png", "issues"} & exported.keys()
    assert candidate.raw_latex == "$$ x^2 $$" and candidate.png == png

    without_crop = candidate_to_formula(
        replace(candidate, png=b"", issues=[]), order=2, block_idx=13,
        model_version="PP-FormulaNet_plus-S", output_dir=tmp_path,
    )
    assert without_crop.image_path is None and not without_crop.prov.needs_review
    assert list((tmp_path / "formulas").iterdir()) == [tmp_path / formula.image_path]

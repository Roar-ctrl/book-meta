import pytest

from book_meta.heuristics import PageContext, default_rules, latex_rule, region_rule
from book_meta.heuristics.base import REGISTRY
from book_meta.models.location import Rect
from book_meta.readers.layout_base import Region, RegionKind


def reg(kind, x0, y0, x1, y1, conf=0.9, page=0):
    return Region(kind=kind, raw_label=kind.value, bbox=Rect(x0=x0, y0=y0, x1=x1, y1=y1), page_index=page, confidence=conf)


TEXT = reg(RegionKind.TEXT, 0.1, 0.1, 0.9, 0.3)
INLINE = reg(RegionKind.FORMULA, 0.4, 0.15, 0.5, 0.18)
DISPLAY = reg(RegionKind.FORMULA, 0.3, 0.4, 0.7, 0.46)
HEADER = reg(RegionKind.PAGE_HEADER, 0.1, 0.0, 0.9, 0.05)
IN_HEADER = reg(RegionKind.FORMULA, 0.4, 0.01, 0.5, 0.04)


def run(regions, **kw):
    return default_rules(strict=True, **kw).apply_regions(regions, PageContext(0, regions))


def test_inline_dropped_display_kept():
    out, hits = run([TEXT, INLINE, DISPLAY])
    assert INLINE not in out and DISPLAY in out and TEXT in out
    h = next(h for h in hits if h.rule == "drop_inline_formulas")
    assert h.removed == (INLINE,)


def test_include_inline_disables_rule():
    out, hits = run([TEXT, INLINE, DISPLAY], disabled=["drop_inline_formulas"])
    assert INLINE in out
    assert all(h.rule != "drop_inline_formulas" for h in hits)


def test_header_formula_dropped():
    out, _ = run([HEADER, IN_HEADER, DISPLAY])
    assert IN_HEADER not in out and DISPLAY in out


def test_low_confidence_and_degenerate_dropped():
    weak = reg(RegionKind.FORMULA, 0.3, 0.6, 0.7, 0.66, conf=0.2)
    tiny = reg(RegionKind.FORMULA, 0.3, 0.7, 0.301, 0.701)
    out, _ = run([weak, tiny, DISPLAY])
    assert out == [DISPLAY]


def test_custom_rule_and_override():
    @region_rule("test_drop_everything", order=1)
    def drop_all(regions, ctx):
        return []

    try:
        out, hits = run([TEXT, DISPLAY])
        assert out == [] and hits[0].rule == "test_drop_everything"

        @region_rule("test_drop_everything", order=1)  # то же имя заменяет правило
        def keep_all(regions, ctx):
            return regions

        out, _ = run([TEXT, DISPLAY])
        assert DISPLAY in out
    finally:
        REGISTRY._entries.pop("test_drop_everything", None)


def test_broken_rule_does_not_kill_run_unless_strict():
    @latex_rule("test_boom")
    def boom(latex, ctx):
        raise RuntimeError("boom")

    try:
        from book_meta.heuristics import LatexContext

        latex, hits = default_rules(strict=False).apply_latex("x", LatexContext())
        assert latex == "x" and any(h.rule == "test_boom" and "boom" in h.detail for h in hits)
        with pytest.raises(RuntimeError):
            default_rules(strict=True).apply_latex("x", LatexContext())
    finally:
        REGISTRY._entries.pop("test_boom", None)

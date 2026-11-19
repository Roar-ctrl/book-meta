import pytest

from book_meta.rules import LatexContext, default_rules
from book_meta.rules.latex import confidence_from_issues

CTX = LatexContext()


@pytest.fixture
def rules():
    return default_rules(strict=True)


@pytest.mark.parametrize("raw,expected", [
    ("$$ x^{2} $$", "x^{2}"),
    ("\\[ a + b \\]", "a + b"),
    ("$x$", "x"),
    ("x   +\n y", "x + y"),
    ("\\frac{a}{b} \\tag{3.14}", "\\frac{a}{b}"),
    ("$$ \\int f \\tag*{(2)} $$", "\\int f"),
])
def test_rules(rules, raw, expected):
    assert rules.apply_latex(raw, CTX)[0] == expected


def test_clean_latex_has_no_hits_and_full_confidence(rules):
    latex, hits = rules.apply_latex("\\frac{a}{b}", CTX)
    assert hits == []
    assert confidence_from_issues(rules.check_latex(latex, CTX)) == 1.0


@pytest.mark.parametrize("latex,name", [
    ("", "empty"),
    ("\\frac{a}{b", "unbalanced_braces"),
    ("\\left( x", "unbalanced_left_right"),
    ("x = " + "\\alpha + \\beta " * 8, "repetition_loop"),
    ("x" * 1300, "too_long"),
])
def test_checks_find_problems(rules, latex, name):
    issues = rules.check_latex(latex, CTX)
    assert any(i.startswith(name + ":") for i in issues), issues


def test_escaped_braces_and_leftarrow_are_fine(rules):
    assert rules.check_latex("\\{ a \\} \\leftarrow b \\rightarrow c", CTX) == []


def test_matrix_of_few_zeros_is_not_a_loop(rules):
    assert rules.check_latex("\\begin{pmatrix} 0 & 0 & 0 \\\\ 0 & 0 & 0 \\end{pmatrix}", CTX) == []


def test_confidence():
    assert confidence_from_issues([]) == 1.0
    assert confidence_from_issues(["unbalanced_braces: x"]) == pytest.approx(0.65)
    assert confidence_from_issues(["empty: пустой результат", "a: b"]) == 0.0
    assert confidence_from_issues(["a: 1", "b: 2", "c: 3", "d: 4"]) == 0.0

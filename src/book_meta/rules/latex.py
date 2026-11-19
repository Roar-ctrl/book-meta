"""Правила над LaTeX от модели. Модель не отдаёт уверенность, поэтому проверки её заменяют.

TODO: сверка с TeX-аннотацией/MathML (EPUB) и проверка через pylatexenc - formulas/cascade.py.
"""
from __future__ import annotations

import re

from book_meta.rules.base import LatexContext, latex_check, latex_rule

MAX_LEN = 1200            # длиннее - почти наверняка зацикливание декодера
CHECK_PENALTY = 0.35      # снижение confidence за каждую найденную проблему

_DELIMS = (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$"))
_TAG = re.compile(r"\\tag\*?\s*\{[^{}]*\}")
_LOOP = re.compile(r"(.{6,}?)\1{4,}")
_LEFT = re.compile(r"\\left(?![A-Za-z])")
_RIGHT = re.compile(r"\\right(?![A-Za-z])")


# Правила
@latex_rule("strip_math_delimiters", order=10)
def strip_math_delimiters(latex: str, ctx: LatexContext) -> str:
    s = latex.strip()
    changed = True
    while changed:
        changed = False
        for a, b in _DELIMS:
            if len(s) >= len(a) + len(b) and s.startswith(a) and s.endswith(b):
                s = s[len(a): len(s) - len(b)].strip()
                changed = True
                break
    return s


@latex_rule("strip_tag", order=20)
def strip_tag(latex: str, ctx: LatexContext) -> str:
    """Номер формулы не должен оставаться в LaTeX (design §3.3).

    TODO: вместо удаления сохранять номер в Formula.number (formulas/numbering.py).
    """
    return _TAG.sub("", latex)


@latex_rule("collapse_whitespace", order=90)
def collapse_whitespace(latex: str, ctx: LatexContext) -> str:
    return re.sub(r"\s+", " ", latex).strip()


# Проверки
def _count_unescaped(s: str, ch: str) -> int:
    n, i = 0, 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == ch:
            n += 1
        i += 1
    return n


@latex_check("empty", order=10)
def check_empty(latex: str, ctx: LatexContext) -> str | None:
    return "пустой результат" if not latex.strip() else None


@latex_check("unbalanced_braces", order=20)
def check_braces(latex: str, ctx: LatexContext) -> str | None:
    o, c = _count_unescaped(latex, "{"), _count_unescaped(latex, "}")
    return f"скобок «{{» {o}, «}}» {c}" if o != c else None


@latex_check("unbalanced_left_right", order=30)
def check_left_right(latex: str, ctx: LatexContext) -> str | None:
    l, r = len(_LEFT.findall(latex)), len(_RIGHT.findall(latex))
    return f"\\left: {l}, \\right: {r}" if l != r else None


@latex_check("repetition_loop", order=40)
def check_loop(latex: str, ctx: LatexContext) -> str | None:
    m = _LOOP.search(latex)
    return f"повтор фрагмента «{m.group(1)[:30]}»" if m else None


@latex_check("too_long", order=50)
def check_long(latex: str, ctx: LatexContext) -> str | None:
    return f"длина {len(latex)} > {MAX_LEN}" if len(latex) > MAX_LEN else None


def confidence_from_issues(issues: list[str]) -> float:
    """Оценка 0..1 вместо уверенности модели, которой у PP-FormulaNet нет."""
    if any(i.startswith("empty:") for i in issues):
        return 0.0
    return max(0.0, 1.0 - CHECK_PENALTY * len(issues))

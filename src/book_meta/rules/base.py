"""Каркас эвристик: правила регистрируются декоратором и применяются по порядку.

Три вида правил:
  * region_rule  - получает список регионов страницы, возвращает (отфильтрованный/изменённый) список;
  * latex_rule   - получает LaTeX от модели, возвращает исправленный LaTeX;
  * latex_check  - ничего не меняет, возвращает текст проблемы или None. Проблемы снижают confidence.

Каждое сработавшее правило оставляет `RuleHit` (что и где изменилось) - по ним видно, какое правило
что испортило. Ошибка внутри правила не роняет прогон по книге (кроме `strict=True`, он нужен тестам).

Добавить правило:

    from book_meta.heuristics import latex_rule

    @latex_rule("fix_my_case", order=50)
    def fix_my_case(latex: str, ctx) -> str:
        return latex.replace("\\\\mathbb{R}", "\\\\mathbb R")

Правило с тем же именем заменяет уже зарегистрированное (так можно переопределить стандартное).
Выключить правило: `default_rules(disabled=["drop_inline_formulas"])`.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from book_meta.readers.layout_base import Region

log = logging.getLogger(__name__)


class Kind(StrEnum):
    REGIONS = "regions"
    LATEX = "latex"
    CHECK = "check"


@dataclass
class PageContext:
    page_index: int
    regions: list[Region]            # все регионы страницы до применения правил


@dataclass
class LatexContext:
    width_px: int | None = None      # размер кропа
    height_px: int | None = None
    region: Region | None = None


@dataclass(frozen=True)
class RuleHit:
    rule: str
    kind: Kind
    detail: str = ""
    removed: tuple[Region, ...] = field(default=(), compare=False)


RegionRule = Callable[[list[Region], PageContext], list[Region]]
LatexRule = Callable[[str, LatexContext], str]
LatexCheck = Callable[[str, LatexContext], "str | None"]


@dataclass(frozen=True)
class _Entry:
    name: str
    kind: Kind
    order: int
    fn: Callable


def _short(s: str, n: int = 80) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


class RuleSet:
    def __init__(self, entries: Iterable[_Entry] = (), disabled: Iterable[str] = (), strict: bool = False):
        self._entries: dict[str, _Entry] = {e.name: e for e in entries}
        self.disabled = set(disabled)
        self.strict = strict

    # регистрация
    def add(self, name: str, kind: Kind, fn: Callable, order: int = 100) -> None:
        self._entries[name] = _Entry(name, kind, order, fn)

    def derive(self, disabled: Iterable[str] = (), strict: bool = False) -> "RuleSet":
        return RuleSet(self._entries.values(), disabled, strict)

    def names(self, kind: Kind | None = None) -> list[str]:
        return [e.name for e in self._active(kind)] if kind else [e.name for e in self._entries.values()]

    def _active(self, kind: Kind | None) -> list[_Entry]:
        es = [e for e in self._entries.values() if e.name not in self.disabled and (kind is None or e.kind == kind)]
        return sorted(es, key=lambda e: e.order)

    def _call(self, e: _Entry, *args):
        try:
            return e.fn(*args), None
        except Exception as exc:  # noqa: BLE001 - правила пишутся быстро, прогон книги не должен падать
            if self.strict:
                raise
            log.exception("rule %s failed", e.name)
            return None, f"ошибка правила: {exc!r}"

    # применение
    def apply_regions(self, regions: list[Region], ctx: PageContext) -> tuple[list[Region], list[RuleHit]]:
        hits: list[RuleHit] = []
        cur = list(regions)
        for e in self._active(Kind.REGIONS):
            new, err = self._call(e, list(cur), ctx)
            if err:
                hits.append(RuleHit(e.name, Kind.REGIONS, err))
                continue
            removed = tuple(r for r in cur if r not in new)
            added = [r for r in new if r not in cur]
            if removed or added:
                hits.append(RuleHit(e.name, Kind.REGIONS, f"убрано {len(removed)}, добавлено/изменено {len(added)}", removed))
            cur = new
        return cur, hits

    def apply_latex(self, latex: str, ctx: LatexContext) -> tuple[str, list[RuleHit]]:
        hits: list[RuleHit] = []
        cur = latex
        for e in self._active(Kind.LATEX):
            new, err = self._call(e, cur, ctx)
            if err:
                hits.append(RuleHit(e.name, Kind.LATEX, err))
                continue
            if new != cur:
                hits.append(RuleHit(e.name, Kind.LATEX, f"{_short(cur)!r} -> {_short(new)!r}"))
                cur = new
        return cur, hits

    def check_latex(self, latex: str, ctx: LatexContext) -> list[str]:
        issues: list[str] = []
        for e in self._active(Kind.CHECK):
            msg, err = self._call(e, latex, ctx)
            if err:
                issues.append(f"{e.name}: {err}")
            elif msg:
                issues.append(f"{e.name}: {msg}")
        return issues


REGISTRY = RuleSet()


def region_rule(name: str, *, order: int = 100):
    def deco(fn: RegionRule) -> RegionRule:
        REGISTRY.add(name, Kind.REGIONS, fn, order)
        return fn
    return deco


def latex_rule(name: str, *, order: int = 100):
    def deco(fn: LatexRule) -> LatexRule:
        REGISTRY.add(name, Kind.LATEX, fn, order)
        return fn
    return deco


def latex_check(name: str, *, order: int = 100):
    def deco(fn: LatexCheck) -> LatexCheck:
        REGISTRY.add(name, Kind.CHECK, fn, order)
        return fn
    return deco


def default_rules(disabled: Iterable[str] = (), strict: bool = False) -> RuleSet:
    """Набор со всеми зарегистрированными правилами (стартовые + ваши, если модуль с ними импортирован)."""
    from book_meta.rules import latex, regions  # noqa: F401, PLC0415 - регистрация при импорте

    return REGISTRY.derive(disabled, strict)

"""Эвристики поверх модели. См. base.py (как добавить правило), regions.py и latex.py (стартовый набор)."""
from book_meta.rules.base import (
    Kind,
    LatexContext,
    PageContext,
    RuleHit,
    RuleSet,
    default_rules,
    latex_check,
    latex_rule,
    region_rule,
)

__all__ = [
    "Kind", "LatexContext", "PageContext", "RuleHit", "RuleSet",
    "default_rules", "latex_check", "latex_rule", "region_rule",
]

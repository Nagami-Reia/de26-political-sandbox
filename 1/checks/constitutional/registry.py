from __future__ import annotations

from ..engine import CheckEngine, RuleRegistry
from . import (
    art30_37, art58, art62, art63, art64, art65, art65a, art66, art67, art68,
    art69, art80a, art83_87, art87a, art115ab,
)


ARTICLE_MODULES = (
    art30_37,
    art58,
    art62,
    art63,
    art64,
    art65,
    art65a,
    art66,
    art67,
    art68,
    art69,
    art80a,
    art83_87,
    art87a,
    art115ab,
)


def build_constitutional_registry() -> RuleRegistry:
    return RuleRegistry(
        rule
        for module in ARTICLE_MODULES
        for rule in module.RULES
    )


def build_gg_check_engine() -> CheckEngine:
    return CheckEngine({"constitutional": build_constitutional_registry()})

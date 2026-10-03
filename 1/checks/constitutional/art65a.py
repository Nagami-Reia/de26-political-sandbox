from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed


def check_art65a(context, intent):
    defence_case = bool(context.facts.get("defence_case_promulgated", False))
    if defence_case:
        if context.holds_office(intent.actor, "federal_chancellor"):
            return passed("GG_65A_115B", "EXERCISE_COMMAND_AUTHORITY_IN_DEFENCE_CASE")
        return blocked(
            "GG_65A_115B", "COMMAND_AUTHORITY_TRANSFERRED_TO_CHANCELLOR",
            "federal_chancellor",
        )
    if not context.has_role(intent.actor, "federal_minister:defence"):
        return blocked(
            "GG_65A", "COMMAND_AUTHORITY_RESERVED_TO_DEFENCE_MINISTER",
            "federal_minister:defence",
        )
    return passed("GG_65A", "EXERCISE_COMMAND_AUTHORITY")


RULES = (
    CompiledRule(
        "GG_65A", frozenset({"command_armed_forces"}), check_art65a,
        GG_AUTHORITY, "Art. 65a Abs. 1, Art. 115b GG", GG_SOURCE_VERSION,
    ),
)

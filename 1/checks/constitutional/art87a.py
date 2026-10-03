from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed


def check_art87a_civilian_protection(context, intent):
    if not context.has_role(intent.actor, "federal_government"):
        return blocked("GG_87A_3", "FEDERAL_GOVERNMENT_REQUIRED", "federal_government")
    tension = bool(context.facts.get("state_of_tension_determined", False))
    defence = bool(context.facts.get("defence_case_promulgated", False))
    if not (tension or defence):
        return blocked(
            "GG_87A_3", "STATE_OF_TENSION_OR_DEFENCE_REQUIRED",
            "state_of_tension_or_defence",
            alternatives=("police_protection", "administrative_assistance", "determine_state_of_tension"),
        )
    return passed(
        "GG_87A_3", "ARMED_FORCES_MAY_PROTECT_CIVILIAN_OBJECTS",
        "COOPERATION_WITH_COMPETENT_AUTHORITIES_REQUIRED",
        constitutional_state="defence" if defence else "tension",
    )


RULES = (
    CompiledRule(
        "GG_87A_3", frozenset({"deploy_armed_forces_to_protect_civilian_objects"}),
        check_art87a_civilian_protection, GG_AUTHORITY, "Art. 87a Abs. 3 GG",
        GG_SOURCE_VERSION,
    ),
)


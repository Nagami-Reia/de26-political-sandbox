from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed


EXEMPT_ACTS = frozenset({
    "appoint_chancellor",
    "dismiss_chancellor_after_art67",
    "dissolve_bundestag_after_art63",
    "request_caretaker_continuation_art69",
})


def check_art58(context, intent):
    if not context.has_role(intent.actor, "federal_president"):
        return blocked("GG_58", "PRESIDENTIAL_ACT_REQUIRED")
    act_type = str(intent.payload.get("presidential_act_type", intent.intent_type))
    if act_type in EXEMPT_ACTS:
        return passed("GG_58", "COUNTERSIGNATURE_EXCEPTION")
    if not intent.payload.get("countersigned", False):
        return blocked("GG_58", "COUNTERSIGNATURE_REQUIRED", "chancellor_or_competent_minister")
    return passed("GG_58", "PRESIDENTIAL_ACT_COUNTERSIGNED")


RULES = (
    CompiledRule(
        "GG_58", frozenset({"issue_presidential_order"}), check_art58,
        GG_AUTHORITY, "Art. 58 GG", GG_SOURCE_VERSION,
    ),
)

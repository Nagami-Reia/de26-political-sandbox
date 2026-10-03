from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed


def check_art69(context, intent):
    if intent.intent_type == "appoint_vice_chancellor":
        if not context.has_role(intent.actor, "federal_chancellor"):
            return blocked("GG_69", "ONLY_CHANCELLOR_APPOINTS_DEPUTY")
        target_roles = context.actor_roles.get(intent.target or "", frozenset())
        if not (
            "federal_minister" in target_roles
            or any(role.startswith("federal_minister:") for role in target_roles)
        ):
            return blocked("GG_69", "DEPUTY_MUST_BE_FEDERAL_MINISTER", "federal_minister")
        return passed("GG_69", "APPOINT_VICE_CHANCELLOR")
    if intent.intent_type == "end_government_office":
        cause = intent.payload.get("cause")
        if cause not in {"new_bundestag_convened", "chancellor_office_ended"}:
            return blocked("GG_69", "CONSTITUTIONAL_END_CAUSE_REQUIRED")
        return passed("GG_69", "END_RELEVANT_GOVERNMENT_OFFICES", cause=str(cause))
    office = str(intent.payload.get("office", ""))
    requester = str(intent.payload.get("requester", ""))
    if office == "federal_chancellor" and requester != context.office_holders.get("federal_president"):
        return blocked("GG_69", "PRESIDENTIAL_REQUEST_REQUIRED_FOR_CARETAKER_CHANCELLOR")
    if office.startswith("federal_minister") and requester not in {
        context.office_holders.get("federal_president"),
        context.office_holders.get("federal_chancellor"),
    }:
        return blocked("GG_69", "CHANCELLOR_OR_PRESIDENT_REQUEST_REQUIRED_FOR_CARETAKER_MINISTER")
    return passed("GG_69", "CONTINUE_CARETAKER_DUTIES_UNTIL_SUCCESSOR")


RULES = (
    CompiledRule(
        "GG_69", frozenset({
            "appoint_vice_chancellor", "end_government_office", "continue_caretaker_duties",
        }), check_art69,
        GG_AUTHORITY, "Art. 69 Abs. 1-3 GG", GG_SOURCE_VERSION,
    ),
)

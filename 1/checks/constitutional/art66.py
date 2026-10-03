from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed, routed


def check_art66(context, intent):
    is_government_member = (
        context.has_role(intent.actor, "federal_chancellor")
        or context.has_role(intent.actor, "federal_minister")
        or any(role.startswith("federal_minister:") for role in context.actor_roles.get(intent.actor, ()))
    )
    if not is_government_member:
        return passed("GG_66", "ART66_INCOMPATIBILITY_NOT_APPLICABLE_TO_ACTOR")
    external_role = str(intent.payload.get("external_role", ""))
    if external_role in {"paid_office", "business", "profession", "company_management"}:
        return blocked("GG_66", "INCOMPATIBLE_EXTERNAL_ROLE", external_role)
    if external_role == "company_supervisory_board":
        if not intent.payload.get("bundestag_consent", False):
            return routed("GG_66", "BUNDESTAG_CONSENT_ART66", "BUNDESTAG_CONSENT_REQUIRED")
        return passed("GG_66", "SUPERVISORY_BOARD_ROLE_WITH_BUNDESTAG_CONSENT")
    return blocked("GG_66", "EXTERNAL_ROLE_TYPE_REQUIRED", "external_role")


RULES = (
    CompiledRule(
        "GG_66", frozenset({"take_external_role"}), check_art66,
        GG_AUTHORITY, "Art. 66 GG", GG_SOURCE_VERSION,
    ),
)

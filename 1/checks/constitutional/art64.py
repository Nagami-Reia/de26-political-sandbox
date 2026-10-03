from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed, pending, routed


def check_art64(context, intent):
    appointing = intent.intent_type in {"propose_appoint_minister", "appoint_minister"}
    procedure_type = "GG64_MINISTER_APPOINTMENT" if appointing else "GG64_MINISTER_DISMISSAL"
    if intent.intent_type.startswith("propose_"):
        if not context.has_role(intent.actor, "federal_chancellor"):
            return blocked("GG_64", "ONLY_CHANCELLOR_MAY_PROPOSE", "federal_chancellor")
        if not intent.target:
            return blocked("GG_64", "MINISTER_CANDIDATE_OR_TARGET_REQUIRED", "target")
        return routed("GG_64", procedure_type, "PRESIDENTIAL_ACT_REQUIRED", target=intent.target)
    if not context.has_role(intent.actor, "federal_president"):
        return blocked(
            "GG_64", "NO_DIRECT_AUTHORITY", "federal_president",
            alternatives=(
                "request_chancellor_proposal",
                "coalition_pressure",
                "party_pressure",
            ),
        )
    procedure = context.procedure_for(intent.payload, procedure_type)
    if procedure is None:
        return routed("GG_64", procedure_type, "CHANCELLOR_PROPOSAL_REQUIRED")
    if not procedure.metadata.get("chancellor_proposal", False):
        return pending("GG_64", "AWAITING_CHANCELLOR_PROPOSAL", "chancellor_proposal")
    if intent.target and procedure.target and intent.target != procedure.target:
        return blocked("GG_64", "TARGET_DIFFERS_FROM_CHANCELLOR_PROPOSAL")
    effect = "APPOINT_FEDERAL_MINISTER" if appointing else "DISMISS_FEDERAL_MINISTER"
    return passed("GG_64", effect, target=intent.target or procedure.target)


RULES = (
    CompiledRule(
        "GG_64", frozenset({
            "propose_appoint_minister", "appoint_minister",
            "propose_dismiss_minister", "dismiss_minister",
        }), check_art64,
        GG_AUTHORITY, "Art. 64 Abs. 1-2 GG", GG_SOURCE_VERSION,
    ),
)

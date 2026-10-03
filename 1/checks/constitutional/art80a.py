from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed, pending, routed


def check_art80a(context, intent):
    if not context.has_role(intent.actor, "bundestag"):
        return blocked("GG_80A", "BUNDESTAG_DETERMINATION_REQUIRED", "bundestag")
    procedure = context.procedure_for(intent.payload, "GG80A_STATE_OF_TENSION")
    if procedure is None:
        return routed("GG_80A", "GG80A_STATE_OF_TENSION")
    if not procedure.metadata.get("vote_completed", False):
        return pending("GG_80A", "AWAITING_BUNDESTAG_VOTE", "vote_result")
    votes_cast = procedure.votes_yes + procedure.votes_no
    required = (2 * votes_cast + 2) // 3
    if procedure.votes_yes < required:
        return blocked("GG_80A", "TWO_THIRDS_OF_VOTES_CAST_NOT_REACHED", "two_thirds_votes_cast")
    return passed(
        "GG_80A", "STATE_OF_TENSION_DETERMINED",
        yes_votes=procedure.votes_yes, votes_cast=votes_cast, required_yes=required,
    )


RULES = (
    CompiledRule(
        "GG_80A", frozenset({"determine_state_of_tension"}), check_art80a,
        GG_AUTHORITY, "Art. 80a Abs. 1 GG", GG_SOURCE_VERSION,
    ),
)


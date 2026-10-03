from __future__ import annotations

from ..base import CompiledRule
from .common import (
    GG_AUTHORITY, GG_SOURCE_VERSION, blocked, majority_diagnostic, passed, pending, routed,
)


def check_art67(context, intent):
    if intent.intent_type == "dismiss_chancellor":
        return blocked(
            "GG_67", "NO_DIRECT_DISMISSAL_AUTHORITY",
            alternatives=("party_pressure", "coalition_pressure", "replace_chancellor"),
        )
    if not (
        context.has_role(intent.actor, "bundestag")
        or context.has_role(intent.actor, "bundestag_member")
    ):
        return blocked("GG_67", "BUNDESTAG_PROCEDURE_REQUIRED", "bundestag_or_member")
    procedure = context.procedure_for(intent.payload, "GG67_CONSTRUCTIVE_NO_CONFIDENCE")
    if procedure is None:
        return routed("GG_67", "GG67_CONSTRUCTIVE_NO_CONFIDENCE")
    diagnostics = majority_diagnostic(context, procedure.votes_yes) | {
        "elapsed_hours": procedure.elapsed_hours(context.now_hours),
        "candidate": procedure.candidate,
    }
    if not procedure.candidate:
        return blocked("GG_67", "SUCCESSOR_REQUIRED", "candidate")
    if procedure.elapsed_hours(context.now_hours) < 48:
        return pending("GG_67", "WAITING_PERIOD", "48_hours", **diagnostics)
    if not procedure.metadata.get("vote_completed", False):
        return pending("GG_67", "AWAITING_VOTE", "vote_result", **diagnostics)
    if procedure.votes_yes < context.bundestag.member_majority:
        return blocked("GG_67", "MEMBER_MAJORITY_NOT_REACHED", "member_majority")
    return passed(
        "GG_67",
        "BUNDESTAG_ELECTS_SUCCESSOR",
        "REQUEST_PRESIDENT_DISMISS_CHANCELLOR",
        "PRESIDENT_MUST_DISMISS_AND_APPOINT",
        **diagnostics,
    )


RULES = (
    CompiledRule(
        "GG_67", frozenset({"dismiss_chancellor", "replace_chancellor"}), check_art67,
        GG_AUTHORITY, "Art. 67 Abs. 1-2 GG", GG_SOURCE_VERSION,
    ),
)

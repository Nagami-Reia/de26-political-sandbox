from __future__ import annotations

from ..base import CompiledRule
from .common import (
    GG_AUTHORITY, GG_SOURCE_VERSION, blocked, majority_diagnostic, passed, pending, routed,
)


def check_art68(context, intent):
    if intent.intent_type == "request_confidence":
        if not context.has_role(intent.actor, "federal_chancellor"):
            return blocked("GG_68", "ONLY_CHANCELLOR_MAY_REQUEST_CONFIDENCE")
        procedure = context.procedure_for(intent.payload, "GG68_CONFIDENCE_MOTION")
        if procedure is None:
            return routed("GG_68", "GG68_CONFIDENCE_MOTION")
        diagnostics = majority_diagnostic(context, procedure.votes_yes) | {
            "elapsed_hours": procedure.elapsed_hours(context.now_hours),
        }
        if procedure.elapsed_hours(context.now_hours) < 48:
            return pending("GG_68", "WAITING_PERIOD", "48_hours", **diagnostics)
        if not procedure.metadata.get("vote_completed", False):
            return pending("GG_68", "AWAITING_VOTE", "vote_result", **diagnostics)
        if procedure.votes_yes >= context.bundestag.member_majority:
            return passed("GG_68", "CONFIDENCE_GRANTED", **diagnostics)
        return passed(
            "GG_68", "CONFIDENCE_NOT_GRANTED", "OPEN_DISSOLUTION_WINDOW_21_DAYS",
            **diagnostics,
        )

    if not context.has_role(intent.actor, "federal_president"):
        return blocked("GG_68", "ONLY_PRESIDENT_MAY_DISSOLVE_UNDER_ART68")
    procedure = context.procedure_for(intent.payload, "GG68_CONFIDENCE_MOTION")
    if procedure is None or not procedure.metadata.get("vote_completed", False):
        return blocked("GG_68", "FAILED_CONFIDENCE_VOTE_REQUIRED", "failed_confidence_vote")
    if procedure.votes_yes >= context.bundestag.member_majority:
        return blocked("GG_68", "CONFIDENCE_WAS_GRANTED")
    if not intent.payload.get("chancellor_proposal", False):
        return blocked("GG_68", "CHANCELLOR_PROPOSAL_REQUIRED", "chancellor_proposal")
    elapsed = procedure.elapsed_hours(context.now_hours)
    if elapsed > 21 * 24:
        return blocked("GG_68", "DISSOLUTION_WINDOW_EXPIRED", "within_21_days")
    if intent.payload.get("successor_elected_by_member_majority", False):
        return blocked("GG_68", "DISSOLUTION_POWER_EXPIRED_AFTER_SUCCESSOR_ELECTION")
    return passed("GG_68", "PRESIDENT_MAY_DISSOLVE_BUNDESTAG", elapsed_hours=elapsed)


RULES = (
    CompiledRule(
        "GG_68", frozenset({"request_confidence", "dissolve_bundestag_after_confidence_loss"}),
        check_art68, GG_AUTHORITY, "Art. 68 Abs. 1-2 GG", GG_SOURCE_VERSION,
    ),
)

from __future__ import annotations

from ..base import CompiledRule
from .common import (
    GG_AUTHORITY, GG_SOURCE_VERSION, blocked, majority_diagnostic, passed, pending, routed,
)


def check_art63(context, intent):
    procedure = context.procedure_for(intent.payload, "GG63_CHANCELLOR_ELECTION")
    if procedure is None:
        return routed("GG_63", "GG63_CHANCELLOR_ELECTION")
    if not procedure.candidate:
        return blocked("GG_63", "CANDIDATE_REQUIRED", "candidate")
    phase = procedure.metadata.get("phase", procedure.stage)
    majority = context.bundestag.member_majority
    diagnostics = majority_diagnostic(context, procedure.votes_yes) | {
        "phase": str(phase),
        "candidate": procedure.candidate,
        "elapsed_hours": procedure.elapsed_hours(context.now_hours),
    }
    if phase == "PRESIDENTIAL_PROPOSAL_REQUIRED":
        return pending("GG_63", "AWAITING_PRESIDENTIAL_PROPOSAL", "presidential_proposal", **diagnostics)
    if phase == "FIRST_BALLOT":
        if not procedure.metadata.get("presidential_proposal", False):
            return blocked("GG_63", "PRESIDENTIAL_PROPOSAL_REQUIRED", "presidential_proposal")
        if not procedure.metadata.get("vote_completed", False):
            return pending("GG_63", "AWAITING_FIRST_BALLOT", "vote_result", **diagnostics)
        if procedure.votes_yes >= majority:
            return passed("GG_63", "PRESIDENT_MUST_APPOINT_CHANCELLOR", **diagnostics)
        return _route_second_phase(diagnostics)
    if phase == "FOURTEEN_DAY_WINDOW":
        elapsed_days = procedure.elapsed_hours(context.now_hours) / 24
        if procedure.metadata.get("vote_completed", False) and procedure.votes_yes >= majority:
            return passed("GG_63", "PRESIDENT_MUST_APPOINT_CHANCELLOR", **diagnostics)
        if elapsed_days < 14:
            return pending("GG_63", "FOURTEEN_DAY_ELECTION_WINDOW_OPEN", "member_majority", **diagnostics)
        return routed("GG_63", "GG63_FINAL_BALLOT", "FINAL_BALLOT_REQUIRED", **diagnostics)
    if phase == "FINAL_BALLOT":
        if not procedure.metadata.get("vote_completed", False):
            return pending("GG_63", "AWAITING_FINAL_BALLOT", "vote_result", **diagnostics)
        if not procedure.metadata.get("plurality_winner", False):
            return blocked("GG_63", "NO_PLURALITY_WINNER_RECORDED", "plurality_winner")
        if procedure.votes_yes >= majority:
            return passed("GG_63", "PRESIDENT_MUST_APPOINT_WITHIN_SEVEN_DAYS", **diagnostics)
        return passed(
            "GG_63",
            "PRESIDENT_MAY_APPOINT_OR_DISSOLVE_WITHIN_SEVEN_DAYS",
            **diagnostics,
        )
    return blocked("GG_63", "UNKNOWN_GG63_PHASE", str(phase))


def _route_second_phase(diagnostics):
    return routed(
        "GG_63", "GG63_FOURTEEN_DAY_WINDOW", "FIRST_BALLOT_FAILED",
        **diagnostics,
    )


RULES = (
    CompiledRule(
        "GG_63", frozenset({"elect_chancellor"}), check_art63,
        GG_AUTHORITY, "Art. 63 Abs. 1-4 GG", GG_SOURCE_VERSION,
    ),
)

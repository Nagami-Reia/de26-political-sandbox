from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed, pending, routed


PROCEDURE = "GG115A_DEFENCE_CASE"


def _threshold(context, procedure):
    votes_cast = procedure.votes_yes + procedure.votes_no
    two_thirds_cast = (2 * votes_cast + 2) // 3
    required = max(context.bundestag.member_majority, two_thirds_cast)
    return votes_cast, required


def check_determine_defence_case(context, intent):
    armed_attack = bool(context.facts.get("federal_territory_attacked_by_armed_force", False))
    imminent = bool(context.facts.get("armed_attack_on_federal_territory_imminent", False))
    if not (armed_attack or imminent):
        return blocked(
            "GG_115A", "ARMED_ATTACK_ON_FEDERAL_TERRITORY_OR_IMMINENCE_NOT_ESTABLISHED",
            "armed_attack_or_imminent_attack",
            alternatives=("criminal_investigation", "nato_article4_consultation", "state_of_tension"),
        )
    if not context.has_role(intent.actor, "bundestag"):
        return blocked("GG_115A", "BUNDESTAG_DETERMINATION_REQUIRED", "bundestag")
    procedure = context.procedure_for(intent.payload, PROCEDURE)
    if procedure is None:
        return routed("GG_115A", PROCEDURE)
    if not procedure.metadata.get("federal_government_application", False):
        return blocked("GG_115A", "FEDERAL_GOVERNMENT_APPLICATION_REQUIRED",
                       "federal_government_application")
    if not procedure.metadata.get("vote_completed", False):
        return pending("GG_115A", "AWAITING_BUNDESTAG_VOTE", "vote_result")
    votes_cast, required = _threshold(context, procedure)
    if procedure.votes_yes < required:
        return blocked("GG_115A", "QUALIFIED_BUNDESTAG_MAJORITY_NOT_REACHED",
                       "two_thirds_votes_cast_and_member_majority")
    if not procedure.metadata.get("bundesrat_consent", False):
        return pending("GG_115A", "AWAITING_BUNDESRAT_CONSENT", "bundesrat_consent")
    return passed(
        "GG_115A", "DEFENCE_CASE_DETERMINED",
        yes_votes=procedure.votes_yes, votes_cast=votes_cast, required_yes=required,
    )


def check_promulgate_defence_case(context, intent):
    if not context.has_role(intent.actor, "federal_president"):
        return blocked("GG_115A_3", "FEDERAL_PRESIDENT_REQUIRED", "federal_president")
    procedure = context.procedure_for(intent.payload, PROCEDURE)
    if procedure is None or not procedure.metadata.get("determination_passed", False):
        return blocked("GG_115A_3", "VALID_DEFENCE_CASE_DETERMINATION_REQUIRED",
                       "determination_passed")
    return passed("GG_115A_3", "PROMULGATE_DEFENCE_CASE_IN_FEDERAL_LAW_GAZETTE")


def check_chancellor_assumes_command(context, intent):
    if not context.holds_office(intent.actor, "federal_chancellor"):
        return blocked("GG_115B", "FEDERAL_CHANCELLOR_REQUIRED", "federal_chancellor")
    if not context.facts.get("defence_case_promulgated", False):
        return blocked(
            "GG_115B", "DEFENCE_CASE_NOT_PROMULGATED", "defence_case_promulgated",
            alternatives=("defence_minister_command", "determine_state_of_defence"),
        )
    return passed("GG_115B", "COMMAND_AUTHORITY_TRANSFERS_TO_CHANCELLOR")


RULES = (
    CompiledRule(
        "GG_115A", frozenset({"determine_state_of_defence"}),
        check_determine_defence_case, GG_AUTHORITY, "Art. 115a Abs. 1-2 GG",
        GG_SOURCE_VERSION,
    ),
    CompiledRule(
        "GG_115A_3", frozenset({"promulgate_state_of_defence"}),
        check_promulgate_defence_case, GG_AUTHORITY, "Art. 115a Abs. 3 GG",
        GG_SOURCE_VERSION,
    ),
    CompiledRule(
        "GG_115B", frozenset({"assume_defence_command"}),
        check_chancellor_assumes_command, GG_AUTHORITY, "Art. 115b GG",
        GG_SOURCE_VERSION,
    ),
)


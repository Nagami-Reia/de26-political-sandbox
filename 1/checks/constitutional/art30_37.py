from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed, routed


def check_art30(context, intent):
    assigned_to_federation = bool(intent.payload.get("constitution_assigns_to_federation", False))
    if assigned_to_federation:
        return passed("GG_30", "FEDERAL_COMPETENCE_EXCEPTION_RECOGNIZED")
    if not context.has_role(intent.actor, "land_authority"):
        return blocked(
            "GG_30", "STATE_POWER_DEFAULTS_TO_LAENDER",
            "land_authority",
            alternatives=("seek_land_execution", "identify_constitutional_federal_competence"),
        )
    return passed("GG_30", "LAND_EXERCISES_STATE_POWER")


def check_art35(context, intent):
    if intent.intent_type == "request_administrative_assistance":
        if not (
            context.has_role(intent.actor, "federal_authority")
            or context.has_role(intent.actor, "land_authority")
        ):
            return blocked("GG_35", "PUBLIC_AUTHORITY_REQUIRED")
        return passed("GG_35", "INTERAUTHORITY_ASSISTANCE_ROUTE")
    emergency = str(intent.payload.get("emergency_type", ""))
    if intent.intent_type == "request_emergency_assistance":
        if not context.has_role(intent.actor, "land_government"):
            return blocked("GG_35", "LAND_REQUEST_REQUIRED")
        if emergency == "major_public_security":
            missing = []
            if not intent.payload.get("case_of_special_importance", False):
                missing.append("case_of_special_importance")
            if not intent.payload.get("land_police_cannot_manage_without_major_difficulty", False):
                missing.append("land_police_capacity_condition")
            if missing:
                return blocked("GG_35", "PUBLIC_SECURITY_ASSISTANCE_CONDITIONS_NOT_MET", *missing)
            return passed("GG_35", "LAND_MAY_REQUEST_FEDERAL_BORDER_POLICE_SUPPORT")
        if emergency in {"natural_disaster", "grave_accident"}:
            return passed("GG_35", "LAND_MAY_REQUEST_DISASTER_ASSISTANCE", emergency_type=emergency)
        return blocked("GG_35", "QUALIFYING_EMERGENCY_REQUIRED")
    if not context.has_role(intent.actor, "federal_government"):
        return blocked("GG_35", "FEDERAL_GOVERNMENT_REQUIRED")
    if emergency not in {"natural_disaster", "grave_accident"}:
        return blocked("GG_35", "QUALIFYING_DISASTER_REQUIRED")
    if int(intent.payload.get("affected_laender", 0)) < 2:
        return blocked("GG_35", "MULTI_LAND_DISASTER_REQUIRED", "affected_laender>=2")
    return passed(
        "GG_35", "FEDERAL_CROSS_LAND_DISASTER_COORDINATION",
        "MEASURES_END_ON_BUNDESRAT_REQUEST_OR_AFTER_DANGER",
    )


def check_art37(context, intent):
    if not context.has_role(intent.actor, "federal_government"):
        return blocked("GG_37", "FEDERAL_GOVERNMENT_REQUIRED")
    if not intent.payload.get("land_failed_federal_obligation", False):
        return blocked("GG_37", "UNFULFILLED_FEDERAL_OBLIGATION_REQUIRED")
    if not intent.payload.get("bundesrat_consent", False):
        return routed("GG_37", "BUNDESRAT_CONSENT_GG37", "BUNDESRAT_CONSENT_REQUIRED")
    return passed("GG_37", "FEDERAL_COERCION_MEASURES", "INSTRUCTION_POWER_OVER_LAENDER")


RULES = (
    CompiledRule(
        "GG_30", frozenset({"exercise_state_power"}), check_art30,
        GG_AUTHORITY, "Art. 30 GG", GG_SOURCE_VERSION,
    ),
    CompiledRule(
        "GG_35", frozenset({
            "request_administrative_assistance", "request_emergency_assistance",
            "coordinate_cross_land_disaster_response",
        }),
        check_art35, GG_AUTHORITY, "Art. 35 Abs. 1-3 GG", GG_SOURCE_VERSION,
    ),
    CompiledRule(
        "GG_37", frozenset({"apply_federal_coercion"}), check_art37,
        GG_AUTHORITY, "Art. 37 Abs. 1-2 GG", GG_SOURCE_VERSION,
    ),
)

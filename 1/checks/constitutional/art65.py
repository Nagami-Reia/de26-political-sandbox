from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed, pending, routed


def check_art65(context, intent):
    kind = intent.intent_type
    if kind == "set_policy_guidelines":
        if not context.has_role(intent.actor, "federal_chancellor"):
            return blocked("GG_65", "RICHTLINIENKOMPETENZ_RESERVED_TO_CHANCELLOR")
        return passed("GG_65", "SET_POLICY_GUIDELINES")
    if kind == "manage_ministry_portfolio":
        portfolio = intent.payload.get("portfolio")
        if not portfolio or not context.has_role(intent.actor, f"federal_minister:{portfolio}"):
            return blocked("GG_65", "PORTFOLIO_AUTHORITY_REQUIRED", f"federal_minister:{portfolio}")
        if not intent.payload.get("within_policy_guidelines", True):
            return routed("GG_65", "CABINET_DISPUTE", "OUTSIDE_CHANCELLOR_GUIDELINES")
        return passed("GG_65", "MINISTER_MANAGES_PORTFOLIO_INDEPENDENTLY")
    if kind == "resolve_ministerial_dispute":
        if not context.has_role(intent.actor, "federal_government"):
            return routed("GG_65", "CABINET_DISPUTE", "COLLECTIVE_CABINET_DECISION_REQUIRED")
        procedure = context.procedure_for(intent.payload, "CABINET_DISPUTE")
        if procedure is None or not procedure.metadata.get("decision_completed", False):
            return pending("GG_65", "AWAITING_CABINET_DECISION", "cabinet_decision")
        return passed("GG_65", "CABINET_RESOLVES_MINISTERIAL_DISPUTE")
    if kind == "adopt_cabinet_rules":
        if not context.has_role(intent.actor, "federal_government"):
            return blocked("GG_65", "CABINET_MUST_ADOPT_RULES")
        return routed("GG_65", "CABINET_RULES_APPROVAL", "PRESIDENTIAL_APPROVAL_REQUIRED")
    if kind == "approve_cabinet_rules":
        if not context.has_role(intent.actor, "federal_president"):
            return blocked("GG_65", "PRESIDENTIAL_APPROVAL_REQUIRED")
        procedure = context.procedure_for(intent.payload, "CABINET_RULES_APPROVAL")
        if procedure is None or not procedure.metadata.get("cabinet_adopted", False):
            return pending("GG_65", "AWAITING_CABINET_ADOPTION", "cabinet_adoption")
        return passed("GG_65", "CABINET_RULES_APPROVED")
    return blocked("GG_65", "UNSUPPORTED_ART65_INTENT")


RULES = (
    CompiledRule(
        "GG_65", frozenset({
            "set_policy_guidelines", "manage_ministry_portfolio",
            "resolve_ministerial_dispute", "adopt_cabinet_rules",
            "approve_cabinet_rules",
        }), check_art65,
        GG_AUTHORITY, "Art. 65 GG", GG_SOURCE_VERSION,
    ),
)

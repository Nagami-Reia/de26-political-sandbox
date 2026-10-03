from __future__ import annotations

from ..base import CompiledRule
from .administrative_structure import CONSTITUTIONAL_ADMINISTRATION_DOMAINS, administration_domain
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed, routed


SPECIAL_FEDERAL_DIRECT_DOMAINS = frozenset(
    key for key, row in CONSTITUTIONAL_ADMINISTRATION_DOMAINS.items()
    if row.mode == "FEDERAL_DIRECT"
)


def _law(context, intent, rule_id):
    law_id = intent.payload.get("law_id")
    law = context.federal_laws.get(law_id)
    if law is None:
        return None, blocked(rule_id, "FEDERAL_LAW_EXECUTION_RECORD_REQUIRED", "law_id")
    return law, None


def check_execution_mode(context, intent):
    law, error = _law(context, intent, "GG_83")
    if error:
        return error
    mode = law.administration_mode
    constitutional_domain = administration_domain(law.domain)
    if law.domain in CONSTITUTIONAL_ADMINISTRATION_DOMAINS:
        mode = constitutional_domain.mode
    if mode not in {
        "LAND_OWN_AFFAIRS", "FEDERAL_COMMISSION", "FEDERAL_DIRECT",
        "FEDERAL_PUBLIC_CORPORATION", "INDEPENDENT_FEDERAL_INSTITUTION",
    }:
        return blocked("GG_83", "UNKNOWN_ADMINISTRATION_MODE", mode)
    return passed(
        "GG_83", f"ADMINISTRATION_MODE:{mode}", law_id=law.law_id,
        domain=law.domain, citation=constitutional_domain.citation,
        compilation_status=constitutional_domain.compilation_status,
    )


def check_execute_federal_law(context, intent):
    law, error = _law(context, intent, "GG_83_86")
    if error:
        return error
    mode = (
        administration_domain(law.domain).mode
        if law.domain in CONSTITUTIONAL_ADMINISTRATION_DOMAINS
        else law.administration_mode
    )
    if mode == "LAND_OWN_AFFAIRS":
        if not context.has_role(intent.actor, "land_authority"):
            return blocked(
                "GG_83_84", "LAND_EXECUTION_IS_CONSTITUTIONAL_DEFAULT",
                "land_authority", alternatives=("coordinate_with_land", "federal_supervision"),
            )
        return passed("GG_83_84", "LAND_EXECUTES_AS_OWN_AFFAIRS")
    if mode == "FEDERAL_COMMISSION":
        if not context.has_role(intent.actor, "land_authority"):
            return blocked("GG_85", "LAND_AUTHORITY_EXECUTES_ON_FEDERAL_COMMISSION")
        return passed("GG_85", "LAND_EXECUTES_ON_FEDERAL_COMMISSION")
    if mode == "FEDERAL_DIRECT":
        if not context.has_role(intent.actor, "federal_authority"):
            return blocked("GG_86", "FEDERAL_AUTHORITY_REQUIRED")
        return passed("GG_86", "FEDERAL_DIRECT_ADMINISTRATION")
    if mode in {"FEDERAL_PUBLIC_CORPORATION", "INDEPENDENT_FEDERAL_INSTITUTION"}:
        domain = administration_domain(law.domain)
        return routed(
            "GG_87_88", f"SPECIAL_ADMINISTRATION:{law.domain}",
            "SPECIAL_CONSTITUTIONAL_AND_STATUTORY_RULES_REQUIRED",
            citation=domain.citation,
        )
    return blocked("GG_83_86", "UNKNOWN_ADMINISTRATION_MODE", str(mode))


def check_general_admin_regulation(context, intent):
    law, error = _law(context, intent, "GG_84_86")
    if error:
        return error
    if not context.has_role(intent.actor, "federal_government"):
        return blocked("GG_84_86", "FEDERAL_GOVERNMENT_REQUIRED")
    mode = (
        administration_domain(law.domain).mode
        if law.domain in CONSTITUTIONAL_ADMINISTRATION_DOMAINS
        else law.administration_mode
    )
    if mode in {"LAND_OWN_AFFAIRS", "FEDERAL_COMMISSION"} and not intent.payload.get("bundesrat_consent", False):
        article = "GG_84" if mode == "LAND_OWN_AFFAIRS" else "GG_85"
        return routed(article, f"BUNDESRAT_CONSENT_{article}", "BUNDESRAT_CONSENT_REQUIRED")
    if mode == "FEDERAL_DIRECT" and law.special_administration_rule:
        return routed("GG_86", law.special_administration_rule, "SPECIAL_STATUTORY_RULE_CONTROLS")
    if mode not in {"LAND_OWN_AFFAIRS", "FEDERAL_COMMISSION", "FEDERAL_DIRECT"}:
        domain = administration_domain(law.domain)
        return routed(
            "GG_87_88", f"SPECIAL_ADMINISTRATION:{law.domain}",
            "SPECIAL_CONSTITUTIONAL_AND_STATUTORY_RULES_REQUIRED",
            citation=domain.citation,
        )
    return passed("GG_84_86", "ISSUE_GENERAL_ADMINISTRATIVE_REGULATION", administration_mode=mode)


def check_federal_supervision(context, intent):
    law, error = _law(context, intent, "GG_84_85")
    if error:
        return error
    mode = law.administration_mode
    if mode == "LAND_OWN_AFFAIRS":
        if intent.payload.get("supervision_scope") not in {None, "legality"}:
            return blocked("GG_84", "SUPERVISION_LIMITED_TO_LEGALITY")
        if intent.intent_type == "send_federal_commissioner":
            consent = intent.payload.get("highest_land_authority_consent", False)
            override = intent.payload.get("bundesrat_consent_after_refusal", False)
            if not consent and not override:
                return routed("GG_84", "LAND_OR_BUNDESRAT_CONSENT_FOR_COMMISSIONER")
        return passed("GG_84", "FEDERAL_LEGALITY_SUPERVISION")
    if mode == "FEDERAL_COMMISSION":
        return passed("GG_85", "FEDERAL_LEGALITY_AND_EXPEDIENCY_SUPERVISION")
    return blocked("GG_84_85", "SUPERVISION_RULE_NOT_APPLICABLE_TO_MODE", str(mode))


def check_individual_instruction(context, intent):
    law, error = _law(context, intent, "GG_84_85")
    if error:
        return error
    urgent = bool(intent.payload.get("urgent", False))
    target_level = intent.payload.get("target_level", "highest_land_authority")
    if law.administration_mode == "LAND_OWN_AFFAIRS":
        if not law.authorizes_individual_instructions or not law.bundesrat_consent:
            return blocked("GG_84", "STATUTORY_AUTHORIZATION_WITH_BUNDESRAT_CONSENT_REQUIRED")
        if not context.has_role(intent.actor, "federal_government"):
            return blocked("GG_84", "FEDERAL_GOVERNMENT_REQUIRED")
    elif law.administration_mode == "FEDERAL_COMMISSION":
        if not context.has_role(intent.actor, "highest_federal_authority"):
            return blocked("GG_85", "COMPETENT_HIGHEST_FEDERAL_AUTHORITY_REQUIRED")
    else:
        return blocked("GG_84_85", "INDIVIDUAL_LAND_INSTRUCTION_NOT_APPLICABLE")
    if not urgent and target_level != "highest_land_authority":
        return blocked("GG_84_85", "INSTRUCTION_MUST_ADDRESS_HIGHEST_LAND_AUTHORITY")
    return passed("GG_84_85", "ISSUE_INDIVIDUAL_INSTRUCTION", urgent=urgent)


def check_create_federal_authority(context, intent):
    if not intent.payload.get("federal_law_enacted", False):
        return routed("GG_87", "FEDERAL_LEGISLATION", "FEDERAL_LAW_REQUIRED")
    if not intent.payload.get("federal_legislative_competence", False):
        return blocked("GG_87", "FEDERAL_LEGISLATIVE_COMPETENCE_REQUIRED")
    level = intent.payload.get("authority_level")
    if level in {"independent_higher_authority", "federal_corporation", "federal_institution"}:
        return passed("GG_87", "CREATE_FEDERAL_BODY_BY_LAW", authority_level=str(level))
    if level in {"middle_authority", "lower_authority"}:
        missing = []
        if not intent.payload.get("new_federal_task", False):
            missing.append("new_federal_task")
        if not intent.payload.get("urgent_need", False):
            missing.append("urgent_need")
        if not intent.payload.get("bundesrat_consent", False):
            missing.append("bundesrat_consent")
        if int(intent.payload.get("bundestag_yes_votes", 0)) < context.bundestag.member_majority:
            missing.append("bundestag_member_majority")
        if missing:
            return blocked("GG_87", "MIDDLE_OR_LOWER_AUTHORITY_CONDITIONS_NOT_MET", *missing)
        return passed("GG_87", "CREATE_FEDERAL_MIDDLE_OR_LOWER_AUTHORITY")
    return blocked("GG_87", "AUTHORITY_LEVEL_REQUIRED", "authority_level")


RULES = (
    CompiledRule(
        "GG_83", frozenset({"determine_federal_law_execution"}), check_execution_mode,
        GG_AUTHORITY, "Art. 83 GG", GG_SOURCE_VERSION,
    ),
    CompiledRule(
        "GG_83_86", frozenset({"execute_federal_law"}), check_execute_federal_law,
        GG_AUTHORITY, "Art. 83-86 GG", GG_SOURCE_VERSION,
    ),
    CompiledRule(
        "GG_84_86_REGULATIONS", frozenset({"issue_general_administrative_regulation"}),
        check_general_admin_regulation, GG_AUTHORITY, "Art. 84 Abs. 2, Art. 85 Abs. 2, Art. 86 GG", GG_SOURCE_VERSION,
    ),
    CompiledRule(
        "GG_84_85_SUPERVISION", frozenset({"exercise_federal_supervision", "send_federal_commissioner"}),
        check_federal_supervision, GG_AUTHORITY, "Art. 84 Abs. 3-4, Art. 85 Abs. 4 GG", GG_SOURCE_VERSION,
    ),
    CompiledRule(
        "GG_84_85_INSTRUCTION", frozenset({"issue_individual_instruction"}),
        check_individual_instruction, GG_AUTHORITY, "Art. 84 Abs. 5, Art. 85 Abs. 3 GG", GG_SOURCE_VERSION,
    ),
    CompiledRule(
        "GG_87", frozenset({"create_federal_authority"}), check_create_federal_authority,
        GG_AUTHORITY, "Art. 87 Abs. 1-3 GG", GG_SOURCE_VERSION,
    ),
)

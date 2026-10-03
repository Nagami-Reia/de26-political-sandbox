"""Constitutional map of German federal administrative responsibility."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class AdministrationDomain:
    domain: str
    mode: str
    citation: str
    compilation_status: str
    note: str

    def payload(self) -> dict:
        return asdict(self)


CONSTITUTIONAL_ADMINISTRATION_DOMAINS = {
    "GENERAL_FEDERAL_LAW": AdministrationDomain(
        "GENERAL_FEDERAL_LAW", "LAND_OWN_AFFAIRS", "Art. 83 GG", "COMPILED",
        "Default unless the Basic Law determines or permits otherwise.",
    ),
    "FOREIGN_SERVICE": AdministrationDomain(
        "FOREIGN_SERVICE", "FEDERAL_DIRECT", "Art. 87 Abs. 1 GG", "COMPILED", "Own federal substructure.",
    ),
    "FEDERAL_FINANCE": AdministrationDomain(
        "FEDERAL_FINANCE", "FEDERAL_DIRECT", "Art. 87 Abs. 1 GG", "COMPILED", "Own federal substructure.",
    ),
    "FEDERAL_WATERWAYS_SHIPPING": AdministrationDomain(
        "FEDERAL_WATERWAYS_SHIPPING", "FEDERAL_DIRECT", "Art. 87 Abs. 1, Art. 89 GG", "ROUTE_ONLY",
        "Federal administration; detailed transfer-on-request rules remain uncompiled.",
    ),
    "DEFENCE_ADMINISTRATION": AdministrationDomain(
        "DEFENCE_ADMINISTRATION", "FEDERAL_DIRECT", "Art. 87b GG", "ROUTE_ONLY",
        "Own federal substructure; third-party intervention and transfer rules need statutory data.",
    ),
    "AIR_TRANSPORT_ADMINISTRATION": AdministrationDomain(
        "AIR_TRANSPORT_ADMINISTRATION", "FEDERAL_DIRECT", "Art. 87d GG", "ROUTE_ONLY",
        "Land commissioned administration may be created by Bundesrat-consent law.",
    ),
    "FEDERAL_RAILWAY_ADMINISTRATION": AdministrationDomain(
        "FEDERAL_RAILWAY_ADMINISTRATION", "FEDERAL_DIRECT", "Art. 87e GG", "ROUTE_ONLY",
        "Some tasks may be transferred to Laender by federal law.",
    ),
    "POST_TELECOM_SOVEREIGN_TASKS": AdministrationDomain(
        "POST_TELECOM_SOVEREIGN_TASKS", "FEDERAL_DIRECT", "Art. 87f GG", "ROUTE_ONLY",
        "Sovereign tasks are federal; services are private-sector activities.",
    ),
    "FEDERAL_AUTOBAHNS": AdministrationDomain(
        "FEDERAL_AUTOBAHNS", "FEDERAL_DIRECT", "Art. 90 Abs. 2 GG", "ROUTE_ONLY",
        "The federation may use its wholly owned private-law company.",
    ),
    "OTHER_FEDERAL_TRUNK_ROADS": AdministrationDomain(
        "OTHER_FEDERAL_TRUNK_ROADS", "FEDERAL_COMMISSION", "Art. 90 Abs. 3 GG", "ROUTE_ONLY",
        "Laender or competent self-governing bodies administer on federal commission.",
    ),
    "CROSS_LAND_SOCIAL_INSURANCE": AdministrationDomain(
        "CROSS_LAND_SOCIAL_INSURANCE", "FEDERAL_PUBLIC_CORPORATION", "Art. 87 Abs. 2 GG", "ROUTE_ONLY",
        "Territorial exception for carriers spanning no more than three Laender remains contextual.",
    ),
    "CENTRAL_BANK": AdministrationDomain(
        "CENTRAL_BANK", "INDEPENDENT_FEDERAL_INSTITUTION", "Art. 88 GG", "ROUTE_ONLY",
        "Powers may be transferred to the independent ECB under EU law.",
    ),
}


def administration_domain(domain: str) -> AdministrationDomain:
    return CONSTITUTIONAL_ADMINISTRATION_DOMAINS.get(
        domain,
        CONSTITUTIONAL_ADMINISTRATION_DOMAINS["GENERAL_FEDERAL_LAW"],
    )

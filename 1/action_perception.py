"""Translate a role repertoire into an actor-specific consideration set."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .action_repertoire import RepertoireAssessment
from .institutional_logic import InstitutionalLogic, clamp01
from .persona_v2 import ActionOption
from .political_agency import AgencyHorizon


@dataclass(frozen=True)
class PerceivedAction:
    action: str
    objective_status: str
    role_status: str
    perceived_status: str
    perceived_feasibility: float
    information_confidence: float
    alternative_legibility_factor: float
    carrier_access: float
    deviation_survivability: float
    reasons: tuple[str, ...]

    def payload(self) -> dict:
        return asdict(self)


class ActionPerceptionFilter:
    def __init__(self, serious_consideration_threshold: float = 0.250):
        self.threshold = clamp01(serious_consideration_threshold)

    def apply(
        self,
        actions: Sequence[ActionOption],
        repertoire: Mapping[str, RepertoireAssessment],
        logic: InstitutionalLogic,
        agency: AgencyHorizon,
        resources: Mapping[str, float],
        information_confidence: float = 1.000,
    ) -> dict[str, PerceivedAction]:
        result: dict[str, PerceivedAction] = {}
        for action in actions:
            role = repertoire[action.key]
            deviation = clamp01(action.institutional_deviation)
            info = min(clamp01(information_confidence), clamp01(action.information_confidence))
            carrier_rows = [
                min(1.0, float(resources.get(key, 0.0)) / need) if need > 0.0 else 1.0
                for key, need in action.organizational_carrier_requirements.items()
            ]
            action_carrier = sum(carrier_rows) / len(carrier_rows) if carrier_rows else 1.0
            carrier_access = min(action_carrier, agency.access_to_organizational_carrier)
            alternative_factor = 1.0 - deviation * (1.0 - logic.alternative_legibility)
            deviation_survivability = 1.0 - (
                deviation
                * logic.necessity_claim_strength
                * logic.deviation_career_cost
                * (1.0 - 0.5 * agency.confidence_in_deviation)
            )
            agency_factor = 1.0 - deviation * (
                1.0
                - (
                    agency.perceived_alternatives
                    + agency.collective_change_expectation
                )
                / 2.0
            )
            perceived = (
                action.objective_feasibility
                * role.resource_coverage
                * info
                * alternative_factor
                * carrier_access
                * deviation_survivability
                * agency_factor
            )
            perceived = clamp01(perceived) if role.role_status == "AVAILABLE" else 0.0
            reasons = list(role.reasons)
            if alternative_factor < 0.650:
                reasons.append("low_alternative_legibility")
            if carrier_access < 0.650:
                reasons.append("low_organizational_carrier")
            if deviation_survivability < 0.650:
                reasons.append("high_deviation_cost")
            if agency.collective_change_expectation < 0.350 and deviation > 0.0:
                reasons.append("low_collective_change_expectation")
            status = (
                "UNAVAILABLE"
                if role.role_status != "AVAILABLE"
                else "CONSIDERED"
                if perceived >= self.threshold
                else "NOT_SERIOUSLY_CONSIDERED"
            )
            if status == "NOT_SERIOUSLY_CONSIDERED":
                reasons.append("combined_perceived_feasibility_below_threshold")
            result[action.key] = PerceivedAction(
                action=action.key,
                objective_status=role.objective_status,
                role_status=role.role_status,
                perceived_status=status,
                perceived_feasibility=round(perceived, 3),
                information_confidence=round(info, 3),
                alternative_legibility_factor=round(alternative_factor, 3),
                carrier_access=round(carrier_access, 3),
                deviation_survivability=round(deviation_survivability, 3),
                reasons=tuple(dict.fromkeys(reasons)),
            )
        return result

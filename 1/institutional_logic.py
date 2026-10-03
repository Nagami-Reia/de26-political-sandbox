"""Institutional rationality shared by an environment, not an actor trait.

The logic shapes perceived feasibility, deviation cost and expected responses.  It
must never select an action or be added to utility as an arbitrary bonus.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Mapping


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def q3(value: float) -> float:
    return round(clamp01(value), 3)


@dataclass(frozen=True)
class InstitutionalLogic:
    logic_id: str
    governability_priority: float = 0.000
    electoral_survival_priority: float = 0.000
    fiscal_efficiency_priority: float = 0.000
    organizational_unity_priority: float = 0.000
    necessity_claim_strength: float = 0.000
    alternative_legibility: float = 1.000
    metric_dominance: float = 0.000
    deviation_career_cost: float = 0.000
    legitimacy: float = 0.500
    control_concentration: float = 0.500
    epistemic_status: str = "MODEL_ASSUMPTION"

    def __post_init__(self) -> None:
        for key, value in asdict(self).items():
            if key in {"logic_id", "epistemic_status"}:
                continue
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{key} must be in 0.000..1.000")

    @classmethod
    def neutral(cls, logic_id: str = "neutral_shadow_logic") -> "InstitutionalLogic":
        """A compatibility default that does not narrow an action repertoire."""
        return cls(logic_id=logic_id)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "InstitutionalLogic":
        return cls(**raw)

    def evolve(
        self,
        *,
        legitimacy_delta: float = 0.0,
        control_concentration_delta: float = 0.0,
        logic_reinforcement: float = 0.0,
        alternative_legibility_delta: float = 0.0,
    ) -> "InstitutionalLogic":
        """Apply slow system feedback; fast political variables live elsewhere."""
        reinforcement = float(logic_reinforcement)
        return replace(
            self,
            legitimacy=q3(self.legitimacy + legitimacy_delta),
            control_concentration=q3(self.control_concentration + control_concentration_delta),
            necessity_claim_strength=q3(self.necessity_claim_strength + 0.100 * reinforcement),
            metric_dominance=q3(self.metric_dominance + 0.050 * reinforcement),
            alternative_legibility=q3(
                self.alternative_legibility
                + alternative_legibility_delta
                - 0.075 * max(0.0, reinforcement)
            ),
        )

    def payload(self) -> dict:
        return {key: round(value, 3) if isinstance(value, float) else value for key, value in asdict(self).items()}


"""Second feedback channel: reproduction, erosion or transformation of a system."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from statistics import fmean
from typing import Mapping

from .institutional_logic import InstitutionalLogic, clamp01
from .persona_v2 import ActionOption
from .rationality_evaluation import RationalityEvaluation


class ReproductionType(str, Enum):
    REINFORCEMENT = "REINFORCEMENT"
    ADAPTIVE_REPRODUCTION = "ADAPTIVE_REPRODUCTION"
    EROSION = "EROSION"
    TRANSFORMATION = "TRANSFORMATION"
    MIXED = "MIXED"


@dataclass(frozen=True)
class SystemFeedback:
    operational_success: float
    legitimacy_delta: float
    agency_delta: float
    control_concentration_delta: float
    autonomy_distribution_delta: Mapping[str, float]
    logic_reinforcement: float
    alternative_legibility_delta: float
    reproduction_type: str
    diagnostics: Mapping[str, float]

    def payload(self) -> dict:
        return asdict(self)


class SystemFeedbackAssessor:
    """Generic rule model; scenario files supply action features, not outcomes."""

    def assess(
        self,
        action: ActionOption,
        evaluation: RationalityEvaluation,
        logic: InstitutionalLogic,
        operational_success: float,
    ) -> SystemFeedback:
        success = clamp01(operational_success)
        autonomy_mean = fmean(action.autonomy_impacts.values()) if action.autonomy_impacts else 0.0
        alignment = clamp01(action.necessity_frame_alignment)
        deviation = clamp01(action.institutional_deviation)
        substantive = evaluation.substantive_score

        reinforcement = success * alignment - success * deviation * (0.5 + 0.5 * substantive)
        agency_delta = 0.120 * success * deviation + 0.080 * autonomy_mean - 0.080 * success * alignment
        control_delta = -0.100 * autonomy_mean + 0.060 * success * alignment * logic.metric_dominance
        legitimacy_delta = 0.080 * (success - 0.5) + 0.080 * (substantive - 0.5)
        legibility_delta = 0.100 * success * deviation - 0.075 * success * alignment

        if deviation >= 0.600 and success >= 0.650 and agency_delta > 0.0:
            kind = ReproductionType.TRANSFORMATION
        elif reinforcement >= 0.250 and evaluation.rationality_conflict >= 0.250:
            kind = ReproductionType.ADAPTIVE_REPRODUCTION
        elif reinforcement >= 0.200:
            kind = ReproductionType.REINFORCEMENT
        elif reinforcement <= -0.200:
            kind = ReproductionType.EROSION
        else:
            kind = ReproductionType.MIXED

        return SystemFeedback(
            operational_success=round(success, 3),
            legitimacy_delta=round(legitimacy_delta, 3),
            agency_delta=round(agency_delta, 3),
            control_concentration_delta=round(control_delta, 3),
            autonomy_distribution_delta={key: round(float(value), 3) for key, value in action.autonomy_impacts.items()},
            logic_reinforcement=round(reinforcement, 3),
            alternative_legibility_delta=round(legibility_delta, 3),
            reproduction_type=kind.value,
            diagnostics={
                "necessity_frame_alignment": round(alignment, 3),
                "institutional_deviation": round(deviation, 3),
                "autonomy_mean": round(autonomy_mean, 3),
            },
        )


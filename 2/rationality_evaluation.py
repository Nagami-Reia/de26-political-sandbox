"""Keep instrumental and substantive rationality visible until final choice."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Mapping

from .institutional_logic import clamp01
from .persona_v2 import ActionOption, ActionScore


@dataclass(frozen=True)
class ActorRationalityProfile:
    instrumental_weight: float = 0.250
    substantive_weight: float = 0.250
    persona_weight: float = 0.500
    strategic_weight: float = 0.000
    instrumental_metric_weights: Mapping[str, float] = field(default_factory=dict)
    substantive_metric_weights: Mapping[str, float] = field(default_factory=dict)

    def normalized_weights(self) -> tuple[float, float, float, float]:
        raw = (
            max(0.0, self.instrumental_weight),
            max(0.0, self.substantive_weight),
            max(0.0, self.persona_weight),
            max(0.0, self.strategic_weight),
        )
        total = sum(raw)
        return tuple(value / total for value in raw) if total else (0.0, 0.0, 1.0, 0.0)


@dataclass(frozen=True)
class RationalityEvaluation:
    action: str
    instrumental_score: float
    substantive_score: float
    persona_score: float
    strategic_score: float
    perceived_feasibility: float
    choice_score: float
    rationality_conflict: float
    instrumental_rows: Mapping[str, float]
    substantive_rows: Mapping[str, float]

    def payload(self) -> dict:
        return asdict(self)


def _weighted_signed_score(values: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Map signed -1..1 impacts to a 0..1 diagnostic with 0.5 neutral."""
    if not values:
        return 0.500
    numerator = 0.0
    denominator = 0.0
    for key, raw in values.items():
        weight = max(0.0, float(weights.get(key, 1.0)))
        numerator += max(-1.0, min(1.0, float(raw))) * weight
        denominator += weight
    signed = numerator / denominator if denominator else 0.0
    return clamp01(0.5 + 0.5 * signed)


def _normalize_persona_score(score: float) -> float:
    # Persona totals are comparison indices without a natural bound.
    return clamp01(1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, score)) / 18.0)))


class RationalityEvaluator:
    def evaluate(
        self,
        action: ActionOption,
        persona: ActionScore,
        profile: ActorRationalityProfile,
        *,
        perceived_feasibility: float = 1.000,
        strategic_score: float = 0.500,
    ) -> RationalityEvaluation:
        instrumental = _weighted_signed_score(
            action.instrumental_impacts,
            profile.instrumental_metric_weights,
        )
        substantive = _weighted_signed_score(
            action.substantive_impacts,
            profile.substantive_metric_weights,
        )
        persona_score = _normalize_persona_score(persona.total)
        strategic = clamp01(strategic_score)
        iw, sw, pw, tw = profile.normalized_weights()
        raw_choice = iw * instrumental + sw * substantive + pw * persona_score + tw * strategic
        choice = raw_choice * (0.500 + 0.500 * clamp01(perceived_feasibility))
        return RationalityEvaluation(
            action=action.key,
            instrumental_score=round(instrumental, 3),
            substantive_score=round(substantive, 3),
            persona_score=round(persona_score, 3),
            strategic_score=round(strategic, 3),
            perceived_feasibility=round(clamp01(perceived_feasibility), 3),
            choice_score=round(choice, 3),
            rationality_conflict=round(abs(instrumental - substantive), 3),
            instrumental_rows={key: round(float(value), 3) for key, value in action.instrumental_impacts.items()},
            substantive_rows={key: round(float(value), 3) for key, value in action.substantive_impacts.items()},
        )


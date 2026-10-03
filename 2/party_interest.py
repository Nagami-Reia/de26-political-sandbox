"""Party-level interests for external political actors and Union overlays.

This is deliberately not a collective personality model.  A profile records
programmatic directions, common organisational interests and current role
constraints.  It can either choose for a party collective or remain a visible
overlay on an individual Union persona.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from .institutional_logic import clamp01
from .persona_v2 import ActionOption


def _clamp_signed(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _weighted_signed(values: Mapping[str, float], weights: Mapping[str, float]) -> float:
    rows = [(max(0.0, float(weights[key])), _clamp_signed(value))
            for key, value in values.items() if key in weights]
    denominator = sum(weight for weight, _ in rows)
    if not denominator:
        return 0.500
    signed = sum(weight * value for weight, value in rows) / denominator
    return clamp01(0.500 + 0.500 * signed)


@dataclass(frozen=True)
class PartyRedLine:
    metric: str
    direction: str
    threshold: float
    penalty: float
    source_status: str = "MODEL_ASSUMPTION"

    def breached(self, action: ActionOption) -> bool:
        if self.metric in action.issue_positions:
            value = float(action.issue_positions[self.metric])
        elif self.metric in action.party_interest_impacts:
            value = float(action.party_interest_impacts[self.metric])
        else:
            return False
        if self.direction == "minimum":
            return value < self.threshold
        if self.direction == "maximum":
            return value > self.threshold
        raise ValueError(f"Unknown red-line direction: {self.direction}")


@dataclass(frozen=True)
class PartyState:
    """Mutable-in-principle context, kept separate from the party programme."""

    cohesion: float = 0.700
    electoral_pressure: float = 0.500
    government_responsibility: float = 0.000
    coalition_dependency: float = 0.000
    narrative_control: float = 0.500

    def normalized(self) -> "PartyState":
        return PartyState(**{key: round(clamp01(value), 3) for key, value in asdict(self).items()})


@dataclass(frozen=True)
class PartyInterestProfile:
    party_id: str
    label: str
    stable_interests: Mapping[str, float]
    policy_positions: Mapping[str, float]
    issue_salience: Mapping[str, float]
    strategic_interests: Mapping[str, float]
    red_lines: tuple[PartyRedLine, ...] = ()
    default_state: PartyState = PartyState()
    evidence_confidence: float = 0.500
    source_ids: tuple[str, ...] = ()
    epistemic_note: str = ""


@dataclass(frozen=True)
class PartyActionEvaluation:
    party_id: str
    action: str
    common_interest_score: float
    programmatic_score: float
    strategic_score: float
    feasibility_score: float
    collective_score: float
    red_line_penalty: float
    breached_red_lines: tuple[str, ...]
    evidence_confidence: float
    diagnostics: Mapping[str, object] = field(default_factory=dict)

    def payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PartyDecision:
    party_id: str
    chosen_action: str
    evaluations: Mapping[str, PartyActionEvaluation]
    rule: str = "party common interests + programme + strategic role + feasibility"

    def payload(self) -> dict:
        return {
            "party_id": self.party_id,
            "chosen_action": self.chosen_action,
            "rule": self.rule,
            "evaluations": {key: value.payload() for key, value in self.evaluations.items()},
        }


class PartyInterestEngine:
    """Deterministic party collective scoring with explicit uncertainty labels."""

    def __init__(self, profiles: Mapping[str, PartyInterestProfile]):
        self.profiles = dict(profiles)
        self.states = {
            party_id: profile.default_state.normalized()
            for party_id, profile in profiles.items()
        }

    @classmethod
    def from_json(cls, path: str | Path) -> "PartyInterestEngine":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if raw.get("schema_version") != "party-interest-profiles-1.0":
            raise ValueError("Expected party-interest-profiles-1.0")
        profiles: dict[str, PartyInterestProfile] = {}
        for party_id, row in raw["parties"].items():
            profiles[party_id] = PartyInterestProfile(
                party_id=party_id,
                label=row["label"],
                stable_interests=row.get("stable_interests", {}),
                policy_positions=row.get("policy_positions", {}),
                issue_salience=row.get("issue_salience", {}),
                strategic_interests=row.get("strategic_interests", {}),
                red_lines=tuple(PartyRedLine(**item) for item in row.get("red_lines", ())),
                default_state=PartyState(**row.get("default_state", {})),
                evidence_confidence=float(row.get("evidence_confidence", 0.500)),
                source_ids=tuple(row.get("source_ids", ())),
                epistemic_note=row.get("epistemic_note", ""),
            )
        return cls(profiles)

    def evaluate(
        self,
        party_id: str,
        action: ActionOption,
        *,
        objective_feasibility: float | None = None,
        state: PartyState | None = None,
    ) -> PartyActionEvaluation:
        profile = self.profiles[party_id]
        state = (state or self.states[party_id]).normalized()
        common = _weighted_signed(action.party_interest_impacts, profile.stable_interests)
        strategy = _weighted_signed(action.party_strategy_impacts, profile.strategic_interests)

        matches = []
        for issue, action_position in action.issue_positions.items():
            if issue not in profile.policy_positions:
                continue
            weight = max(0.0, float(profile.issue_salience.get(issue, 0.500)))
            distance = abs(_clamp_signed(action_position) - _clamp_signed(profile.policy_positions[issue]))
            matches.append((weight, clamp01(1.000 - distance / 2.000)))
        programmatic = (
            sum(weight * match for weight, match in matches) / sum(weight for weight, _ in matches)
            if matches and sum(weight for weight, _ in matches) else 0.500
        )

        feasibility = clamp01(
            action.objective_feasibility if objective_feasibility is None else objective_feasibility
        )
        # Current role changes how much organisational strategy matters without
        # changing the party's programme. Opposition pressure rewards visible
        # differentiation; government responsibility rewards governability.
        role_adjustment = 0.0
        role_adjustment += state.government_responsibility * float(
            action.party_strategy_impacts.get("government_stability", 0.0)
        ) * 0.080
        role_adjustment += (1.0 - state.government_responsibility) * state.electoral_pressure * float(
            action.party_strategy_impacts.get("opposition_differentiation", 0.0)
        ) * 0.080
        role_adjustment += state.coalition_dependency * float(
            action.party_strategy_impacts.get("coalition_reliability", 0.0)
        ) * 0.060

        raw = 0.350 * common + 0.350 * programmatic + 0.200 * strategy + 0.100 * feasibility
        # Low cohesion compresses a collective's ability to take a sharp line;
        # it does not invent a different preference.
        collective = 0.500 + (raw - 0.500) * (0.600 + 0.400 * state.cohesion)
        collective += role_adjustment
        breached = tuple(rule.metric for rule in profile.red_lines if rule.breached(action))
        penalty = sum(rule.penalty for rule in profile.red_lines if rule.breached(action))
        collective = clamp01(collective - penalty)
        return PartyActionEvaluation(
            party_id=party_id,
            action=action.key,
            common_interest_score=round(common, 3),
            programmatic_score=round(programmatic, 3),
            strategic_score=round(strategy, 3),
            feasibility_score=round(feasibility, 3),
            collective_score=round(collective, 3),
            red_line_penalty=round(penalty, 3),
            breached_red_lines=breached,
            evidence_confidence=round(clamp01(profile.evidence_confidence), 3),
            diagnostics={
                "state": asdict(state),
                "matched_issues": tuple(issue for issue in action.issue_positions if issue in profile.policy_positions),
                "missing_interest_impacts": tuple(
                    key for key in profile.stable_interests if key not in action.party_interest_impacts
                ),
                "source_ids": profile.source_ids,
            },
        )

    def decide(
        self,
        party_id: str,
        actions: Sequence[ActionOption],
        *,
        objective_feasibility: Mapping[str, float] | None = None,
        state: PartyState | None = None,
    ) -> PartyDecision:
        if not actions:
            raise ValueError("Party decision requires at least one action")
        feasibility = objective_feasibility or {}
        rows = {
            action.key: self.evaluate(
                party_id,
                action,
                objective_feasibility=feasibility.get(action.key),
                state=state,
            )
            for action in actions
        }
        order = {action.key: index for index, action in enumerate(actions)}
        chosen = max(rows, key=lambda key: (rows[key].collective_score, -order[key]))
        return PartyDecision(party_id, chosen, rows)

    @staticmethod
    def overlay(
        individual_scores: Mapping[str, float],
        party_evaluations: Mapping[str, PartyActionEvaluation],
        weight: float,
    ) -> dict[str, float]:
        """Blend without hiding either input; weight 0 exactly preserves persona."""
        w = clamp01(weight)
        return {
            key: round((1.0 - w) * score + w * party_evaluations[key].collective_score, 3)
            for key, score in individual_scores.items()
        }


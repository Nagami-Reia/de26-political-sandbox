"""Historical causality, mechanisms, risk decomposition and event generation.

This layer explains why an event enters the political world.  It never chooses an
actor action.  Long structures alter the risk terrain, medium/short developments
accumulate pressure, triggers add an immediate shock, and mechanisms transform
their interaction.  A generated event can then enter ``decision_space.py``.
"""
from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field, replace
from typing import Mapping, Protocol, Sequence

from .decision_space import DecisionEvent, StrategyEffectModel
from .persona_v2 import WorldEvent
from .political_state import StateVariable
from .political_state_system import quantize3


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _bounded_add(current: float, delta: float) -> float:
    return clamp01(current + delta)


@dataclass(frozen=True)
class LongTermFactor:
    key: str
    intensity: float
    duration_turns: int
    affected_systems: tuple[str, ...]
    affected_risk_domains: tuple[str, ...]
    system_deltas_per_turn: Mapping[str, float] = field(default_factory=dict)
    source_status: str = "MODEL_ASSUMPTION"


@dataclass(frozen=True)
class MediumTermChange:
    key: str
    intensity: float
    duration_turns: int
    affected_systems: tuple[str, ...]
    affected_risk_domains: tuple[str, ...]
    system_deltas_per_turn: Mapping[str, float] = field(default_factory=dict)
    source_status: str = "MODEL_ASSUMPTION"


@dataclass(frozen=True)
class ShortTermPressure:
    key: str
    intensity: float
    duration_turns: int
    affected_systems: tuple[str, ...]
    affected_risk_domains: tuple[str, ...]
    system_deltas_per_turn: Mapping[str, float] = field(default_factory=dict)
    source_status: str = "MODEL_ASSUMPTION"


@dataclass(frozen=True)
class TriggerEvent:
    key: str
    shock: float
    affected_risk_domains: tuple[str, ...]
    tags: tuple[str, ...]
    ambiguity: float = 0.500
    source_actor: str | None = None
    target_actor: str | None = None
    source_status: str = "MODEL_CONTINGENCY"


@dataclass
class ActiveFactor:
    category: str
    factor: LongTermFactor | MediumTermChange | ShortTermPressure
    age_turns: int = 0

    def effective_intensity(self) -> float:
        duration = max(1, int(self.factor.duration_turns))
        progress = min(1.0, self.age_turns / duration)
        if self.category == "long_term":
            persistence = 1.0 if progress < .900 else max(0.0, (1.0 - progress) / .100)
        elif self.category == "medium_term":
            persistence = math.sqrt(max(0.0, 1.0 - progress))
        else:
            persistence = max(0.0, 1.0 - progress)
        return clamp01(self.factor.intensity) * persistence

    def active(self) -> bool:
        return self.age_turns < max(1, int(self.factor.duration_turns))


@dataclass
class HistoricalWorldState:
    systems: dict[str, float]
    base_risk: dict[str, float]
    long_term: list[ActiveFactor] = field(default_factory=list)
    medium_term: list[ActiveFactor] = field(default_factory=list)
    short_term: list[ActiveFactor] = field(default_factory=list)
    turn: int = 0
    history: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.systems = {key: clamp01(value) for key, value in self.systems.items()}
        self.base_risk = {key: clamp01(value) for key, value in self.base_risk.items()}

    def add_long_term(self, factor: LongTermFactor) -> None:
        self.long_term.append(ActiveFactor("long_term", factor))

    def add_medium_term(self, factor: MediumTermChange) -> None:
        self.medium_term.append(ActiveFactor("medium_term", factor))

    def add_short_term(self, factor: ShortTermPressure) -> None:
        self.short_term.append(ActiveFactor("short_term", factor))

    def _all_factors(self) -> tuple[ActiveFactor, ...]:
        return tuple(self.long_term + self.medium_term + self.short_term)

    def advance(self, turns: int = 1) -> dict:
        if turns < 0:
            raise ValueError("turns cannot be negative")
        before = dict(self.systems)
        applied: list[dict] = []
        for _ in range(turns):
            self.turn += 1
            for active in self._all_factors():
                intensity = active.effective_intensity()
                for key, raw_delta in active.factor.system_deltas_per_turn.items():
                    delta = float(raw_delta) * intensity
                    self.systems[key] = _bounded_add(self.systems.get(key, .500), delta)
                    applied.append({
                        "turn": self.turn,
                        "factor": active.factor.key,
                        "category": active.category,
                        "system": key,
                        "delta": delta,
                    })
                active.age_turns += 1
            self.long_term = [row for row in self.long_term if row.active()]
            self.medium_term = [row for row in self.medium_term if row.active()]
            self.short_term = [row for row in self.short_term if row.active()]
        row = quantize3({
            "kind": "historical_time_advance",
            "turns": turns,
            "turn_after": self.turn,
            "systems_before": before,
            "systems_after": self.systems,
            "factor_effects": applied,
        })
        self.history.append(row)
        return row

    def apply_system_deltas(self, deltas: Mapping[str, float], source: str) -> dict:
        before = dict(self.systems)
        for key, delta in deltas.items():
            self.systems[key] = _bounded_add(self.systems.get(key, .500), float(delta))
        row = quantize3({
            "kind": "historical_system_update",
            "source": source,
            "before": before,
            "after": self.systems,
        })
        self.history.append(row)
        return row

    def payload(self) -> dict:
        def factors(rows):
            return [
                {
                    "category": row.category,
                    "age_turns": row.age_turns,
                    "effective_intensity": row.effective_intensity(),
                    "factor": asdict(row.factor),
                }
                for row in rows
            ]
        return quantize3({
            "schema_version": "historical-world-state-1.0",
            "turn": self.turn,
            "systems": self.systems,
            "base_risk": self.base_risk,
            "long_term": factors(self.long_term),
            "medium_term": factors(self.medium_term),
            "short_term": factors(self.short_term),
            "history": self.history,
        })

    def as_political_variables(self) -> dict[str, StateVariable]:
        """Bridge normalized historical systems into the 0..100 FoW world."""
        uncertainty = clamp01(self.systems.get("information_uncertainty", 0.0))
        return {
            key: StateVariable(
                key,
                round(value * 100.0, 3),
                scale=10.0,
                uncertainty=uncertainty,
                evidence="HISTORICAL_WORLD_STATE",
            )
            for key, value in self.systems.items()
        }


@dataclass(frozen=True)
class MechanismEffect:
    mechanism: str
    activation: float
    risk_deltas: Mapping[str, float]
    system_deltas: Mapping[str, float]
    tags: tuple[str, ...]
    explanation: str

    def payload(self) -> dict:
        return quantize3(asdict(self))


class HistoricalMechanism(Protocol):
    key: str

    def evaluate(self, state: HistoricalWorldState) -> MechanismEffect:
        ...


class SecurityDilemmaMechanism:
    key = "security_dilemma"

    def evaluate(self, state: HistoricalWorldState) -> MechanismEffect:
        buildup = state.systems.get("military_buildup", 0.0)
        threat = state.systems.get("threat_perception", 0.0)
        activation = math.sqrt(clamp01(buildup) * clamp01(threat))
        return MechanismEffect(
            self.key,
            activation,
            {"security_crisis": .260 * activation},
            {
                "mutual_trust": -.080 * activation,
                "threat_perception": .050 * activation,
            },
            ("security_dilemma", "recursive_threat"),
            "defensive preparation is interpreted as offensive intent",
        )


class CommitmentTrapMechanism:
    key = "commitment_trap"

    def evaluate(self, state: HistoricalWorldState) -> MechanismEffect:
        commitment = state.systems.get("alliance_commitment", 0.0)
        reputation = state.systems.get("reputation_cost", 0.0)
        activation = clamp01(commitment) * clamp01(reputation)
        return MechanismEffect(
            self.key,
            activation,
            {"security_crisis": .220 * activation, "alliance_crisis": .180 * activation},
            {"exit_cost": .090 * activation},
            ("commitment_trap", "alliance_lock_in"),
            "strong commitments and reputation costs reduce room for de-escalation",
        )


class MiscalculationMechanism:
    key = "miscalculation"

    def evaluate(self, state: HistoricalWorldState) -> MechanismEffect:
        uncertainty = state.systems.get("information_uncertainty", 0.0)
        urgency = state.systems.get("decision_urgency", 0.0)
        activation = clamp01(uncertainty) * clamp01(urgency)
        return MechanismEffect(
            self.key,
            activation,
            {"security_crisis": .210 * activation, "political_crisis": .140 * activation},
            {"decision_quality": -.100 * activation},
            ("miscalculation", "fog_of_war", "time_pressure"),
            "uncertainty and urgency jointly degrade judgement",
        )


class HistoricalMechanismLibrary:
    def __init__(self, mechanisms: Sequence[HistoricalMechanism] | None = None) -> None:
        self.mechanisms = tuple(
            mechanisms
            if mechanisms is not None
            else (
                SecurityDilemmaMechanism(),
                CommitmentTrapMechanism(),
                MiscalculationMechanism(),
            )
        )

    def evaluate(self, state: HistoricalWorldState, *, apply: bool = False) -> tuple[MechanismEffect, ...]:
        rows = tuple(mechanism.evaluate(state) for mechanism in self.mechanisms)
        if apply:
            for row in rows:
                if row.activation > 0.0:
                    state.apply_system_deltas(row.system_deltas, f"mechanism:{row.mechanism}")
        return rows


@dataclass(frozen=True)
class RiskContribution:
    source: str
    category: str
    value: float


@dataclass(frozen=True)
class RiskDecomposition:
    domain: str
    base: float
    long_term: float
    medium_term: float
    short_term: float
    mechanisms: float
    triggers: float
    total: float
    contributions: tuple[RiskContribution, ...]

    def payload(self) -> dict:
        return quantize3(asdict(self))


@dataclass(frozen=True)
class HistoricalRiskModel:
    long_term_coefficient: float = .260
    medium_term_coefficient: float = .300
    short_term_coefficient: float = .360
    trigger_coefficient: float = .420

    def assess(
        self,
        state: HistoricalWorldState,
        mechanism_effects: Sequence[MechanismEffect] = (),
        triggers: Sequence[TriggerEvent] = (),
    ) -> dict[str, RiskDecomposition]:
        domains = set(state.base_risk)
        for active in state._all_factors():
            domains.update(active.factor.affected_risk_domains)
        for effect in mechanism_effects:
            domains.update(effect.risk_deltas)
        for trigger in triggers:
            domains.update(trigger.affected_risk_domains)
        result: dict[str, RiskDecomposition] = {}
        for domain in sorted(domains):
            base = state.base_risk.get(domain, 0.0)
            rows: list[RiskContribution] = []
            category_totals = {"long_term": 0.0, "medium_term": 0.0, "short_term": 0.0}
            coefficients = {
                "long_term": self.long_term_coefficient,
                "medium_term": self.medium_term_coefficient,
                "short_term": self.short_term_coefficient,
            }
            for active in state._all_factors():
                if domain not in active.factor.affected_risk_domains:
                    continue
                value = active.effective_intensity() * coefficients[active.category]
                category_totals[active.category] += value
                rows.append(RiskContribution(active.factor.key, active.category, value))
            mechanism_total = 0.0
            for effect in mechanism_effects:
                value = float(effect.risk_deltas.get(domain, 0.0))
                if value:
                    mechanism_total += value
                    rows.append(RiskContribution(effect.mechanism, "mechanism", value))
            trigger_total = 0.0
            for trigger in triggers:
                if domain in trigger.affected_risk_domains:
                    value = clamp01(trigger.shock) * self.trigger_coefficient
                    trigger_total += value
                    rows.append(RiskContribution(trigger.key, "trigger", value))
            total = clamp01(
                base
                + category_totals["long_term"]
                + category_totals["medium_term"]
                + category_totals["short_term"]
                + mechanism_total
                + trigger_total
            )
            result[domain] = RiskDecomposition(
                domain,
                round(base, 3),
                round(category_totals["long_term"], 3),
                round(category_totals["medium_term"], 3),
                round(category_totals["short_term"], 3),
                round(mechanism_total, 3),
                round(trigger_total, 3),
                round(total, 3),
                tuple(RiskContribution(row.source, row.category, round(row.value, 3)) for row in rows),
            )
        return result


@dataclass(frozen=True)
class HistoricalEventCandidate:
    key: str
    risk_domain: str
    threshold: float
    selection_weight: float
    decision_domain: str
    tags: tuple[str, ...]
    effect_models: Mapping[str, StrategyEffectModel]
    allowed_strategy_keys: tuple[str, ...] = ()
    signal_variables: Mapping[str, float] = field(default_factory=dict)
    required_trigger_tags: tuple[str, ...] = ()
    default_ambiguity: float = .500


@dataclass(frozen=True)
class GeneratedHistoricalEvent:
    candidate: HistoricalEventCandidate
    assessment: Mapping[str, RiskDecomposition]
    selected_trigger: TriggerEvent | None
    mechanism_effects: tuple[MechanismEffect, ...]
    selection_score: float
    stochastic: bool
    turn: int

    def to_decision_event(self) -> DecisionEvent:
        trigger_tags = self.selected_trigger.tags if self.selected_trigger else ()
        mechanism_tags = tuple(
            tag
            for effect in self.mechanism_effects
            if effect.activation >= .100
            for tag in effect.tags
        )
        risk = self.assessment[self.candidate.risk_domain]
        trigger = self.selected_trigger
        return DecisionEvent(
            key=f"{self.candidate.key}_t{self.turn}",
            domain=self.candidate.decision_domain,
            tags=tuple(dict.fromkeys(self.candidate.tags + trigger_tags + mechanism_tags)),
            severity=risk.total,
            ambiguity=trigger.ambiguity if trigger else self.candidate.default_ambiguity,
            effect_models=self.candidate.effect_models,
            source_actor=trigger.source_actor if trigger else None,
            signal_variables=self.candidate.signal_variables,
            allowed_strategy_keys=self.candidate.allowed_strategy_keys,
            target_actor=trigger.target_actor if trigger else None,
        )

    def to_pss_event(self) -> WorldEvent:
        """Represent the same event as an actor-state shock before deliberation."""
        decision = self.to_decision_event()
        return WorldEvent(
            event_id=decision.key,
            event_type=f"historical_{self.candidate.risk_domain}",
            severity=decision.severity,
            tags=decision.tags,
            valence=-1.0,
            surprise=decision.ambiguity,
            workload=.030 + .070 * decision.severity,
            impact_profile={
                "pressure": 1.000,
                "energy": .350,
                "confidence": .250,
                "control": .250,
                "identity_integrity": .050,
            },
        )

    def payload(self) -> dict:
        return quantize3({
            "candidate": self.candidate.key,
            "risk_domain": self.candidate.risk_domain,
            "turn": self.turn,
            "selection_score": self.selection_score,
            "stochastic": self.stochastic,
            "selected_trigger": asdict(self.selected_trigger) if self.selected_trigger else None,
            "risk_assessment": {key: row.payload() for key, row in self.assessment.items()},
            "mechanisms": [row.payload() for row in self.mechanism_effects],
            "decision_event": asdict(self.to_decision_event()),
            "pss_event": asdict(self.to_pss_event()),
        })


@dataclass(frozen=True)
class EventGenerationResult:
    generated_event: GeneratedHistoricalEvent | None
    assessment: Mapping[str, RiskDecomposition]
    eligible_candidates: tuple[Mapping[str, float | str], ...]
    reason: str

    def payload(self) -> dict:
        return quantize3({
            "reason": self.reason,
            "eligible_candidates": list(self.eligible_candidates),
            "assessment": {key: row.payload() for key, row in self.assessment.items()},
            "generated_event": self.generated_event.payload() if self.generated_event else None,
        })


class HistoricalEventGenerator:
    def __init__(
        self,
        candidates: Sequence[HistoricalEventCandidate],
        *,
        risk_model: HistoricalRiskModel | None = None,
        seed: int = 0,
        stochastic: bool = False,
    ) -> None:
        self.candidates = tuple(candidates)
        self.risk_model = risk_model or HistoricalRiskModel()
        self.rng = random.Random(seed)
        self.stochastic = stochastic

    @staticmethod
    def _matching_trigger(
        candidate: HistoricalEventCandidate,
        triggers: Sequence[TriggerEvent],
    ) -> TriggerEvent | None:
        rows = [
            row for row in triggers
            if candidate.risk_domain in row.affected_risk_domains
            and (
                not candidate.required_trigger_tags
                or set(candidate.required_trigger_tags).intersection(row.tags)
            )
        ]
        return max(rows, key=lambda row: (row.shock, row.key), default=None)

    def generate(
        self,
        state: HistoricalWorldState,
        mechanism_effects: Sequence[MechanismEffect] = (),
        triggers: Sequence[TriggerEvent] = (),
    ) -> EventGenerationResult:
        assessment = self.risk_model.assess(state, mechanism_effects, triggers)
        eligible: list[tuple[HistoricalEventCandidate, float, TriggerEvent | None]] = []
        for candidate in self.candidates:
            risk = assessment.get(candidate.risk_domain)
            if risk is None or risk.total < candidate.threshold:
                continue
            trigger = self._matching_trigger(candidate, triggers)
            if candidate.required_trigger_tags and trigger is None:
                continue
            excess = max(.001, risk.total - candidate.threshold + .050)
            score = excess * max(.001, candidate.selection_weight)
            eligible.append((candidate, score, trigger))
        diagnostics = tuple(
            {"candidate": row.key, "score": round(score, 3), "risk": assessment[row.risk_domain].total}
            for row, score, _ in sorted(eligible, key=lambda item: (-item[1], item[0].key))
        )
        if not eligible:
            return EventGenerationResult(None, assessment, diagnostics, "NO_THRESHOLD_CROSSED")
        if self.stochastic:
            total = sum(score for _, score, _ in eligible)
            draw = self.rng.random() * total
            cumulative = 0.0
            selected = eligible[-1]
            for row in eligible:
                cumulative += row[1]
                if draw <= cumulative:
                    selected = row
                    break
        else:
            selected = max(eligible, key=lambda item: (item[1], item[0].key))
        candidate, score, trigger = selected
        event = GeneratedHistoricalEvent(
            candidate,
            assessment,
            trigger,
            tuple(mechanism_effects),
            round(score, 3),
            self.stochastic,
            state.turn,
        )
        return EventGenerationResult(event, assessment, diagnostics, "EVENT_GENERATED")


class HistoricalWorldEngine:
    """Advance history and emit, but never decide, political events."""

    def __init__(
        self,
        state: HistoricalWorldState,
        event_generator: HistoricalEventGenerator,
        mechanisms: HistoricalMechanismLibrary | None = None,
    ) -> None:
        self.state = state
        self.event_generator = event_generator
        self.mechanisms = mechanisms or HistoricalMechanismLibrary()

    def step(
        self,
        triggers: Sequence[TriggerEvent] = (),
        *,
        advance_turns: int = 1,
    ) -> EventGenerationResult:
        self.state.advance(advance_turns)
        effects = self.mechanisms.evaluate(self.state, apply=True)
        result = self.event_generator.generate(self.state, effects, triggers)
        self.state.history.append(quantize3({
            "kind": "historical_event_generation",
            "turn": self.state.turn,
            "triggers": [asdict(row) for row in triggers],
            "mechanisms": [row.payload() for row in effects],
            "result": result.payload(),
        }))
        return result

    def record_outcome(
        self,
        action: str,
        outcome: str,
        system_deltas: Mapping[str, float],
        *,
        long_term: Sequence[LongTermFactor] = (),
        medium_term: Sequence[MediumTermChange] = (),
        short_term: Sequence[ShortTermPressure] = (),
    ) -> dict:
        update = self.state.apply_system_deltas(system_deltas, f"outcome:{action}:{outcome}")
        for row in long_term:
            self.state.add_long_term(row)
        for row in medium_term:
            self.state.add_medium_term(row)
        for row in short_term:
            self.state.add_short_term(row)
        result = quantize3({
            "kind": "historical_outcome_feedback",
            "action": action,
            "outcome": outcome,
            "system_update": update,
            "new_factors": {
                "long_term": [asdict(row) for row in long_term],
                "medium_term": [asdict(row) for row in medium_term],
                "short_term": [asdict(row) for row in short_term],
            },
        })
        self.state.history.append(result)
        return result

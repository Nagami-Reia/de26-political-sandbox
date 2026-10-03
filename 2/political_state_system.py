"""Political State System (PSS): actor pressure, damage, recovery and memory.

Personality parameters are stable. Events become actor-specific impacts first;
only impacts mutate state. All card inputs and PSS states use a 0.000..1.000 scale.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


def bound1(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def q3(value: float) -> float:
    return round(float(value), 3)


def quantize3(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, float):
        return q3(value)
    if isinstance(value, dict):
        return {key: quantize3(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [quantize3(item) for item in value]
    return value


def tag_overlap(left: Sequence[str], right: Sequence[str]) -> float:
    a, b = set(left), set(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


@dataclass
class PoliticalState:
    energy: float = 0.750
    pressure: float = 0.250
    confidence: float = 0.700
    control: float = 0.650
    identity_integrity: float = 0.850

    def normalize(self) -> None:
        for key in ("energy", "pressure", "confidence", "control", "identity_integrity"):
            setattr(self, key, bound1(getattr(self, key)))


@dataclass(frozen=True)
class PSSProfile:
    stress_resistance: float
    recovery_rate: float
    sensitivity_map: Mapping[str, float]
    state_modulation: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.stress_resistance <= 1:
            raise ValueError("stress_resistance must be 0..1")
        if not 0 <= self.recovery_rate <= 1:
            raise ValueError("recovery_rate must be 0..1")
        if any(not 0 <= value <= 1 for value in self.sensitivity_map.values()):
            raise ValueError("sensitivity values must be 0..1")


@dataclass
class MemoryNode:
    event_id: str
    tags: tuple[str, ...]
    severity: float
    valence: float
    decay_per_day: float = 0.01
    unresolved: float = 0.0
    learned_response_tags: tuple[str, ...] = ()

    def normalize(self) -> None:
        self.severity = bound1(self.severity)
        self.valence = max(-1.0, min(1.0, self.valence))
        self.decay_per_day = max(0.0, min(1.0, self.decay_per_day))
        self.unresolved = bound1(self.unresolved)


@dataclass(frozen=True)
class PoliticalEvent:
    event_id: str
    event_type: str
    severity: float
    tags: tuple[str, ...]
    valence: float = -1.0
    surprise: float = 0.5
    workload: float = 0.0
    impact_profile: Mapping[str, float] = field(default_factory=lambda: {
        "pressure": 1.0,
        "energy": 0.35,
        "confidence": 0.45,
        "control": 0.55,
        "identity_integrity": 0.15,
    })
    relationship_deltas: Mapping[str, Mapping[str, float]] = field(default_factory=dict)


@dataclass(frozen=True)
class StateImpact:
    actor: str
    event_id: str
    event_type: str
    tags: tuple[str, ...]
    base_severity: float
    sensitivity: float
    sensitivity_multiplier: float
    resistance_factor: float
    memory_multiplier: float
    effective_damage: float
    state_deltas: Mapping[str, float]
    memory_resonance: tuple[Mapping[str, Any], ...]
    relationship_deltas: Mapping[str, Mapping[str, float]]


@dataclass
class ActorPSS:
    actor: str
    profile: PSSProfile
    state: PoliticalState
    memories: list[MemoryNode] = field(default_factory=list)
    elapsed_days: int = 0


class PoliticalStateSystem:
    def __init__(self) -> None:
        self.actors: dict[str, ActorPSS] = {}
        self.history: list[dict[str, Any]] = []

    def register(
        self,
        actor: str,
        profile: PSSProfile,
        state: PoliticalState | None = None,
        memories: Sequence[MemoryNode] = (),
    ) -> ActorPSS:
        if actor in self.actors:
            raise ValueError(f"Actor already registered: {actor}")
        current = state or PoliticalState()
        current.normalize()
        copied_memories = [MemoryNode(**asdict(memory)) for memory in memories]
        for memory in copied_memories:
            memory.normalize()
        record = ActorPSS(actor, profile, current, copied_memories)
        self.actors[actor] = record
        return record

    def calculate_impact(self, actor: str, event: PoliticalEvent) -> StateImpact:
        record = self.actors[actor]
        profile = record.profile
        sensitivity = max(
            (float(profile.sensitivity_map.get(tag, 0.5)) for tag in event.tags),
            default=0.5,
        )
        sensitivity_multiplier = 0.5 + sensitivity
        resistance_factor = 1.0 - profile.stress_resistance
        resonance_rows: list[Mapping[str, Any]] = []
        resonance_load = 0.0
        for memory in record.memories:
            resonance = tag_overlap(memory.tags, event.tags)
            if resonance <= 0:
                continue
            contribution = (
                resonance
                * memory.severity
                * memory.unresolved
                * (0.45 + 0.55 * max(0.0, -memory.valence))
            )
            resonance_load += contribution
            resonance_rows.append({
                "memory": memory.event_id,
                "tag_overlap": round(resonance, 4),
                "contribution": round(contribution, 4),
            })
        memory_multiplier = min(2.0, 1.0 + resonance_load)
        effective_damage = bound1(
            bound1(event.severity)
            * resistance_factor
            * sensitivity_multiplier
            * memory_multiplier
        )
        valence = max(-1.0, min(1.0, event.valence))
        # Negative events increase pressure and reduce the other four channels.
        direction = -1.0 if valence < 0 else 1.0
        magnitude = abs(valence)
        deltas = {
            "pressure": effective_damage * float(event.impact_profile.get("pressure", 1.0)) * (-direction),
            "energy": direction * effective_damage * float(event.impact_profile.get("energy", 0.35)),
            "confidence": direction * effective_damage * float(event.impact_profile.get("confidence", 0.45)),
            "control": direction * effective_damage * float(event.impact_profile.get("control", 0.55)),
            "identity_integrity": direction * effective_damage * float(event.impact_profile.get("identity_integrity", 0.15)),
        }
        if magnitude < 1.0:
            deltas = {key: value * magnitude for key, value in deltas.items()}
        deltas["energy"] -= bound1(event.workload)
        return StateImpact(
            actor=actor,
            event_id=event.event_id,
            event_type=event.event_type,
            tags=event.tags,
            base_severity=bound1(event.severity),
            sensitivity=sensitivity,
            sensitivity_multiplier=sensitivity_multiplier,
            resistance_factor=resistance_factor,
            memory_multiplier=memory_multiplier,
            effective_damage=effective_damage,
            state_deltas=deltas,
            memory_resonance=tuple(resonance_rows),
            relationship_deltas=event.relationship_deltas,
        )

    def apply_impact(self, impact: StateImpact, create_memory: bool = True) -> dict[str, Any]:
        record = self.actors[impact.actor]
        before = asdict(record.state)
        for channel, delta in impact.state_deltas.items():
            setattr(record.state, channel, getattr(record.state, channel) + delta)
        record.state.normalize()
        if create_memory:
            record.memories.append(MemoryNode(
                event_id=impact.event_id,
                tags=impact.tags,
                severity=bound1(impact.effective_damage),
                valence=-1.0 if impact.state_deltas.get("pressure", 0.0) >= 0 else 1.0,
                decay_per_day=0.002 + 0.006 * record.profile.recovery_rate,
                unresolved=bound1(impact.effective_damage * (0.7 + impact.memory_multiplier * 0.3)),
            ))
        event = {
            "kind": "state_impact",
            "actor": impact.actor,
            "impact": asdict(impact),
            "before": before,
            "after": asdict(record.state),
        }
        public_event = quantize3(event)
        self.history.append(public_event)
        return public_event

    def process_event(self, actor: str, event: PoliticalEvent) -> dict[str, Any]:
        impact = self.calculate_impact(actor, event)
        applied = self.apply_impact(impact)
        return quantize3({"impact": asdict(impact), "application": applied})

    def record_outcome(
        self,
        actor: str,
        action: str,
        success: float,
        tags: Sequence[str] = (),
        workload: float = 0.040,
    ) -> dict[str, Any]:
        """Success can restore confidence; time alone cannot."""
        record = self.actors[actor]
        signed = 2.0 * bound1(success) - 1.0
        before = asdict(record.state)
        record.state.energy -= max(0.0, workload)
        record.state.confidence += 0.120 * signed
        record.state.pressure -= 0.080 * signed
        record.state.identity_integrity += 0.040 * signed
        record.state.normalize()
        record.memories.append(MemoryNode(
            event_id=f"outcome:{action}:{len(self.history)}",
            tags=tuple(tags) + (action,),
            severity=0.350 + 0.450 * abs(signed),
            valence=signed,
            decay_per_day=0.003 + 0.006 * record.profile.recovery_rate,
            unresolved=bound1(max(0.0, -signed) * 0.700),
            learned_response_tags=tuple(tags) if success >= 0.65 else (),
        ))
        result = {"kind": "action_outcome", "actor": actor, "action": action, "before": before, "after": asdict(record.state)}
        public_result = quantize3(result)
        self.history.append(public_result)
        return public_result

    def restore_control(self, actor: str, amount: float, source: str) -> dict[str, Any]:
        """Control only returns through an explicit resource/process restoration."""
        record = self.actors[actor]
        before = record.state.control
        record.state.control = bound1(record.state.control + max(0.0, amount))
        result = {"kind": "control_restoration", "actor": actor, "source": source, "before": before, "after": record.state.control}
        public_result = quantize3(result)
        self.history.append(public_result)
        return public_result

    def reinforce_identity(self, actor: str, alignment: float, source: str) -> dict[str, Any]:
        """Identity moves slowly and only after identity-relevant action/outcome."""
        record = self.actors[actor]
        before = record.state.identity_integrity
        record.state.identity_integrity = bound1(record.state.identity_integrity + max(-0.030, min(0.030, alignment)))
        result = {"kind": "identity_update", "actor": actor, "source": source, "before": before, "after": record.state.identity_integrity}
        public_result = quantize3(result)
        self.history.append(public_result)
        return public_result

    def advance_time(self, actor: str, days: int, workload: float = 0.0) -> dict[str, Any]:
        """Natural recovery: energy and pressure only; memories decay by channel."""
        if days < 0:
            raise ValueError("days cannot be negative")
        record = self.actors[actor]
        before = asdict(record.state)
        recovery = record.profile.recovery_rate
        record.state.energy += days * 0.0055 * recovery - max(0.0, workload)
        record.state.pressure -= days * 0.0040 * recovery
        # Confidence, control and identity do not heal merely because time passes.
        record.state.normalize()
        for memory in record.memories:
            memory.severity *= (1.0 - memory.decay_per_day) ** days
            memory.unresolved *= (1.0 - 0.25 * memory.decay_per_day) ** days
            memory.normalize()
        record.elapsed_days += days
        result = {"kind": "time_advance", "actor": actor, "days": days, "before": before, "after": asdict(record.state)}
        public_result = quantize3(result)
        self.history.append(public_result)
        return public_result

    def effective_decision_parameters(
        self,
        actor: str,
        base_ambition: float,
        base_risk_appetite: float,
        control_preferences: Mapping[str, float],
    ) -> dict[str, Any]:
        """State modulates stable personality without overwriting it."""
        record = self.actors[actor]
        state, mod = record.state, record.profile.state_modulation
        pressure = state.pressure
        low_energy = 1.0 - state.energy
        low_control = 1.0 - state.control
        low_confidence = 1.0 - state.confidence
        def move(value: float, target_key: str, strength_key: str, intensity: float) -> float:
            target = bound1(float(mod.get(target_key, value)))
            strength = bound1(float(mod.get(strength_key, 0.0)))
            return bound1(value + (target - value) * intensity * strength)

        ambition = move(base_ambition, "pressure_ambition_target", "pressure_ambition_strength", pressure)
        ambition = move(ambition, "low_energy_ambition_target", "low_energy_ambition_strength", low_energy)
        ambition = move(ambition, "low_confidence_ambition_target", "low_confidence_ambition_strength", low_confidence)
        risk = move(base_risk_appetite, "pressure_risk_target", "pressure_risk_strength", pressure)
        risk = move(risk, "low_energy_risk_target", "low_energy_risk_strength", low_energy)
        risk = move(risk, "low_confidence_risk_target", "low_confidence_risk_strength", low_confidence)
        control_multiplier = 1.0 + low_control * bound1(float(mod.get("low_control_control_strength", 0.50)))
        effective_control = {key: bound1(value * control_multiplier) for key, value in control_preferences.items()}
        return quantize3({
            "ambition": ambition,
            "risk_appetite": risk,
            "control_preferences": effective_control,
            "state_inputs": asdict(state),
            "control_multiplier": control_multiplier,
        })

    def payload(self) -> dict[str, Any]:
        return quantize3({
            "schema_version": "political-state-system-1.0",
            "scale": "0.000..1.000; serialized diagnostics round to three decimals",
            "actors": {
                actor: {
                    "profile": asdict(record.profile),
                    "state": asdict(record.state),
                    "memories": [asdict(memory) for memory in record.memories],
                    "elapsed_days": record.elapsed_days,
                }
                for actor, record in self.actors.items()
            },
            "history": self.history,
        })

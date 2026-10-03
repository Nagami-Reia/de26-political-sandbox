"""Roguelike personality-card v2: free choice over an environment action menu.

The environment owns available actions, predicted effects and resources.  A card
owns only stable preferences and update rules.  Runtime state and memory are
mutable, so the same character can rationally choose differently in a later turn.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from .political_state_system import (
    MemoryNode as EventMemory,
    PSSProfile,
    PoliticalEvent as WorldEvent,
    PoliticalState as CurrentState,
    PoliticalStateSystem,
    quantize3,
)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def overlap(left: Sequence[str], right: Sequence[str]) -> float:
    a, b = set(left), set(right)
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


@dataclass(frozen=True)
class RankedValue:
    key: str
    rank: int
    weight: float


@dataclass(frozen=True)
class CharacterDNA:
    archetype: str
    core_drive: str
    core_drive_tags: tuple[str, ...]
    value_hierarchy: tuple[RankedValue, ...]
    ambition: float
    risk_appetite: float
    risk_context_appetite: Mapping[str, float]
    control_preferences: Mapping[str, float]
    adaptability: float
    conflict_strategies: Mapping[str, float]
    relationship_orientation: Mapping[str, float] = field(default_factory=dict)


@dataclass
class RelationshipMemory:
    counterpart: str
    trust: float = 0.50
    operational_reliability: float = 0.50
    dependency: dict[str, float] = field(default_factory=lambda: {
        "organizational": 0.50,
        "informational": 0.50,
        "electoral": 0.50,
        "personal_trust": 0.50,
    })
    alternative_capacity: dict[str, float] = field(default_factory=lambda: {
        "organizational": 0.50,
        "informational": 0.50,
        "electoral": 0.50,
    })
    leverage: float = 0.50
    loyalty_injury: float = 0.0
    betrayal_count: int = 0
    failed_response_count: int = 0
    consecutive_action_count: int = 0
    pattern_exposures: dict[str, int] = field(default_factory=dict)
    mistake_attribution: float = 0.50
    structural_unreliability: float = 0.0
    last_action: str | None = None
    last_event: str | None = None

    def normalize(self) -> None:
        for key in (
            "trust", "operational_reliability", "leverage", "loyalty_injury",
            "mistake_attribution", "structural_unreliability",
        ):
            setattr(self, key, clamp(getattr(self, key)))
        self.dependency = {key: clamp(value) for key, value in self.dependency.items()}
        self.alternative_capacity = {
            key: clamp(value) for key, value in self.alternative_capacity.items()
        }
        self.betrayal_count = max(0, int(self.betrayal_count))
        self.failed_response_count = max(0, int(self.failed_response_count))
        self.consecutive_action_count = max(0, int(self.consecutive_action_count))
        self.pattern_exposures = {
            str(key): max(0, int(value)) for key, value in self.pattern_exposures.items()
        }

    def dependency_index(self) -> float:
        weights = {
            "organizational": 0.35,
            "informational": 0.25,
            "electoral": 0.20,
            "personal_trust": 0.20,
        }
        return sum(weights[key] * self.dependency.get(key, 0.50) for key in weights)

    def alternative_index(self) -> float:
        weights = {"organizational": 0.40, "informational": 0.30, "electoral": 0.30}
        return sum(weights[key] * self.alternative_capacity.get(key, 0.50) for key in weights)


@dataclass
class PersonaRuntime:
    state: CurrentState = field(default_factory=CurrentState)
    memories: list[EventMemory] = field(default_factory=list)
    relationships: dict[str, RelationshipMemory] = field(default_factory=dict)
    turn: int = 0


@dataclass(frozen=True)
class PersonaCard:
    actor: str
    name: str
    dna: CharacterDNA
    pss_profile: PSSProfile
    initial_resources: Mapping[str, float]
    evidence_confidence: float
    runtime: PersonaRuntime
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionOption:
    """One action supplied by the world, never by the personality card."""

    key: str
    goal_impacts: Mapping[str, float] = field(default_factory=dict)
    value_impacts: Mapping[str, float] = field(default_factory=dict)
    required_resources: Mapping[str, float] = field(default_factory=dict)
    resource_costs: Mapping[str, float] = field(default_factory=dict)
    upside: float = 0.0
    downside: float = 0.0
    uncertainty: float = 0.0
    irreversibility: float = 0.0
    effort: float = 0.0
    visibility: float = 0.0
    information_confidence: float = 1.0
    control_domains: tuple[str, ...] = ()
    restores_control: float = 0.0
    conflict_strategy: str = "institutionalize"
    identity_tags: tuple[str, ...] = ()
    event_tags: tuple[str, ...] = ()
    risk_tags: tuple[str, ...] = ()
    target_actor: str | None = None
    legal: bool = True
    # v3 environment-owned fields.  Neutral defaults preserve every v2 result.
    objective_feasibility: float = 1.0
    instrumental_impacts: Mapping[str, float] = field(default_factory=dict)
    substantive_impacts: Mapping[str, float] = field(default_factory=dict)
    institutional_deviation: float = 0.0
    necessity_frame_alignment: float = 0.0
    autonomy_impacts: Mapping[str, float] = field(default_factory=dict)
    organizational_carrier_requirements: Mapping[str, float] = field(default_factory=dict)
    required_offices: tuple[str, ...] = ()
    required_institutional_permissions: tuple[str, ...] = ()
    # How the action changes a targeted relationship. Neutral preserves v2.
    relationship_posture: str = "neutral"
    # Party-interest layer.  The environment supplies these descriptions; the
    # party profile only supplies weights and preferred policy directions.
    # Signed impacts use -1..1.  Issue positions use -1..1 on named axes.
    party_interest_impacts: Mapping[str, float] = field(default_factory=dict)
    party_strategy_impacts: Mapping[str, float] = field(default_factory=dict)
    issue_positions: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionScore:
    action: str
    total: float
    goal_alignment: float
    resource_feasibility: float
    risk_calculation: float
    current_state_modifier: float
    memory_modifier: float
    identity_consistency: float
    hard_rejections: tuple[str, ...]
    diagnostics: Mapping[str, Any]
    relationship_history_modifier: float = 0.0


@dataclass(frozen=True)
class FreeDecision:
    actor: str
    chosen_action: str
    scores: Mapping[str, ActionScore]
    turn: int
    rule: str = (
        "goal alignment + resource feasibility + risk calculation + current state "
        "+ memory + identity consistency"
    )


@dataclass(frozen=True)
class ActionOutcome:
    action: str
    success: float
    surprise: float = 0.0
    tags: tuple[str, ...] = ()
    target_actor: str | None = None
    relationship_delta: Mapping[str, Any] = field(default_factory=dict)
    workload: float = 0.040
    control_restoration: float = 0.0
    identity_alignment: float = 0.0


class FreeAgentDecisionEngine:
    """Deterministic character choice; uncertainty belongs to beliefs/outcomes."""

    def __init__(self, cards: Mapping[str, PersonaCard]):
        self.cards = dict(cards)
        self.runtime = {actor: _copy_runtime(card.runtime) for actor, card in cards.items()}
        self.pss = PoliticalStateSystem()
        for actor, card in cards.items():
            runtime = self.runtime[actor]
            record = self.pss.register(actor, card.pss_profile, runtime.state, runtime.memories)
            runtime.state = record.state
            runtime.memories = record.memories

    @classmethod
    def from_json(cls, path: str | Path) -> "FreeAgentDecisionEngine":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema_version") != "persona-cards-pss-1.0":
            raise ValueError("Expected persona-cards-pss-1.0")
        cards = {actor: _parse_card(actor, raw) for actor, raw in payload["actors"].items()}
        return cls(cards)

    @classmethod
    def from_json_files(cls, *paths: str | Path) -> "FreeAgentDecisionEngine":
        """Load a base deck followed by explicit research-wave overlays.

        Later decks replace actors with the same key. This makes revisions
        auditable without silently rewriting the frozen base research deck.
        """
        if not paths:
            raise ValueError("At least one persona-card file is required")
        merged: dict[str, PersonaCard] = {}
        for path in paths:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if payload.get("schema_version") != "persona-cards-pss-1.0":
                raise ValueError(f"Expected persona-cards-pss-1.0 in {path}")
            merged.update(
                {actor: _parse_card(actor, raw) for actor, raw in payload["actors"].items()}
            )
        return cls(merged)

    def decide(
        self,
        actor: str,
        actions: Sequence[ActionOption],
        perceived_resources: Mapping[str, float],
        current_goals: Mapping[str, float] | None = None,
        scene_tags: Sequence[str] = (),
        soft_resource_constraints: bool = False,
    ) -> FreeDecision:
        if actor not in self.cards:
            raise KeyError(f"No v2 card for {actor}")
        if not actions:
            raise ValueError("The environment supplied no actions")
        goals = dict(current_goals or {})
        scores = {
            action.key: self.score(
                actor,
                action,
                perceived_resources,
                goals,
                scene_tags,
                soft_resource_constraints=soft_resource_constraints,
            )
            for action in actions
        }
        legal = [key for key, row in scores.items() if not row.hard_rejections]
        if not legal:
            raise RuntimeError(f"No legal/feasible action for {actor}")
        # Stable tie-break: the environment's menu order, not an invented personality draw.
        menu_order = {action.key: i for i, action in enumerate(actions)}
        chosen = max(legal, key=lambda key: (scores[key].total, -menu_order[key]))
        return FreeDecision(actor, chosen, scores, self.runtime[actor].turn)

    def score(
        self,
        actor: str,
        action: ActionOption,
        resources: Mapping[str, float],
        goals: Mapping[str, float],
        scene_tags: Sequence[str] = (),
        soft_resource_constraints: bool = False,
    ) -> ActionScore:
        card, runtime = self.cards[actor], self.runtime[actor]
        dna, state = card.dna, runtime.state
        effective = self.pss.effective_decision_parameters(
            actor,
            dna.ambition,
            dna.risk_appetite,
            dna.control_preferences,
        )
        effective_ambition = effective["ambition"]
        effective_control_preferences = effective["control_preferences"]
        energy = state.energy
        pressure = state.pressure
        confidence = state.confidence
        control = state.control
        identity_integrity = state.identity_integrity
        resistance = card.pss_profile.stress_resistance
        rejected: list[str] = []
        if not action.legal:
            rejected.append("environment_illegal")

        ratios: list[float] = []
        for key, need in action.required_resources.items():
            have = clamp(float(resources.get(key, 0.0)))
            if have + 1e-9 < need and not soft_resource_constraints:
                rejected.append(f"resource:{key}<{need:.2f}")
            ratios.append(1.0 if need <= 0 else min(1.0, have / need))
        mean_ratio = sum(ratios) / len(ratios) if ratios else 1.0
        cost_load = sum(max(0.0, cost - float(resources.get(key, 0.0))) for key, cost in action.resource_costs.items())
        relationship_factor = 1.0
        relationship_row: dict[str, float] | None = None
        relationship_history_modifier = 0.0
        if action.target_actor:
            rel = runtime.relationships.get(action.target_actor, RelationshipMemory(action.target_actor))
            dependency_index = rel.dependency_index()
            alternative_index = rel.alternative_index()
            exit_lock = dependency_index * (1.0 - alternative_index)
            if action.conflict_strategy in {"negotiate", "institutionalize"}:
                relationship_factor = 0.45 + 0.35 * rel.trust + 0.20 * rel.operational_reliability
            elif action.conflict_strategy == "attack":
                relationship_factor = 0.75 + 0.25 * (1.0 - rel.trust)
            orientation = {
                "loyalty_expectation": 0.500,
                "betrayal_sensitivity": 0.500,
                "repair_patience": 0.500,
                "escalation_readiness": 0.500,
                **dna.relationship_orientation,
            }
            loyalty = clamp(orientation["loyalty_expectation"])
            betrayal = clamp(orientation["betrayal_sensitivity"])
            patience = clamp(orientation["repair_patience"])
            escalation = clamp(orientation["escalation_readiness"])
            injury = rel.loyalty_injury
            structural = rel.structural_unreliability
            mistake = rel.mistake_attribution
            repetition = min(1.0, rel.betrayal_count / 3.0)
            failed = min(1.0, rel.failed_response_count / 3.0)
            same_action_failure = (
                min(1.0, rel.consecutive_action_count / 2.0) * failed
                if rel.last_action == action.key else 0.0
            )
            posture = action.relationship_posture
            if posture == "repair":
                relationship_history_modifier = (
                    7.0 * patience * (1.0 - injury)
                    + 4.0 * dependency_index
                    - 13.0 * injury * failed * (1.15 - patience)
                    + 5.0 * mistake
                    - 12.0 * structural * (1.10 - patience)
                    - 8.0 * same_action_failure
                )
            elif posture == "boundary":
                relationship_history_modifier = (
                    11.0 * injury * (0.45 + 0.55 * betrayal)
                    + 3.0 * dependency_index
                    + 4.0 * repetition * escalation
                    + 5.0 * structural * escalation
                    - 11.0 * same_action_failure
                )
            elif posture == "rupture":
                relationship_history_modifier = (
                    19.0 * injury * betrayal
                    + 10.0 * alternative_index
                    + 7.0 * repetition * escalation
                    + 9.0 * structural * escalation
                    - 15.0 * exit_lock
                    - 7.0 * (1.0 - injury)
                )
            elif posture == "comply":
                relationship_history_modifier = (
                    5.0 * exit_lock - 15.0 * injury * loyalty - 5.0 * failed
                )
            elif posture == "exit":
                relationship_history_modifier = (
                    14.0 * injury
                    + 12.0 * alternative_index
                    + 5.0 * repetition
                    + 8.0 * structural
                    - 13.0 * exit_lock
                    - 4.0 * (1.0 - injury)
                )
            relationship_row = {
                "trust": rel.trust,
                "operational_reliability": rel.operational_reliability,
                "dependency": rel.dependency,
                "alternative_capacity": rel.alternative_capacity,
                "dependency_index": dependency_index,
                "alternative_index": alternative_index,
                "exit_lock": exit_lock,
                "loyalty_injury": injury,
                "betrayal_count": rel.betrayal_count,
                "failed_response_count": rel.failed_response_count,
                "mistake_attribution": mistake,
                "structural_unreliability": structural,
                "last_action": rel.last_action,
                "relationship_posture": posture,
                "history_modifier": relationship_history_modifier,
                "factor": relationship_factor,
            }
        resource_feasibility = 15.0 * mean_ratio * relationship_factor - 18.0 * cost_load

        value_weights = {value.key: value.weight for value in dna.value_hierarchy}
        value_fit = sum(value_weights.get(key, 0.0) * clamp(float(impact), -1.0, 1.0) for key, impact in action.value_impacts.items())
        live_goal_fit = sum(clamp(float(goals.get(key, 0.0))) * clamp(float(impact), -1.0, 1.0) for key, impact in action.goal_impacts.items())
        goal_alignment = 22.0 * value_fit + 14.0 * live_goal_fit

        context_risks = [dna.risk_context_appetite[tag] for tag in action.risk_tags if tag in dna.risk_context_appetite]
        effective_risk = float(effective["risk_appetite"])
        if context_risks:
            context_target = sum(context_risks) / len(context_risks)
            effective_risk = clamp(0.45 * effective_risk + 0.55 * context_target)
        knownness = clamp(action.information_confidence)
        expected_upside = action.upside * (0.55 + 0.45 * effective_ambition) * effective_risk
        expected_loss = action.downside * (1.15 - effective_risk)
        ambiguity = action.uncertainty * (1.0 - knownness) * (1.15 - dna.adaptability)
        irreversible_cost = action.irreversibility * (1.0 - effective_risk) * (0.75 + pressure)
        risk_calculation = 24.0 * (expected_upside - expected_loss - ambiguity - irreversible_cost)

        energy_fit = -13.0 * max(0.0, action.effort - energy)
        exposure_fit = -10.0 * action.visibility * max(0.0, 0.55 - confidence)
        control_need = 1.0 - control
        preferred_control = max(
            (effective_control_preferences.get(domain, 0.0) for domain in action.control_domains),
            default=0.0,
        )
        control_fit = 15.0 * control_need * action.restores_control * preferred_control
        pressure_fit = -8.0 * pressure * action.effort * (1.0 - resistance)
        current_state_modifier = energy_fit + exposure_fit + control_fit + pressure_fit

        memory_modifier = 0.0
        memory_rows: list[dict[str, Any]] = []
        action_tags = tuple(set(action.event_tags + action.risk_tags + action.identity_tags + tuple(scene_tags)))
        for memory in runtime.memories:
            resonance = overlap(memory.tags, action_tags)
            severity = memory.severity
            unresolved = memory.unresolved
            wound = -16.0 * resonance * severity * unresolved * (1.10 - 0.45 * dna.adaptability)
            learned = 10.0 * overlap(memory.learned_response_tags, action.identity_tags + action.control_domains) * severity
            valence = 6.0 * resonance * memory.valence * severity
            contribution = wound + learned + valence
            if abs(contribution) > 1e-8:
                memory_rows.append({"event_id": memory.event_id, "resonance": resonance, "contribution": contribution})
            memory_modifier += contribution

        drive_fit = overlap(dna.core_drive_tags, action.identity_tags)
        strategy_fit = dna.conflict_strategies.get(action.conflict_strategy, 0.0)
        control_identity = preferred_control * (0.4 + 0.6 * action.restores_control)
        negative_values = sum(max(0.0, -impact) * value_weights.get(key, 0.0) for key, impact in action.value_impacts.items())
        identity_consistency = (
            9.0 * drive_fit
            + 6.0 * strategy_fit
            + 6.0 * control_identity
            - 12.0 * negative_values * (0.5 + 0.5 * identity_integrity)
        )

        total = (
            goal_alignment
            + resource_feasibility
            + risk_calculation
            + current_state_modifier
            + memory_modifier
            + identity_consistency
            + relationship_history_modifier
        )
        if rejected:
            total = -1_000_000.0
        diagnostics = {
            "effective_risk_appetite": round(effective_risk, 4),
            "resource_ratio": round(mean_ratio, 4),
            "relationship": relationship_row,
            "memory_rows": quantize3(memory_rows),
            "state_before": asdict(state),
            "effective_personality": effective,
            "card_evidence_confidence": card.evidence_confidence,
            "resource_constraint_mode": "soft" if soft_resource_constraints else "hard_v2_compatibility",
        }
        return ActionScore(
            action.key,
            round(total, 3),
            round(goal_alignment, 3),
            round(resource_feasibility, 3),
            round(risk_calculation, 3),
            round(current_state_modifier, 3),
            round(memory_modifier, 3),
            round(identity_consistency, 3),
            tuple(rejected),
            quantize3(diagnostics),
            round(relationship_history_modifier, 3),
        )

    def apply_event(self, actor: str, event: WorldEvent) -> dict[str, Any]:
        runtime = self.runtime[actor]
        exposure_counts = []
        for counterpart, deltas in event.relationship_deltas.items():
            if any(float(value) < 0 for value in deltas.values() if isinstance(value, (int, float))):
                rel = runtime.relationships.setdefault(counterpart, RelationshipMemory(counterpart))
                exposure_counts.append(rel.pattern_exposures.get(event.event_type, 0))
        prior_exposure = max(exposure_counts, default=0)
        # Repeated shocks become less surprising/stress-amplifying, but their
        # relationship evidence is still applied in full below.
        habituation_factor = 1.0 / (1.0 + 0.600 * prior_exposure)
        impact_profile = dict(event.impact_profile)
        impact_profile["pressure"] = float(impact_profile.get("pressure", 1.0)) * habituation_factor
        impact_profile["energy"] = float(impact_profile.get("energy", 0.35)) * math.sqrt(habituation_factor)
        adjusted_event = replace(
            event,
            surprise=event.surprise * habituation_factor,
            impact_profile=impact_profile,
        )
        result = self.pss.process_event(actor, adjusted_event)
        relationship_updates = {}
        for counterpart, deltas in event.relationship_deltas.items():
            rel = runtime.relationships.setdefault(counterpart, RelationshipMemory(counterpart))
            for key, delta in deltas.items():
                if key in {"dependency", "alternative_capacity"} and isinstance(delta, Mapping):
                    current = getattr(rel, key)
                    for domain, domain_delta in delta.items():
                        current[domain] = current.get(domain, 0.5) + float(domain_delta)
                elif hasattr(rel, key) and key not in {
                    "counterpart", "last_event", "last_action", "pattern_exposures"
                }:
                    setattr(rel, key, getattr(rel, key) + delta)
            negative = [
                abs(float(deltas[key]))
                for key in ("trust", "operational_reliability")
                if key in deltas and float(deltas[key]) < 0
            ]
            if negative:
                magnitude = sum(negative) / len(negative)
                orientation = {
                    "loyalty_expectation": 0.500,
                    "betrayal_sensitivity": 0.500,
                    **self.cards[actor].dna.relationship_orientation,
                }
                prior = rel.pattern_exposures.get(event.event_type, 0)
                rel.pattern_exposures[event.event_type] = prior + 1
                rel.betrayal_count += 1
                rel.loyalty_injury += (
                    magnitude
                    * (0.45 + 0.55 * clamp(orientation["betrayal_sensitivity"]))
                    * (0.45 + 0.55 * clamp(orientation["loyalty_expectation"]))
                    * (1.0 + 0.15 * min(prior, 3))
                )
                rel.structural_unreliability += magnitude * (0.25 + 0.25 * min(prior, 2))
                rel.mistake_attribution = max(
                    0.0,
                    0.65 - 0.20 * prior - 0.50 * rel.structural_unreliability,
                )
            rel.last_event = event.event_id
            rel.normalize()
            relationship_updates[counterpart] = asdict(rel)
        runtime.turn += 1
        return quantize3({
            "actor": actor,
            "event": event.event_id,
            "impact": result["impact"],
            "state": asdict(runtime.state),
            "habituation": {
                "prior_pattern_exposures": prior_exposure,
                "factor": habituation_factor,
                "interpretation": "lower acute pressure; full evidence update",
            },
            "relationship_updates": relationship_updates,
        })

    def apply_outcome(self, actor: str, outcome: ActionOutcome) -> dict[str, Any]:
        runtime = self.runtime[actor]
        result = self.pss.record_outcome(
            actor,
            outcome.action,
            outcome.success,
            outcome.tags,
            workload=outcome.workload,
        )
        if outcome.control_restoration:
            self.pss.restore_control(actor, outcome.control_restoration, outcome.action)
        if outcome.identity_alignment:
            self.pss.reinforce_identity(actor, outcome.identity_alignment, outcome.action)
        if outcome.target_actor:
            rel = runtime.relationships.setdefault(outcome.target_actor, RelationshipMemory(outcome.target_actor))
            for key, delta in outcome.relationship_delta.items():
                if key in {"dependency", "alternative_capacity"} and isinstance(delta, Mapping):
                    current = getattr(rel, key)
                    for domain, domain_delta in delta.items():
                        current[domain] = current.get(domain, 0.5) + float(domain_delta)
                elif hasattr(rel, key) and key not in {"counterpart", "last_event"}:
                    setattr(rel, key, getattr(rel, key) + delta)
            if rel.last_action == outcome.action:
                rel.consecutive_action_count += 1
            else:
                rel.consecutive_action_count = 1
            rel.last_action = outcome.action
            if outcome.success < 0.650:
                rel.failed_response_count += 1
            else:
                rel.failed_response_count = max(0, rel.failed_response_count - 1)
                rel.loyalty_injury -= 0.180 * outcome.success
                rel.structural_unreliability -= 0.120 * outcome.success
                rel.mistake_attribution += 0.100 * outcome.success
            rel.last_event = outcome.action
            rel.normalize()
        runtime.turn += 1
        return quantize3({"actor": actor, "action": outcome.action, "pss_update": result, "state": asdict(runtime.state)})

    def advance_time(self, actor: str, days: int, workload: float = 0.0) -> dict[str, Any]:
        result = self.pss.advance_time(actor, days, workload)
        self.runtime[actor].turn += 1
        return result

    def recover(self, actor: str, turns: int = 1) -> dict[str, Any]:
        """Compatibility wrapper: one old turn equals seven elapsed days."""
        return self.advance_time(actor, days=7 * turns)

    def payload(self) -> dict[str, Any]:
        return quantize3({
            "schema_version": "persona-runtime-pss-1.0",
            "political_state_system": self.pss.payload(),
            "actors": {
                actor: {
                    "card": _card_payload(card),
                    "runtime": asdict(self.runtime[actor]),
                }
                for actor, card in self.cards.items()
            },
        })


def _copy_runtime(runtime: PersonaRuntime) -> PersonaRuntime:
    return PersonaRuntime(
        state=CurrentState(**asdict(runtime.state)),
        memories=[EventMemory(**asdict(memory)) for memory in runtime.memories],
        relationships={key: RelationshipMemory(**asdict(value)) for key, value in runtime.relationships.items()},
        turn=runtime.turn,
    )


def _parse_card(actor: str, raw: Mapping[str, Any]) -> PersonaCard:
    fixed = raw["fixed_personality"]
    decision = raw["decision_parameters"]
    pss = raw["political_state_system"]
    dynamic = raw.get("initial_current_state", {})
    memories = [
        EventMemory(
            event_id=item["event_id"],
            tags=tuple(item.get("tags", ())),
            severity=float(item.get("severity", 0.0)),
            valence=float(item.get("valence", 0.0)),
            decay_per_day=float(item.get("decay_per_day", 0.01)),
            unresolved=float(item.get("unresolved", 0.0)),
            learned_response_tags=tuple(item.get("learned_response_tags", ())),
        )
        for item in raw.get("event_memory", ())
    ]
    relationships = {
        counterpart: _parse_relationship(counterpart, values)
        for counterpart, values in raw.get("relationship_memory", {}).items()
    }
    dna = CharacterDNA(
        archetype=fixed["archetype"],
        core_drive=fixed["core_drive"],
        core_drive_tags=tuple(fixed.get("core_drive_tags", ())),
        value_hierarchy=tuple(RankedValue(**item) for item in fixed["value_hierarchy"]),
        ambition=float(decision["ambition"]),
        risk_appetite=float(decision["risk_appetite"]),
        risk_context_appetite={key: float(value) for key, value in decision.get("risk_context_appetite", {}).items()},
        control_preferences={key: float(value) for key, value in decision["control_preferences"].items()},
        adaptability=float(decision["adaptability"]),
        conflict_strategies={key: float(value) for key, value in decision["conflict_strategies"].items()},
        relationship_orientation={
            key: float(value)
            for key, value in decision.get("relationship_orientation", {}).items()
        },
    )
    pss_profile = PSSProfile(
        stress_resistance=float(pss["stress_resistance"]),
        recovery_rate=float(pss["recovery_rate"]),
        sensitivity_map={key: float(value) for key, value in pss["sensitivity_map"].items()},
        state_modulation={key: float(value) for key, value in pss.get("state_modulation", {}).items()},
    )
    runtime = PersonaRuntime(CurrentState(**dynamic), memories, relationships)
    return PersonaCard(
        actor=actor,
        name=raw["name"],
        dna=dna,
        pss_profile=pss_profile,
        initial_resources={key: float(value) for key, value in raw.get("initial_resources", {}).items()},
        evidence_confidence=float(raw.get("evidence_confidence", 0.5)),
        runtime=runtime,
        source_ids=tuple(raw.get("source_ids", ())),
    )


def _parse_relationship(counterpart: str, values: Mapping[str, Any]) -> RelationshipMemory:
    """Load v3 multidimensional relations while accepting legacy scalar dependency."""
    raw = dict(values)
    trust = float(raw.get("trust", 0.50))
    dependency = raw.pop("dependency", 0.50)
    if isinstance(dependency, Mapping):
        dependency_map = {
            "organizational": float(dependency.get("organizational", 0.50)),
            "informational": float(dependency.get("informational", 0.50)),
            "electoral": float(dependency.get("electoral", 0.50)),
            "personal_trust": float(dependency.get("personal_trust", trust)),
        }
    else:
        scalar = float(dependency)
        dependency_map = {
            "organizational": scalar,
            "informational": scalar,
            "electoral": scalar,
            "personal_trust": trust,
        }
    alternative = raw.pop("alternative_capacity", None)
    if isinstance(alternative, Mapping):
        alternative_map = {
            "organizational": float(alternative.get("organizational", 0.50)),
            "informational": float(alternative.get("informational", 0.50)),
            "electoral": float(alternative.get("electoral", 0.50)),
        }
    else:
        alternative_map = {
            "organizational": 1.0 - dependency_map["organizational"],
            "informational": 1.0 - dependency_map["informational"],
            "electoral": 1.0 - dependency_map["electoral"],
        }
    raw["dependency"] = dependency_map
    raw["alternative_capacity"] = alternative_map
    relation = RelationshipMemory(counterpart=counterpart, **raw)
    relation.normalize()
    return relation


def _card_payload(card: PersonaCard) -> dict[str, Any]:
    return {
        "actor": card.actor,
        "name": card.name,
        "dna": asdict(card.dna),
        "political_state_system": asdict(card.pss_profile),
        "initial_resources": dict(card.initial_resources),
        "evidence_confidence": card.evidence_confidence,
        "source_ids": card.source_ids,
    }

"""Compatibility bridge for personality-card v2 and the pre-v3 world engine.

New scenarios should enter through ``simulation_orchestrator.py``.  This module
remains stable so archived v2 baselines can be reproduced byte-for-byte.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Mapping, Sequence

from .information_filter import InformationFilter
from .persona_v2 import (
    ActionOption,
    ActionOutcome,
    FreeAgentDecisionEngine,
    WorldEvent,
)
from .political_state import PoliticalAction, PoliticalState, PressureRule
from .interaction.intents import Intent


@dataclass(frozen=True)
class WorldAction:
    """Environment consequence plus actor-visible interpretation of that action."""

    world: PoliticalAction
    choice: ActionOption
    actor_events: Mapping[str, tuple[WorldEvent, ...]] = field(default_factory=dict)
    actor_outcomes: Mapping[str, ActionOutcome] = field(default_factory=dict)
    intent: Intent | None = None

    def __post_init__(self) -> None:
        if self.world.key != self.choice.key:
            raise ValueError("WorldAction keys must match")


@dataclass(frozen=True)
class FreeAgentNode:
    key: str
    owner: str
    actions: tuple[WorldAction, ...]
    current_goals: Mapping[str, float] = field(default_factory=dict)
    scene_tags: tuple[str, ...] = ()


class FreeAgentGame:
    """Sequential roguelike turns with independent, partially informed actors.

    No outcome is inferred from the choice.  The world action is applied first;
    votes, polls, negotiations or implementation are settled by their dedicated
    modules and then returned through ``settle_outcome``.
    """

    def __init__(
        self,
        state: PoliticalState,
        nodes: Mapping[str, FreeAgentNode],
        personas: FreeAgentDecisionEngine,
        information: InformationFilter,
        resource_bindings: Mapping[str, Mapping[str, str]],
        pressure_rules: Sequence[PressureRule] = (),
        event_observers: Sequence[object] = (),
    ) -> None:
        self.state = state
        self.nodes = dict(nodes)
        self.personas = personas
        self.information = information
        self.resource_bindings = {actor: dict(values) for actor, values in resource_bindings.items()}
        self.pressure_rules = tuple(pressure_rules)
        self.event_observers = tuple(event_observers)
        self.trace: list[dict] = []

    def _perceived_resources(self, actor: str, belief_state) -> dict[str, float]:
        card = self.personas.cards[actor]
        resources = dict(card.initial_resources)
        for resource, binding in self.resource_bindings.get(actor, {}).items():
            kind, key = binding.split(":", 1)
            if kind == "variable":
                belief = belief_state.beliefs[key]
                resources[resource] = max(0.0, min(1.0, belief.estimate / 100.0))
            elif kind == "capital":
                resources[resource] = max(0.0, min(1.0, self.state.capital.get(key, 0.0) / 100.0))
            else:
                raise ValueError(f"Unknown resource binding kind: {kind}")
        return resources

    def run(self, start_node: str, max_steps: int = 20) -> dict:
        key = start_node
        for _ in range(max_steps):
            node = self.nodes[key]
            beliefs = self.information.observe(node.owner, self.state, commit=True)
            resources = self._perceived_resources(node.owner, beliefs)
            mean_confidence = (
                sum(item.confidence for item in beliefs.beliefs.values()) / len(beliefs.beliefs)
                if beliefs.beliefs else 0.5
            )
            legal_pairs = [item for item in node.actions if self.state.legal(item.world)]
            visible_options = [
                replace(
                    item.choice,
                    legal=item.choice.legal and self.state.legal(item.world),
                    information_confidence=min(item.choice.information_confidence, mean_confidence),
                )
                for item in legal_pairs
            ]
            decision = self.personas.decide(
                node.owner,
                visible_options,
                resources,
                current_goals=node.current_goals,
                scene_tags=node.scene_tags,
            )
            selected = next(item for item in legal_pairs if item.world.key == decision.chosen_action)
            state_update = self.state.apply(selected.world, self.pressure_rules)
            for observer in self.event_observers:
                observer.record(
                    self.state,
                    event_id=f"free_decision:{node.key}",
                    actor=node.owner,
                    action=selected.world.key,
                    event_kind="free_agent_decision",
                    resource_changes=state_update,
                )
            self.trace.append({
                "node": node.key,
                "owner": node.owner,
                "chosen_action": decision.chosen_action,
                "six_component_scores": {
                    action: asdict(score) for action, score in decision.scores.items()
                },
                "perceived_resources": resources,
                "beliefs": InformationFilter.payload(beliefs),
                "current_state": asdict(self.personas.runtime[node.owner].state),
                "state_update": state_update,
            })
            if selected.world.next_node is None:
                break
            key = selected.world.next_node
        return self.payload()

    def apply_world_event(self, event: WorldEvent, affected_actors: Sequence[str]) -> list[dict]:
        return [self.personas.apply_event(actor, event) for actor in affected_actors]

    def settle_outcome(self, actor: str, outcome: ActionOutcome) -> dict:
        return self.personas.apply_outcome(actor, outcome)

    def payload(self) -> dict:
        return {
            "schema_version": "free-agent-game-2.0",
            "trace": self.trace,
            "world_state": self.state.payload(),
            "persona_runtime": self.personas.payload(),
            "warning": (
                "Scores are model explanations, not psychometric measurements. "
                "Randomness may enter world information/outcomes, never personality selection."
            ),
        }

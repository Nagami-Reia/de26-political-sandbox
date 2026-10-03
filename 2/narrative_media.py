"""A separate media route for narrative competition and legitimacy feedback.

Facts do not directly mutate public support. Actors choose media moves, competing
frames reach heterogeneous audiences, and the resulting interpretation produces
legitimacy/support signals. Personality choice is deterministic; stochasticity is
limited to reach and amplification after the media move has been chosen.
"""
from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from .persona_v2 import ActionOption, FreeAgentDecisionEngine, clamp, overlap
from .political_state import PoliticalAction, PoliticalState, PressureRule
from .political_state_system import quantize3


@dataclass(frozen=True)
class NarrativeFact:
    key: str
    issue: str
    tags: tuple[str, ...]
    salience: float
    ambiguity: float
    evidence_strength: float
    news_competition: float = 0.000
    source_status: str = "WORLD_FACT"


@dataclass(frozen=True)
class NarrativeFrame:
    key: str
    issue: str
    sponsors: tuple[str, ...]
    claim_tags: tuple[str, ...]
    contradicted_by_tags: tuple[str, ...]
    target_audiences: tuple[str, ...]
    credibility: float
    emotional_force: float
    simplicity: float
    identity_tags: tuple[str, ...] = ()
    goal_impacts: Mapping[str, float] = field(default_factory=dict)
    value_impacts: Mapping[str, float] = field(default_factory=dict)
    legitimacy_impacts: Mapping[str, float] = field(default_factory=dict)
    support_impacts: Mapping[str, float] = field(default_factory=dict)
    blame_target: str | None = None
    conflict_strategy: str = "reframe"
    relationship_posture: str = "neutral"


@dataclass(frozen=True)
class MediaChannel:
    key: str
    reach: float
    speed: float
    trust: float
    volatility: float
    audience_affinity: Mapping[str, float]
    resource_cost: float = .100
    visibility: float = .700


@dataclass(frozen=True)
class AudienceSegment:
    key: str
    size: float
    attention: float
    emotional_susceptibility: float
    identity_tags: tuple[str, ...]
    source_trust: Mapping[str, float]
    interpretation_inertia: float = .550


@dataclass(frozen=True)
class NarrativeMove:
    actor: str
    frame_key: str | None
    channel_key: str | None
    intensity: float
    resource_cost: float
    timing: float = .500

    @property
    def key(self) -> str:
        if self.frame_key is None:
            return f"media__{self.actor}__hold_message"
        return f"media__{self.actor}__{self.frame_key}__{self.channel_key}"


@dataclass(frozen=True)
class NarrativeMoveOption:
    move: NarrativeMove
    choice: ActionOption


@dataclass(frozen=True)
class NarrativeChoice:
    actor: str
    chosen_move: NarrativeMove
    decision: Mapping[str, Any]

    def payload(self) -> dict:
        return quantize3({
            "actor": self.actor,
            "chosen_move": asdict(self.chosen_move),
            "decision": self.decision,
        })


@dataclass
class NarrativeArenaState:
    audience_frame_shares: dict[str, dict[str, float]] = field(default_factory=dict)
    exposures: dict[str, int] = field(default_factory=dict)
    round: int = 0
    history: list[dict] = field(default_factory=list)

    def payload(self) -> dict:
        return quantize3(asdict(self))


@dataclass(frozen=True)
class FrameAudienceResult:
    audience: str
    frame: str
    persuasion_power: float
    narrative_share: float
    effective_credibility: float
    effective_attention: float
    evidence_alignment: float
    identity_fit: float
    saturation: float


@dataclass(frozen=True)
class AudienceNarrativeResult:
    audience: str
    winning_frame: str
    frame_shares: Mapping[str, float]
    response_strength: float


@dataclass(frozen=True)
class NarrativeRoundOutcome:
    fact: str
    round: int
    audience_results: tuple[AudienceNarrativeResult, ...]
    frame_audience_results: tuple[FrameAudienceResult, ...]
    agenda_ownership: Mapping[str, float]
    legitimacy_deltas: Mapping[str, float]
    support_deltas: Mapping[str, float]
    moves: tuple[NarrativeMove, ...]
    stochastic: bool

    def payload(self) -> dict:
        return quantize3(asdict(self))

    def apply_to_political_state(
        self,
        state: PoliticalState,
        *,
        legitimacy_variables: Mapping[str, str] | None = None,
        support_variables: Mapping[str, str] | None = None,
        capital_accounts: Mapping[str, str] | None = None,
        legitimacy_points_per_unit: float = 4.000,
        support_points_per_unit: float = 3.000,
        capital_points_per_unit: float = 10.000,
        pressure_rules: Sequence[PressureRule] = (),
    ) -> dict:
        """Apply interpretation effects only after narrative competition settles."""
        legitimacy_variables = legitimacy_variables or {}
        support_variables = support_variables or {}
        capital_accounts = capital_accounts or {}
        effects: dict[str, float] = {}
        for target, delta in self.legitimacy_deltas.items():
            variable = legitimacy_variables.get(target)
            if variable in state.variables:
                effects[variable] = effects.get(variable, 0.0) + delta * legitimacy_points_per_unit
        for target, delta in self.support_deltas.items():
            variable = support_variables.get(target)
            if variable in state.variables:
                effects[variable] = effects.get(variable, 0.0) + delta * support_points_per_unit
        capital_delta: dict[str, float] = {}
        for move in self.moves:
            account = capital_accounts.get(move.actor)
            if account:
                capital_delta[account] = (
                    capital_delta.get(account, 0.0)
                    - move.resource_cost * capital_points_per_unit
                )
        action = PoliticalAction(
            key=f"narrative_round:{self.fact}:{self.round}",
            effects={"immediate": effects, "medium": {}, "long": {}},
            capital_delta=capital_delta,
            tags=("narrative_competition", "legitimacy_feedback"),
        )
        update = state.apply(action, tuple(pressure_rules))
        update["narrative_outcome"] = self.payload()
        return update


class NarrativeMoveGenerator:
    """Create a separate media menu; it does not replace substantive actions."""

    def __init__(
        self,
        frames: Sequence[NarrativeFrame],
        channels: Sequence[MediaChannel],
        *,
        default_intensity: float = .750,
    ) -> None:
        self.frames = {row.key: row for row in frames}
        self.channels = {row.key: row for row in channels}
        self.default_intensity = clamp(default_intensity)

    def generate(self, actor: str, fact: NarrativeFact) -> tuple[NarrativeMoveOption, ...]:
        options: list[NarrativeMoveOption] = []
        for frame in self.frames.values():
            if frame.issue != fact.issue or actor not in frame.sponsors:
                continue
            evidence_fit = overlap(frame.claim_tags, fact.tags)
            contradiction = overlap(frame.contradicted_by_tags, fact.tags)
            for channel in self.channels.values():
                move = NarrativeMove(
                    actor,
                    frame.key,
                    channel.key,
                    self.default_intensity,
                    channel.resource_cost,
                    timing=channel.speed,
                )
                options.append(NarrativeMoveOption(
                    move,
                    ActionOption(
                        move.key,
                        goal_impacts=frame.goal_impacts,
                        value_impacts=frame.value_impacts,
                        required_resources={"public_capital": min(.950, channel.resource_cost)},
                        resource_costs={"public_capital": channel.resource_cost},
                        upside=clamp(.35 + .30 * frame.credibility + .20 * frame.emotional_force + .15 * evidence_fit),
                        downside=clamp(.20 + .35 * contradiction + .25 * channel.volatility),
                        uncertainty=clamp(fact.ambiguity * (.60 + .40 * channel.volatility)),
                        irreversibility=clamp(.15 + .45 * channel.visibility * frame.emotional_force),
                        effort=clamp(.20 + .45 * move.intensity + .20 * channel.speed),
                        visibility=channel.visibility,
                        information_confidence=clamp((1.0 - fact.ambiguity) * (.60 + .40 * fact.evidence_strength)),
                        control_domains=("direction", "communication"),
                        restores_control=.35 * channel.speed,
                        conflict_strategy=frame.conflict_strategy,
                        identity_tags=tuple(dict.fromkeys(frame.identity_tags + ("narrative_control",))),
                        event_tags=fact.tags + ("media_route",),
                        risk_tags=("relationally_fragile",) if frame.blame_target else (),
                        target_actor=frame.blame_target,
                        relationship_posture=frame.relationship_posture,
                        instrumental_impacts={
                            "agenda_control": .45 + .35 * channel.reach,
                            "message_speed": channel.speed,
                        },
                        substantive_impacts={
                            "evidence_alignment": evidence_fit - contradiction,
                            "public_deliberation": .20 - .25 * frame.emotional_force,
                        },
                    ),
                ))
        hold = NarrativeMove(actor, None, None, 0.0, 0.0, 0.0)
        options.append(NarrativeMoveOption(
            hold,
            ActionOption(
                hold.key,
                value_impacts={"unity": .050},
                upside=.080,
                downside=.180 * fact.salience,
                uncertainty=.050,
                effort=.020,
                visibility=.0,
                information_confidence=1.0,
                conflict_strategy="avoid",
                identity_tags=("message_discipline",),
                event_tags=fact.tags + ("media_silence",),
            ),
        ))
        return tuple(options)

    def choose(
        self,
        actor: str,
        fact: NarrativeFact,
        personas: FreeAgentDecisionEngine,
        resources: Mapping[str, float],
        current_goals: Mapping[str, float] | None = None,
    ) -> NarrativeChoice:
        options = self.generate(actor, fact)
        decision = personas.decide(
            actor,
            [row.choice for row in options],
            resources,
            current_goals=current_goals or {},
            scene_tags=fact.tags + ("narrative_competition",),
            soft_resource_constraints=True,
        )
        selected = next(row.move for row in options if row.choice.key == decision.chosen_action)
        return NarrativeChoice(
            actor,
            selected,
            {
                "chosen_action": decision.chosen_action,
                "scores": {key: asdict(value) for key, value in decision.scores.items()},
                "rule": decision.rule,
            },
        )


class NarrativeArena:
    def __init__(
        self,
        frames: Sequence[NarrativeFrame],
        channels: Sequence[MediaChannel],
        audiences: Sequence[AudienceSegment],
        *,
        state: NarrativeArenaState | None = None,
        seed: int = 0,
        stochastic: bool = False,
    ) -> None:
        self.frames = {row.key: row for row in frames}
        self.channels = {row.key: row for row in channels}
        self.audiences = {row.key: row for row in audiences}
        self.state = state or NarrativeArenaState()
        self.rng = random.Random(seed)
        self.stochastic = stochastic

    def _validate_move(self, fact: NarrativeFact, move: NarrativeMove) -> None:
        if move.frame_key is None:
            return
        if move.frame_key not in self.frames or move.channel_key not in self.channels:
            raise KeyError(f"unknown narrative frame/channel in {move.key}")
        frame = self.frames[move.frame_key]
        if frame.issue != fact.issue:
            raise ValueError(f"frame {frame.key} does not address fact issue {fact.issue}")
        if move.actor not in frame.sponsors:
            raise ValueError(f"actor {move.actor} cannot sponsor frame {frame.key}")

    def resolve_round(
        self,
        fact: NarrativeFact,
        moves: Sequence[NarrativeMove],
    ) -> NarrativeRoundOutcome:
        for move in moves:
            self._validate_move(fact, move)
        active_moves = tuple(move for move in moves if move.frame_key is not None)
        self.state.round += 1
        frame_rows: list[FrameAudienceResult] = []
        audience_rows: list[AudienceNarrativeResult] = []
        actor_power: dict[str, float] = {}
        legitimacy: dict[str, float] = {}
        support: dict[str, float] = {}

        for audience in self.audiences.values():
            prior = dict(self.state.audience_frame_shares.get(audience.key, {"__unframed__": 1.0}))
            inertia_power = max(.050, audience.interpretation_inertia)
            powers: dict[str, float] = {
                key: share * inertia_power for key, share in prior.items()
            }
            details: dict[str, dict[str, float]] = {}
            move_power_total = 0.0
            for move in active_moves:
                frame = self.frames[move.frame_key]
                channel = self.channels[move.channel_key]
                exposure_key = f"{audience.key}|{frame.key}|{channel.key}"
                prior_exposures = self.state.exposures.get(exposure_key, 0)
                saturation = min(.850, prior_exposures * .120)
                evidence_fit = overlap(frame.claim_tags, fact.tags)
                contradiction = overlap(frame.contradicted_by_tags, fact.tags)
                identity_fit = overlap(frame.identity_tags, audience.identity_tags)
                source_trust = clamp(audience.source_trust.get(move.actor, .500))
                target_fit = 1.0 if audience.key in frame.target_audiences else .550
                emotional_fit = 1.0 - .500 * abs(frame.emotional_force - audience.emotional_susceptibility)
                credibility = (
                    frame.credibility
                    * channel.trust
                    * source_trust
                    * (.55 + .45 * evidence_fit * fact.evidence_strength)
                    * (1.0 - .65 * contradiction * fact.evidence_strength)
                )
                contingency = self.rng.uniform(.750, 1.250) if self.stochastic else 1.0
                attention = (
                    fact.salience
                    * audience.attention
                    * (1.0 - .75 * fact.news_competition)
                    * channel.reach
                    * channel.audience_affinity.get(audience.key, .500)
                    * move.intensity
                    * (1.0 - saturation)
                    * target_fit
                    * contingency
                )
                resonance = (
                    (.45 + .55 * frame.emotional_force * emotional_fit)
                    * (.55 + .45 * frame.simplicity)
                    * (.65 + .35 * identity_fit)
                )
                volatility_penalty = 1.0 - channel.volatility * (.20 + .30 * fact.ambiguity)
                power = max(0.0, attention * credibility * resonance * volatility_penalty)
                powers[frame.key] = powers.get(frame.key, 0.0) + power
                move_power_total += power
                actor_power[move.actor] = actor_power.get(move.actor, 0.0) + power * audience.size
                prior_detail = details.get(frame.key)
                if prior_detail is None or power > prior_detail["power"]:
                    details[frame.key] = {
                        "power": power,
                        "credibility": credibility,
                        "attention": attention,
                        "evidence_fit": evidence_fit,
                        "identity_fit": identity_fit,
                        "saturation": saturation,
                    }
                self.state.exposures[exposure_key] = prior_exposures + 1
            total = sum(powers.values())
            shares = {
                key: (value / total if total > 0.0 else 0.0)
                for key, value in powers.items()
            }
            self.state.audience_frame_shares[audience.key] = shares
            response_strength = move_power_total / (move_power_total + inertia_power) if move_power_total else 0.0
            winner = max(shares, key=lambda key: (shares[key], key))
            audience_rows.append(AudienceNarrativeResult(
                audience.key,
                winner,
                {key: round(value, 3) for key, value in shares.items()},
                round(response_strength, 3),
            ))
            for frame_key, detail in details.items():
                frame_rows.append(FrameAudienceResult(
                    audience.key,
                    frame_key,
                    round(detail["power"], 3),
                    round(shares.get(frame_key, 0.0), 3),
                    round(detail["credibility"], 3),
                    round(detail["attention"], 3),
                    round(detail["evidence_fit"], 3),
                    round(detail["identity_fit"], 3),
                    round(detail["saturation"], 3),
                ))
                frame = self.frames[frame_key]
                influence = audience.size * shares.get(frame_key, 0.0) * response_strength
                for target, delta in frame.legitimacy_impacts.items():
                    legitimacy[target] = legitimacy.get(target, 0.0) + influence * float(delta)
                for target, delta in frame.support_impacts.items():
                    support[target] = support.get(target, 0.0) + influence * float(delta)

        total_actor_power = sum(actor_power.values())
        ownership = {
            actor: (power / total_actor_power if total_actor_power else 0.0)
            for actor, power in actor_power.items()
        }
        outcome = NarrativeRoundOutcome(
            fact.key,
            self.state.round,
            tuple(audience_rows),
            tuple(frame_rows),
            {key: round(value, 3) for key, value in ownership.items()},
            {key: round(value, 3) for key, value in legitimacy.items()},
            {key: round(value, 3) for key, value in support.items()},
            tuple(moves),
            self.stochastic,
        )
        self.state.history.append(outcome.payload())
        return outcome

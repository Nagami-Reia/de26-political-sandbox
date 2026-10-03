"""Seeded routine political activity and attention-limited public effects."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import random
from typing import Mapping

from .political_state import PoliticalAction, PoliticalState, PressureRule


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ActivityTemplate:
    key: str
    channel_effects: Mapping[str, float]
    capital_cost: float = 0.0
    base_reach: float = .5
    base_credibility: float = .5
    novelty: float = .5
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoutineActivityProgram:
    actor: str
    expected_events_per_day: float
    activity_mix: Mapping[str, float]
    issue_mix: Mapping[str, float]
    capital_account: str
    channel_aliases: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.expected_events_per_day < 0:
            raise ValueError("expected_events_per_day cannot be negative")
        if not self.activity_mix or sum(self.activity_mix.values()) <= 0:
            raise ValueError("activity_mix needs positive weight")
        if not self.issue_mix or sum(self.issue_mix.values()) <= 0:
            raise ValueError("issue_mix needs positive weight")


@dataclass(frozen=True)
class ActivityContext:
    issue_salience: float
    audience_alignment: float
    news_competition: float
    saturation: float
    local_relevance: float = .5
    detection_floor: float = .08

    def __post_init__(self) -> None:
        for key in ("issue_salience", "audience_alignment", "news_competition", "saturation", "local_relevance"):
            if not 0 <= getattr(self, key) <= 1:
                raise ValueError(f"{key} must be within 0..1")
        if self.detection_floor < 0:
            raise ValueError("detection_floor cannot be negative")


@dataclass(frozen=True)
class PoliticalActivity:
    event_id: str
    day: int
    actor: str
    activity_type: str
    issue: str
    source_status: str = "GENERATED_ROUTINE_EVENT"


@dataclass(frozen=True)
class ActivityOutcome:
    activity: PoliticalActivity
    reach: float
    effective_attention: float
    effects: Mapping[str, float]
    capital_delta: Mapping[str, float]
    impact_class: str
    explanation: str


class PoliticalActivityModel:
    def __init__(self, templates: Mapping[str, ActivityTemplate]):
        self.templates = dict(templates)

    @staticmethod
    def _weighted_choice(weights: Mapping[str, float], rng: random.Random) -> str:
        total = sum(max(0.0, value) for value in weights.values())
        u = rng.random() * total; cumulative = 0.0
        for key, value in weights.items():
            cumulative += max(0.0, value)
            if u <= cumulative:
                return key
        return next(reversed(weights))

    def generate(
        self,
        programs: tuple[RoutineActivityProgram, ...],
        days: int,
        seed: int,
        stochastic: bool = True,
    ) -> tuple[PoliticalActivity, ...]:
        if days < 0:
            raise ValueError("days cannot be negative")
        rng = random.Random(seed); events = []; serial = 0
        for day in range(1, days + 1):
            for program in programs:
                rate = program.expected_events_per_day
                if stochastic:
                    count = int(rate)
                    if rng.random() < rate - int(rate): count += 1
                else:
                    # Expected-calendar baseline: deterministic carry produces
                    # the requested long-run cadence without a random draw.
                    count = floor_nonnegative(day * rate) - floor_nonnegative((day - 1) * rate)
                for _ in range(count):
                    serial += 1
                    activity_type = self._weighted_choice(program.activity_mix, rng) if stochastic else max(program.activity_mix, key=program.activity_mix.get)
                    issue = self._weighted_choice(program.issue_mix, rng) if stochastic else max(program.issue_mix, key=program.issue_mix.get)
                    if activity_type not in self.templates:
                        raise KeyError(f"missing activity template: {activity_type}")
                    events.append(PoliticalActivity(f"PA{serial:04d}", day, program.actor, activity_type, issue))
        return tuple(events)

    def resolve(
        self,
        activity: PoliticalActivity,
        context: ActivityContext,
        capital_account: str,
        channel_aliases: Mapping[str, str] | None = None,
        seed: int | None = None,
        stochastic: bool = False,
    ) -> ActivityOutcome:
        template = self.templates[activity.activity_type]
        reach = template.base_reach
        contingency = 1.0
        if stochastic:
            rng = random.Random(seed)
            reach = _clamp(reach * rng.uniform(.55, 1.45))
            contingency = rng.uniform(.75, 1.25)
        attention = (
            reach * template.base_credibility * context.issue_salience
            * (.35 + .65 * context.audience_alignment)
            * (1 - .75 * context.news_competition)
            * (1 - .65 * context.saturation)
            * (.65 + .35 * template.novelty)
            * (.75 + .25 * context.local_relevance)
            * contingency
        )
        aliases = channel_aliases or {}
        effects = {aliases.get(key, key): round(delta * attention, 4) for key, delta in template.channel_effects.items()}
        poll_keys = [key for key in effects if "poll" in key or "support" in key or "acceptance" in key]
        poll_signal = max((abs(effects[key]) for key in poll_keys), default=0.0)
        if poll_signal < context.detection_floor:
            for key in poll_keys: effects[key] = 0.0
            impact_class = "no_detectable_poll_effect"
            explanation = "The activity occurred, but attention-adjusted poll/support effects stayed below the declared detection floor."
        elif poll_signal < context.detection_floor * 3:
            impact_class = "small_effect"
            explanation = "The activity cleared the detection floor but remained attention-limited."
        else:
            impact_class = "salient_effect"
            explanation = "High reach, salience and audience fit produced a visible model effect."
        capital_delta = {capital_account: -template.capital_cost} if template.capital_cost else {}
        return ActivityOutcome(activity, round(reach, 4), round(attention, 4), effects, capital_delta, impact_class, explanation)

    def apply(
        self,
        state: PoliticalState,
        outcome: ActivityOutcome,
        pressure_rules: tuple[PressureRule, ...] = (),
    ) -> dict:
        effects = {key: value for key, value in outcome.effects.items() if key in state.variables}
        action = PoliticalAction(
            key=f"activity:{outcome.activity.event_id}:{outcome.activity.activity_type}",
            effects={"immediate": effects, "medium": {}, "long": {}},
            capital_delta=outcome.capital_delta,
            tags=("routine_political_activity", outcome.activity.activity_type),
        )
        update = state.apply(action, pressure_rules)
        update["activity_outcome"] = asdict(outcome)
        return update


def floor_nonnegative(value: float) -> int:
    return max(0, int(value + 1e-12))

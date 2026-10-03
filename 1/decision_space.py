"""Generate actor-specific decision spaces from events instead of scripted trees.

The pipeline is deliberately asymmetric:

    event -> perception distribution -> active goals -> strategy families
          -> execution styles -> outcome distributions

Perception is inferred from fog-of-war, memory and relationships; an actor does
not get to choose the most convenient belief.  Personality remains deterministic
and chooses only among the generated actions.  Randomness is confined to the
outcome resolver.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Mapping, Sequence

from .free_agent_game import WorldAction
from .information_filter import BeliefState
from .persona_v2 import ActionOption, PersonaCard, PersonaRuntime, clamp, overlap
from .political_state import HORIZONS, PoliticalAction
from .political_state_system import quantize3


def _scale_effects(
    effects: Mapping[str, Mapping[str, float]], multiplier: float
) -> dict[str, dict[str, float]]:
    return {
        horizon: {key: float(value) * multiplier for key, value in effects.get(horizon, {}).items()}
        for horizon in HORIZONS
    }


def _normalize(rows: Mapping[str, float]) -> dict[str, float]:
    total = sum(max(0.0, value) for value in rows.values())
    if total <= 0.0:
        return {key: round(1.0 / len(rows), 3) for key in rows} if rows else {}
    return {key: round(max(0.0, value) / total, 3) for key, value in rows.items()}


@dataclass(frozen=True)
class PerceptionTemplate:
    key: str
    label: str
    domains: tuple[str, ...] = ()
    cue_tags: tuple[str, ...] = ()
    interpretation_tags: tuple[str, ...] = ()
    base_weight: float = 0.500
    ambiguity_affinity: float = 0.500
    authority_threat_affinity: float = 0.000


@dataclass(frozen=True)
class GoalTemplate:
    key: str
    value_keys: tuple[str, ...]
    cue_tags: tuple[str, ...] = ()
    base_salience: float = 0.350
    pressure_sensitivity: float = 0.000
    confidence_sensitivity: float = 0.000
    domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyTemplate:
    key: str
    label: str
    domains: tuple[str, ...]
    goal_keys: tuple[str, ...]
    conflict_strategy: str
    identity_tags: tuple[str, ...]
    control_domains: tuple[str, ...] = ()
    style_keys: tuple[str, ...] = ()
    required_resources: Mapping[str, float] = field(default_factory=dict)
    required_offices: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    instrumental_impacts: Mapping[str, float] = field(default_factory=dict)
    substantive_impacts: Mapping[str, float] = field(default_factory=dict)
    value_impacts: Mapping[str, float] = field(default_factory=dict)
    institutional_deviation: float = 0.000
    necessity_frame_alignment: float = 0.000
    base_upside: float = 0.500
    base_downside: float = 0.400
    base_effort: float = 0.500
    base_control_restoration: float = 0.300


@dataclass(frozen=True)
class ExecutionStyleTemplate:
    key: str
    label: str
    compatible_strategies: tuple[str, ...]
    conflict_strategy: str
    control_domains: tuple[str, ...] = ()
    visibility: float = 0.500
    effort_multiplier: float = 1.000
    downside_multiplier: float = 1.000
    uncertainty_multiplier: float = 1.000
    feasibility_multiplier: float = 1.000
    relationship_posture: str = "neutral"


@dataclass(frozen=True)
class StrategyEffectModel:
    effects: Mapping[str, Mapping[str, float]]
    uncertainty: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    capital_delta: Mapping[str, float] = field(default_factory=dict)
    pressure_delta: Mapping[str, float] = field(default_factory=dict)
    base_feasibility: float = 0.650
    irreversibility: float = 0.300
    next_node: str | None = None
    outcome_effect_overrides: Mapping[str, Mapping[str, Mapping[str, float]]] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class DecisionEvent:
    key: str
    domain: str
    tags: tuple[str, ...]
    severity: float
    ambiguity: float
    effect_models: Mapping[str, StrategyEffectModel]
    source_actor: str | None = None
    signal_variables: Mapping[str, float] = field(default_factory=dict)
    allowed_strategy_keys: tuple[str, ...] = ()
    target_actor: str | None = None


@dataclass(frozen=True)
class PerceptionAssessment:
    key: str
    label: str
    weight: float
    information_confidence: float
    cue_fit: float
    perceived_signal: float
    memory_resonance: float
    relationship_trust: float | None
    interpretation_tags: tuple[str, ...]


@dataclass(frozen=True)
class GoalAssessment:
    key: str
    salience: float
    value_fit: float
    event_fit: float
    state_modifier: float


@dataclass(frozen=True)
class DecisionPath:
    perception: str
    active_goals: tuple[str, ...]
    strategy: str
    execution_style: str


@dataclass(frozen=True)
class OutcomeBranch:
    key: str
    conditional_weight: float
    success_level: float
    world_action: PoliticalAction
    interpretation: str


@dataclass(frozen=True)
class GeneratedAction:
    world_action: WorldAction
    path: DecisionPath
    generation_score: float
    outcome_branches: tuple[OutcomeBranch, ...]

    def payload(self) -> dict:
        return quantize3({
            "action": self.world_action.choice.key,
            "path": asdict(self.path),
            "generation_score": self.generation_score,
            "outcomes": [
                {
                    "key": row.key,
                    "conditional_weight": row.conditional_weight,
                    "success_level": row.success_level,
                    "interpretation": row.interpretation,
                }
                for row in self.outcome_branches
            ],
        })


@dataclass(frozen=True)
class GeneratedDecisionSpace:
    event: DecisionEvent
    actor: str
    perceptions: tuple[PerceptionAssessment, ...]
    goals: tuple[GoalAssessment, ...]
    actions: tuple[GeneratedAction, ...]
    rejected_generation_paths: tuple[Mapping[str, Any], ...] = ()

    @property
    def world_actions(self) -> tuple[WorldAction, ...]:
        return tuple(row.world_action for row in self.actions)

    def by_key(self) -> dict[str, GeneratedAction]:
        return {row.world_action.choice.key: row for row in self.actions}

    def payload(self) -> dict:
        return quantize3({
            "event": {
                "key": self.event.key,
                "domain": self.event.domain,
                "tags": list(self.event.tags),
                "severity": self.event.severity,
                "ambiguity": self.event.ambiguity,
            },
            "actor": self.actor,
            "perception_branch": [asdict(row) for row in self.perceptions],
            "goal_branch": [asdict(row) for row in self.goals],
            "strategy_style_actions": [row.payload() for row in self.actions],
            "rejected_generation_paths": list(self.rejected_generation_paths),
        })


@dataclass(frozen=True)
class ActionLibrary:
    perceptions: tuple[PerceptionTemplate, ...]
    goals: tuple[GoalTemplate, ...]
    strategies: tuple[StrategyTemplate, ...]
    styles: tuple[ExecutionStyleTemplate, ...]


def default_action_library() -> ActionLibrary:
    """Small reusable grammar. Scenarios supply effects, not hand-authored menus."""
    perceptions = (
        PerceptionTemplate("implementation_problem", "implementation/majority problem", ("legislative", "party", "coalition"), ("votes", "implementation", "capacity"), ("implementation", "organization"), .62, .25),
        PerceptionTemplate("coalition_bargain", "coalition bargaining conflict", ("legislative", "coalition"), ("coalition", "partner", "bargain"), ("coalition", "negotiation"), .58, .35),
        PerceptionTemplate("authority_test", "test of leadership authority", ("legislative", "party", "crisis", "electoral"), ("authority", "defiance", "leadership"), ("authority_challenge",), .42, .45, .80),
        PerceptionTemplate("limited_warning", "bounded warning rather than full escalation", ("security", "crisis"), ("warning", "limited", "signal"), ("limited_escalation",), .55, .50),
        PerceptionTemplate("escalation_onset", "opening of a wider escalation", ("security", "crisis"), ("attack", "escalation", "deterrence"), ("systemic_crisis", "deterrence"), .50, .35, .35),
        PerceptionTemplate("information_uncertain", "evidence remains incomplete", (), ("uncertain", "intelligence", "unverified"), ("verification", "uncertainty"), .44, .95),
    )
    goals = (
        GoalTemplate("preserve_authority", ("political_authority", "strategic_direction"), ("authority", "leadership", "defiance"), .38, .50, .10),
        GoalTemplate("deliver_policy", ("reform_achievement", "implementation", "wirksamkeit"), ("legislative", "implementation", "reform"), .48, .15, .25),
        GoalTemplate("secure_organization", ("organization_success", "political_stability"), ("votes", "organization", "party"), .46, .35, .10),
        GoalTemplate("preserve_unity", ("unity", "political_stability"), ("coalition", "party", "alliance"), .44, .25, .15),
        GoalTemplate("restore_deterrence", ("strategic_direction", "security", "responsibility"), ("attack", "deterrence", "security"), .45, .45, .05, ("security", "crisis")),
        GoalTemplate("avoid_escalation", ("unity", "political_stability", "responsibility"), ("crisis", "escalation", "alliance"), .42, .30, .20, ("security", "crisis")),
        GoalTemplate("verify_reality", ("organization_success", "responsibility", "implementation"), ("uncertain", "intelligence", "votes"), .36, .10, .70),
    )
    strategies = (
        StrategyTemplate("direct_control", "issue a binding direction", ("legislative", "party", "coalition", "crisis"), ("preserve_authority", "deliver_policy", "secure_organization"), "institutionalize", ("authority", "agency", "organization"), ("direction", "organization"), ("formal_process", "public_pressure"), {"formal_power": .55}, instrumental_impacts={"decision_speed": .75, "coordination": .45}, substantive_impacts={"autonomy": -.35, "deliberation": -.25}, necessity_frame_alignment=.70, base_upside=.72, base_downside=.52, base_effort=.62, base_control_restoration=.82),
        StrategyTemplate("private_negotiation", "open a private bargaining channel", ("legislative", "party", "coalition", "security", "crisis"), ("preserve_unity", "deliver_policy", "avoid_escalation", "verify_reality"), "negotiate", ("negotiation", "organization", "unity"), ("process", "coalition"), ("behind_scenes", "formal_process"), {"network_capital": .35}, instrumental_impacts={"agreement": .65, "decision_speed": .15}, substantive_impacts={"autonomy": .20, "deliberation": .30}, base_upside=.66, base_downside=.28, base_effort=.50, base_control_restoration=.45),
        StrategyTemplate("institutional_consultation", "move the conflict into an institution", ("legislative", "party", "coalition", "security", "crisis"), ("secure_organization", "preserve_unity", "verify_reality", "avoid_escalation"), "institutionalize", ("organization", "responsibility", "majority"), ("organization", "process"), ("formal_process", "behind_scenes"), {"organization_base": .30}, instrumental_impacts={"coordination": .70, "decision_speed": -.10}, substantive_impacts={"autonomy": .35, "deliberation": .55}, base_upside=.60, base_downside=.22, base_effort=.58, base_control_restoration=.62),
        StrategyTemplate("public_signal", "shape the public interpretation", ("legislative", "party", "coalition", "security", "crisis", "electoral"), ("preserve_authority", "restore_deterrence", "preserve_unity"), "reframe", ("public_signal", "strategic_direction", "agency"), ("direction",), ("public_pressure", "measured_statement"), {"public_capital": .25}, instrumental_impacts={"agenda_control": .68, "agreement": -.12}, substantive_impacts={"transparency": .45, "escalation_risk": -.28}, base_upside=.64, base_downside=.46, base_effort=.40, base_control_restoration=.55),
        StrategyTemplate("limited_countermove", "take a bounded material countermove", ("security", "crisis", "coalition"), ("restore_deterrence", "preserve_authority", "deliver_policy"), "attack", ("deterrence", "agency", "authority"), ("direction", "execution"), ("formal_process", "public_pressure"), {"formal_power": .55, "organization_base": .35}, instrumental_impacts={"deterrence": .75, "agreement": -.35}, substantive_impacts={"security": .50, "escalation_risk": -.55}, institutional_deviation=.30, base_upside=.76, base_downside=.70, base_effort=.70, base_control_restoration=.78),
        StrategyTemplate("delay_verify", "delay commitment pending verification", ("legislative", "party", "coalition", "security", "crisis", "electoral"), ("verify_reality", "avoid_escalation", "secure_organization"), "avoid", ("verification", "future_option"), ("process",), ("verification_pause", "behind_scenes"), instrumental_impacts={"information_quality": .85, "decision_speed": -.65}, substantive_impacts={"deliberation": .45, "responsibility": .30}, institutional_deviation=.12, base_upside=.40, base_downside=.34, base_effort=.26, base_control_restoration=.20),
    )
    styles = (
        ExecutionStyleTemplate("behind_scenes", "private coordination", ("private_negotiation", "institutional_consultation", "delay_verify"), "negotiate", ("process", "coalition"), .12, .92, .82, .85, 1.05, "repair"),
        ExecutionStyleTemplate("formal_process", "formal institutional procedure", ("direct_control", "private_negotiation", "institutional_consultation", "limited_countermove"), "institutionalize", ("organization", "process"), .38, 1.05, .92, .82, 1.03, "boundary"),
        ExecutionStyleTemplate("public_pressure", "visible public pressure", ("direct_control", "public_signal", "limited_countermove"), "attack", ("direction",), .92, .95, 1.24, 1.05, .94, "boundary"),
        ExecutionStyleTemplate("measured_statement", "measured public statement", ("public_signal",), "reframe", ("direction", "coalition"), .62, .78, .86, .90, 1.02, "neutral"),
        ExecutionStyleTemplate("verification_pause", "explicit verification pause", ("delay_verify",), "avoid", ("process",), .30, .72, .88, .68, 1.06, "neutral"),
    )
    return ActionLibrary(perceptions, goals, strategies, styles)


class DecisionSpaceGenerator:
    def __init__(
        self,
        library: ActionLibrary | None = None,
        *,
        max_actions: int = 12,
        minimum_goal_salience: float = 0.180,
        minimum_style_fit: float = 0.180,
    ) -> None:
        self.library = library or default_action_library()
        self.max_actions = max(1, max_actions)
        self.minimum_goal_salience = clamp(minimum_goal_salience)
        self.minimum_style_fit = clamp(minimum_style_fit)

    def _perceptions(
        self,
        event: DecisionEvent,
        beliefs: BeliefState,
        card: PersonaCard,
        runtime: PersonaRuntime,
    ) -> tuple[PerceptionAssessment, ...]:
        mean_confidence = (
            sum(row.confidence for row in beliefs.beliefs.values()) / len(beliefs.beliefs)
            if beliefs.beliefs else .500
        )
        authority_preference = card.dna.control_preferences.get("direction", .500)
        signal_rows = []
        for key, direction in event.signal_variables.items():
            belief = beliefs.beliefs.get(key)
            if belief is None or float(direction) == 0.0:
                continue
            normalized = clamp(belief.estimate / 100.0)
            aligned = normalized if float(direction) > 0.0 else 1.0 - normalized
            signal_rows.append((aligned, abs(float(direction))))
        perceived_signal = (
            sum(value * weight for value, weight in signal_rows)
            / sum(weight for _, weight in signal_rows)
            if signal_rows else .500
        )
        source_trust = None
        if event.source_actor:
            source_trust = runtime.relationships.get(event.source_actor)
            source_trust = source_trust.trust if source_trust else .500
        raw: dict[str, float] = {}
        diagnostics: dict[str, tuple[float, float, float | None]] = {}
        eligible: list[PerceptionTemplate] = []
        for template in self.library.perceptions:
            if template.domains and event.domain not in template.domains:
                continue
            eligible.append(template)
            cue_fit = overlap(template.cue_tags, event.tags)
            memory = max(
                (overlap(item.tags, template.interpretation_tags + event.tags) * item.severity * (.5 + .5 * item.unresolved) for item in runtime.memories),
                default=0.0,
            )
            ambiguity_fit = .35 + .65 * (1.0 - abs(event.ambiguity - template.ambiguity_affinity))
            authority = template.authority_threat_affinity * authority_preference * runtime.state.pressure
            signal_fit = perceived_signal * (.20 + .80 * template.authority_threat_affinity)
            uncertainty_fit = (1.0 - mean_confidence) * template.ambiguity_affinity
            trust_factor = .75 + .25 * (source_trust if source_trust is not None else .500)
            score = max(
                .001,
                template.base_weight * ambiguity_fit * trust_factor
                + .42 * cue_fit
                + .24 * memory
                + .18 * authority
                + .16 * signal_fit
                + .20 * uncertainty_fit,
            )
            raw[template.key] = score
            diagnostics[template.key] = (cue_fit, memory, source_trust)
        weights = _normalize(raw)
        rows = [
            PerceptionAssessment(
                template.key,
                template.label,
                weights[template.key],
                round(mean_confidence * (1.0 - .35 * event.ambiguity), 3),
                round(diagnostics[template.key][0], 3),
                round(perceived_signal, 3),
                round(diagnostics[template.key][1], 3),
                None if diagnostics[template.key][2] is None else round(diagnostics[template.key][2], 3),
                template.interpretation_tags,
            )
            for template in eligible
        ]
        return tuple(sorted(rows, key=lambda row: (-row.weight, row.key)))

    def _goals(
        self,
        event: DecisionEvent,
        card: PersonaCard,
        runtime: PersonaRuntime,
        current_goals: Mapping[str, float],
    ) -> tuple[GoalAssessment, ...]:
        values = {row.key: row.weight for row in card.dna.value_hierarchy}
        rows: list[GoalAssessment] = []
        for template in self.library.goals:
            if template.domains and event.domain not in template.domains:
                continue
            value_fit = max((values.get(key, 0.0) for key in template.value_keys), default=0.0)
            event_fit = overlap(template.cue_tags, event.tags)
            state_modifier = (
                template.pressure_sensitivity * runtime.state.pressure
                + template.confidence_sensitivity * (1.0 - runtime.state.confidence)
            )
            live = float(current_goals.get(template.key, 0.0))
            salience = clamp(template.base_salience + .38 * value_fit + .25 * event_fit + .20 * state_modifier + .30 * live)
            if salience >= self.minimum_goal_salience:
                rows.append(GoalAssessment(template.key, round(salience, 3), round(value_fit, 3), round(event_fit, 3), round(state_modifier, 3)))
        return tuple(sorted(rows, key=lambda row: (-row.salience, row.key)))

    @staticmethod
    def _outcomes(
        key: str,
        base: PoliticalAction,
        feasibility: float,
        uncertainty: float,
        model: StrategyEffectModel,
    ) -> tuple[OutcomeBranch, ...]:
        success = clamp(feasibility * (1.0 - .45 * uncertainty))
        failure = clamp((1.0 - feasibility) * (.55 + .45 * uncertainty))
        partial = max(0.0, 1.0 - success - failure)
        weights = _normalize({"success": success, "partial_success": partial, "failure": failure})
        multipliers = {"success": 1.0, "partial_success": .45, "failure": 0.0}
        levels = {"success": .900, "partial_success": .500, "failure": .100}
        labels = {
            "success": "intended operational effect substantially realized",
            "partial_success": "mixed implementation and contested feedback",
            "failure": "intended effect not realized; later feedback must carry backlash",
        }
        result = []
        for branch in ("success", "partial_success", "failure"):
            effects = model.outcome_effect_overrides.get(branch)
            if effects is None:
                effects = _scale_effects(base.effects, multipliers[branch])
            world = replace(
                base,
                key=key,
                effects=effects,
                capital_delta={k: v * multipliers[branch] for k, v in base.capital_delta.items()},
                pressure_delta={k: v * multipliers[branch] for k, v in base.pressure_delta.items()},
            )
            result.append(OutcomeBranch(branch, weights[branch], levels[branch], world, labels[branch]))
        return tuple(result)

    def generate(
        self,
        actor: str,
        event: DecisionEvent,
        beliefs: BeliefState,
        card: PersonaCard,
        runtime: PersonaRuntime,
        resources: Mapping[str, float],
        current_goals: Mapping[str, float] | None = None,
    ) -> GeneratedDecisionSpace:
        current_goals = current_goals or {}
        perceptions = self._perceptions(event, beliefs, card, runtime)
        goals = self._goals(event, card, runtime, current_goals)
        dominant = perceptions[0]
        active_goal_keys = {row.key for row in goals}
        styles = {row.key: row for row in self.library.styles}
        candidates: list[GeneratedAction] = []
        rejected: list[dict[str, Any]] = []
        for strategy in self.library.strategies:
            if event.domain not in strategy.domains:
                continue
            if event.allowed_strategy_keys and strategy.key not in event.allowed_strategy_keys:
                continue
            if strategy.key not in event.effect_models:
                rejected.append({"strategy": strategy.key, "reason": "missing_event_effect_model"})
                continue
            served_goals = [row for row in goals if row.key in strategy.goal_keys]
            if not served_goals:
                rejected.append({"strategy": strategy.key, "reason": "no_active_goal"})
                continue
            effect_model = event.effect_models[strategy.key]
            for style_key in strategy.style_keys:
                style = styles.get(style_key)
                if style is None or strategy.key not in style.compatible_strategies:
                    continue
                strategy_pref = card.dna.conflict_strategies.get(style.conflict_strategy, .0)
                control_pref = max(
                    (card.dna.control_preferences.get(key, .0) for key in style.control_domains + strategy.control_domains),
                    default=.0,
                )
                style_fit = .55 * strategy_pref + .45 * control_pref
                if style_fit < self.minimum_style_fit:
                    rejected.append({"strategy": strategy.key, "style": style.key, "reason": "style_fit_below_threshold", "style_fit": round(style_fit, 3)})
                    continue
                feasibility = clamp(effect_model.base_feasibility * style.feasibility_multiplier)
                uncertainty_level = clamp(event.ambiguity * style.uncertainty_multiplier)
                action_key = f"{event.key}__{strategy.key}__{style.key}"
                world = PoliticalAction(
                    action_key,
                    _scale_effects(effect_model.effects, .45 + .55 * style.feasibility_multiplier),
                    uncertainty=effect_model.uncertainty,
                    capital_delta=effect_model.capital_delta,
                    pressure_delta=effect_model.pressure_delta,
                    irreversibility=effect_model.irreversibility,
                    feasibility=feasibility,
                    next_node=effect_model.next_node,
                    tags=event.tags + (f"strategy:{strategy.key}", f"style:{style.key}"),
                )
                goal_impacts = {row.key: min(1.0, .35 + .65 * row.salience) for row in served_goals}
                value_impacts = dict(strategy.value_impacts)
                goal_templates = {row.key: row for row in self.library.goals}
                for goal in served_goals:
                    for value_key in goal_templates[goal.key].value_keys:
                        value_impacts.setdefault(value_key, min(.85, .35 + .45 * goal.salience))
                choice = ActionOption(
                    action_key,
                    goal_impacts=goal_impacts,
                    value_impacts=value_impacts,
                    required_resources=strategy.required_resources,
                    upside=clamp(strategy.base_upside * (.75 + .25 * style_fit)),
                    downside=clamp(strategy.base_downside * style.downside_multiplier),
                    uncertainty=uncertainty_level,
                    irreversibility=effect_model.irreversibility,
                    effort=clamp(strategy.base_effort * style.effort_multiplier),
                    visibility=style.visibility,
                    information_confidence=dominant.information_confidence,
                    control_domains=tuple(dict.fromkeys(strategy.control_domains + style.control_domains)),
                    restores_control=clamp(strategy.base_control_restoration * (.75 + .25 * control_pref)),
                    conflict_strategy=style.conflict_strategy,
                    identity_tags=tuple(dict.fromkeys(strategy.identity_tags + dominant.interpretation_tags)),
                    event_tags=event.tags,
                    risk_tags=("systemic_crisis",) if event.severity >= .800 else (),
                    target_actor=event.target_actor or event.source_actor,
                    objective_feasibility=feasibility,
                    instrumental_impacts=strategy.instrumental_impacts,
                    substantive_impacts=strategy.substantive_impacts,
                    institutional_deviation=strategy.institutional_deviation,
                    necessity_frame_alignment=strategy.necessity_frame_alignment,
                    required_offices=strategy.required_offices,
                    required_institutional_permissions=strategy.required_permissions,
                    organizational_carrier_requirements=strategy.required_resources,
                    relationship_posture=style.relationship_posture,
                )
                goal_strength = sum(row.salience for row in served_goals) / len(served_goals)
                generation_score = round(.30 * dominant.weight + .30 * goal_strength + .25 * style_fit + .15 * feasibility, 3)
                outcomes = self._outcomes(action_key, world, feasibility, uncertainty_level, effect_model)
                candidates.append(GeneratedAction(WorldAction(world, choice), DecisionPath(dominant.key, tuple(row.key for row in served_goals), strategy.key, style.key), generation_score, outcomes))

        # Preserve strategy diversity before filling remaining high-scoring slots.
        ordered = sorted(candidates, key=lambda row: (-row.generation_score, row.world_action.choice.key))
        selected: list[GeneratedAction] = []
        represented: set[str] = set()
        for row in ordered:
            if row.path.strategy not in represented:
                selected.append(row)
                represented.add(row.path.strategy)
        for row in ordered:
            if row not in selected and len(selected) < self.max_actions:
                selected.append(row)
        selected = selected[: self.max_actions]
        if not selected:
            raise RuntimeError(f"Decision generator produced no actions for {actor} at {event.key}")
        return GeneratedDecisionSpace(event, actor, perceptions, goals, tuple(selected), tuple(rejected))


@dataclass(frozen=True)
class ResolvedOutcome:
    action: str
    branch: str
    conditional_weight: float
    success_level: float
    world_action: PoliticalAction
    stochastic: bool

    def payload(self) -> dict:
        return quantize3({
            "action": self.action,
            "branch": self.branch,
            "conditional_weight": self.conditional_weight,
            "success_level": self.success_level,
            "stochastic": self.stochastic,
        })


class OutcomeResolver:
    """Resolve consequences; this is the only random stage in the generator."""

    def __init__(self, seed: int = 0, stochastic: bool = True) -> None:
        self.rng = random.Random(seed)
        self.stochastic = stochastic

    def resolve(self, action: GeneratedAction) -> ResolvedOutcome:
        if self.stochastic:
            draw = self.rng.random()
            cumulative = 0.0
            selected = action.outcome_branches[-1]
            for row in action.outcome_branches:
                cumulative += row.conditional_weight
                if draw <= cumulative + 1e-12:
                    selected = row
                    break
        else:
            selected = max(action.outcome_branches, key=lambda row: row.conditional_weight)
        return ResolvedOutcome(
            action.world_action.choice.key,
            selected.key,
            selected.conditional_weight,
            selected.success_level,
            selected.world_action,
            self.stochastic,
        )

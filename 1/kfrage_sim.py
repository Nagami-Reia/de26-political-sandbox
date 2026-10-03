#!/usr/bin/env python3
"""Retrospective process calibration for the 2024 CDU/CSU K-Frage.

This is a small, auditable mechanism model. It is not an election forecast and its
Monte Carlo frequencies are not real-world probabilities. Randomness represents
unobserved information, imperfect perception, and negotiation contingencies only.

The observed 16/17 September outcome appears only in `compare_with_observed()`.
Decision functions never read it.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional

if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

try:
    from kfrage_model.personality_api import (
        DecisionContext,
        PersonalityPolicy,
        default_personality_policies,
        load_policy,
    )
except ModuleNotFoundError:  # Supports `python kfrage_model/kfrage_sim.py`.
    from personality_api import (  # type: ignore
        DecisionContext,
        PersonalityPolicy,
        default_personality_policies,
        load_policy,
    )


DIMENSIONS = (
    "formal_office_default",
    "landesverband_hausmacht",
    "fraktion",
    "party_apparatus",
    "public_visibility",
    "union_acceptability",
    "future_option_value",
)
DEFAULT_ENVIRONMENT_PATH = Path(__file__).with_name("environment.json")


def clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class Resources:
    formal_office_default: float
    landesverband_hausmacht: float
    fraktion: float
    party_apparatus: float
    public_visibility: float
    union_acceptability: float
    future_option_value: float

    def adjust(self, **changes: float) -> None:
        for name, delta in changes.items():
            setattr(self, name, clamp(getattr(self, name) + delta))

    def weighted(self, weights: Mapping[str, float]) -> float:
        denom = sum(weights.values())
        return sum(getattr(self, k) * v for k, v in weights.items()) / denom


@dataclass
class Node:
    name: str
    kind: str
    alignment: str
    signal_strength: float
    visibility: float


@dataclass
class Event:
    step: int
    node: str
    stage: str
    information_update: Dict[str, object]
    perceived_resource_state: Dict[str, object]
    rule: str
    utilities: Dict[str, float]
    action: str
    redistribution: Dict[str, object]
    next_node: str
    policy_id: str = "environment"


@dataclass
class Scenario:
    name: str = "baseline"
    wuest_control_weight: float = 1.00
    merz_default_multiplier: float = 1.00
    soeder_cdu_bridgehead_bonus: float = 0.00
    fraktion_alignment: str = "Merz"
    fraktion_strength: float = 0.82
    perception_sigma: float = 0.00
    contingency_sigma: float = 0.00
    seed: int = 20240917


@dataclass
class State:
    resources: Dict[str, Resources]
    nodes: Dict[str, Node]
    cdu_bridgehead_soeder: float
    unity_cost_memory_2021: float
    private_bargain: float
    events: List[Event] = field(default_factory=list)
    actions: Dict[str, str] = field(default_factory=dict)
    closure_candidate: Optional[str] = None


def load_environment_config(path: Path = DEFAULT_ENVIRONMENT_PATH) -> Dict[str, object]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if tuple(config["resource_dimensions"]) != DIMENSIONS:
        raise ValueError("Environment resource dimensions do not match the engine schema")
    allowed = set(config["allowed_timeline_handlers"])
    requested = {item["handler"] for item in config["timeline"]}
    if not requested <= allowed:
        raise ValueError(f"Environment requests unknown handlers: {sorted(requested - allowed)}")
    return config


def initial_state(s: Scenario, rng: random.Random, environment: Mapping[str, object]) -> State:
    """Initial encodings are documented in assumptions.json and source_notes.md."""
    actor_data = copy.deepcopy(environment["actors"])
    actor_data["Merz"]["formal_office_default"] = clamp(
        actor_data["Merz"]["formal_office_default"] * s.merz_default_multiplier
    )
    resources = {name: Resources(**values) for name, values in actor_data.items()}
    nodes = {key: Node(**values) for key, values in environment["nodes"].items()}
    nodes["Bundestagsfraktion"].alignment = s.fraktion_alignment
    nodes["Bundestagsfraktion"].signal_strength = s.fraktion_strength
    globals_ = environment["global_constraints"]
    private_bargain = rng.gauss(0.0, s.contingency_sigma)
    return State(
        resources=resources,
        nodes=nodes,
        cdu_bridgehead_soeder=clamp(float(globals_["cdu_bridgehead_soeder"]) + s.soeder_cdu_bridgehead_bonus),
        unity_cost_memory_2021=float(globals_["unity_cost_memory_2021"]),
        private_bargain=private_bargain,
    )


class Simulation:
    def __init__(
        self, scenario: Scenario,
        policies: Optional[Mapping[str, PersonalityPolicy]] = None,
        environment_config: Optional[Mapping[str, object]] = None,
    ):
        self.scenario = scenario
        self.rng = random.Random(scenario.seed)
        self.environment_config = copy.deepcopy(
            dict(environment_config) if environment_config is not None else load_environment_config()
        )
        self.state = initial_state(scenario, self.rng, self.environment_config)
        self.policies = default_personality_policies()
        if policies:
            self.policies.update(copy.deepcopy(dict(policies)))
        for actor in ("Merz", "Wuest", "Soeder"):
            if actor not in self.policies:
                raise ValueError(f"Missing personality policy for {actor}")
            declared_actor = self.policies[actor].actor
            if declared_actor not in (actor, "*"):
                raise ValueError(f"Policy {self.policies[actor].policy_id} belongs to {declared_actor}, not {actor}")

    def perceive(self, value: float) -> float:
        return clamp(value + self.rng.gauss(0.0, self.scenario.perception_sigma))

    def add_event(
        self, node: str, stage: str, info: Dict[str, object], perceived: Dict[str, object],
        rule: str, utilities: Dict[str, float], action: str,
        redistribution: Dict[str, object], next_node: str, policy_id: str = "environment",
    ) -> None:
        self.state.events.append(Event(
            len(self.state.events) + 1, node, stage, info, perceived, rule,
            {k: round(v, 4) for k, v in utilities.items()}, action,
            redistribution, next_node, policy_id,
        ))
        self.state.actions[node] = action

    def decide(self, actor: str, context: DecisionContext):
        policy = self.policies[actor]
        decision = policy.decide(context)
        if decision.action not in context.allowed_actions:
            raise ValueError(
                f"{policy.policy_id} chose {decision.action!r}; allowed={context.allowed_actions}"
            )
        return decision

    def organizational_support(self, candidate: str) -> float:
        visible = [n for n in self.state.nodes.values() if n.alignment == candidate]
        if not visible:
            return 0.0
        return sum(n.signal_strength * n.visibility for n in visible) / 3.4

    def candidate_viability(self, candidate: str) -> float:
        r = self.state.resources[candidate]
        weights = {
            "formal_office_default": 1.45,
            "landesverband_hausmacht": 1.00,
            "fraktion": 1.25,
            "party_apparatus": 1.00,
            "public_visibility": 0.60,
            "union_acceptability": 1.25,
            "future_option_value": 0.15,
        }
        base = r.weighted(weights)
        support = self.organizational_support(candidate)
        bridge = self.state.cdu_bridgehead_soeder if candidate == "Soeder" else 0.0
        return clamp(0.78 * base + 0.16 * support + 0.24 * bridge)

    def merz_waits_on_default(self) -> None:
        r = self.state.resources["Merz"]
        default = self.perceive(r.formal_office_default)
        backing = self.perceive((r.fraktion + r.party_apparatus) / 2)
        agency = 0.89
        decision = self.decide("Merz", DecisionContext(
            actor="Merz",
            stage="preclosure_positioning",
            allowed_actions=("hold_default_and_bilateral_channel", "declare_publicly"),
            features={"default": default, "backing": backing, "agency": agency,
                      "unity_cost": self.state.unity_cost_memory_2021},
            visible_world={"offices": ["CDU chair", "fraktion chair"],
                           "unknown": ["full private preferences of Landeschefs"]},
        ))
        action = decision.action
        if action == "declare_publicly":
            r.adjust(public_visibility=0.08, union_acceptability=-0.04)
        self.add_event(
            "Merz", "information update -> threshold logic",
            {"known": ["CDU chair", "fraktion chair", "agreed late-summer process"],
             "unknown": ["full private preferences of Landeschefs"]},
            {"default": round(default, 3), "party_and_fraktion_backing": round(backing, 3)},
            decision.rule, dict(decision.utilities), action,
            {"resource_change": "none" if action.startswith("hold") else "visibility up; unity acceptance slightly down"},
            "Soeder", self.policies["Merz"].policy_id,
        )

    def soeder_signal(self) -> None:
        r = self.state.resources["Soeder"]
        visibility = self.perceive(r.public_visibility)
        apparatus = self.perceive(r.party_apparatus)
        bridge = self.perceive(self.state.cdu_bridgehead_soeder)
        decision = self.decide("Soeder", DecisionContext(
            actor="Soeder",
            stage="availability_signal",
            allowed_actions=("signal_availability_conditioned_on_CDU_call", "stay_quiet"),
            features={"visibility": visibility, "apparatus": apparatus, "bridgehead": bridge,
                      "unity_cost": self.state.unity_cost_memory_2021},
            visible_world={"constraint": "a CSU candidate needs meaningful CDU demand"},
        ))
        action = decision.action
        if action.startswith("signal"):
            r.adjust(public_visibility=0.05, union_acceptability=-0.01)
            self.state.cdu_bridgehead_soeder = clamp(self.state.cdu_bridgehead_soeder + 0.035)
        self.add_event(
            "Soeder", "information update -> signal choice",
            {"known": ["strong CSU apparatus", "high public visibility", "a CSU candidate needs meaningful CDU demand"],
             "evidence_limit": "No private motive is inferred."},
            {"visibility": round(visibility, 3), "apparatus": round(apparatus, 3), "CDU_bridgehead": round(bridge, 3)},
            decision.rule, dict(decision.utilities), action,
            {"Soeder.public_visibility": "+0.05" if action.startswith("signal") else "+0.00",
             "CDU_bridgehead": "+0.035" if action.startswith("signal") else "+0.00"},
            "Rhein/Hagel", self.policies["Soeder"].policy_id,
        )

    def landeschef_signals(self) -> None:
        merz_v = self.perceive(self.candidate_viability("Merz"))
        soeder_v = self.perceive(self.candidate_viability("Soeder"))
        default_norm = self.perceive(self.state.resources["Merz"].formal_office_default)
        # Minimal role logic, not rich personality models.
        rhein_merz = clamp(0.50 * merz_v + 0.30 * default_norm + 0.20 * self.state.unity_cost_memory_2021)
        rhein_wait = clamp(0.47 + 0.20 * soeder_v)
        rhein_action = "signal_Merz" if rhein_merz >= rhein_wait else "withhold_preference"
        if rhein_action == "signal_Merz":
            self.state.nodes["Rhein"].alignment = "Merz"

        hagel_merz = clamp(0.46 * merz_v + 0.38 * default_norm + 0.16 * self.state.unity_cost_memory_2021)
        hagel_open = clamp(0.44 + 0.27 * soeder_v)
        hagel_action = "affirm_CDU_first_access" if hagel_merz >= hagel_open else "keep_door_open"
        if hagel_action == "affirm_CDU_first_access":
            self.state.nodes["Hagel"].alignment = "Merz"

        if rhein_action == "signal_Merz":
            self.state.resources["Merz"].adjust(landesverband_hausmacht=0.035, union_acceptability=0.025)
        if hagel_action == "affirm_CDU_first_access":
            self.state.resources["Merz"].adjust(landesverband_hausmacht=0.04, union_acceptability=0.025)
            self.state.cdu_bridgehead_soeder = clamp(self.state.cdu_bridgehead_soeder - 0.025)
        self.add_event(
            "Rhein/Hagel", "distributed elite signals",
            {"known": ["Merz office default", "Söder public availability", "2021 coordination cost"],
             "model_scope": "thin organizational-node rules only"},
            {"Merz_viability": round(merz_v, 3), "Soeder_viability": round(soeder_v, 3), "default_norm": round(default_norm, 3)},
            "Rhein weights incumbent viability/unity; Hagel additionally weights the CDU chair's first-access norm.",
            {"Rhein:Merz": rhein_merz, "Rhein:wait": rhein_wait,
             "Hagel:Merz": hagel_merz, "Hagel:open": hagel_open},
            f"Rhein={rhein_action}; Hagel={hagel_action}",
            {"Merz.Landesverband/acceptability": "conditional increase", "Soeder.CDU_bridgehead": "conditional decrease"},
            "Wuest",
        )

    def wuest_decision(self) -> None:
        merz_v = self.perceive(self.candidate_viability("Merz"))
        wuest_v = self.perceive(self.candidate_viability("Wuest"))
        soeder_v = self.perceive(self.candidate_viability("Soeder"))
        opening = clamp(wuest_v - 0.54 * merz_v + 0.12 * (1 - soeder_v))
        control = clamp(0.79 - 0.62 * merz_v + 0.20 * wuest_v)
        acceptance = clamp(self.state.resources["Wuest"].union_acceptability - 0.38 * self.state.unity_cost_memory_2021)
        timing = clamp(0.45 + 0.40 * opening)
        ambition = 0.91

        # Endorse the most viable CDU candidate, not a named historical winner.
        cdu_target = max(("Merz", "Wuest"), key=self.candidate_viability)
        target_v = self.perceive(self.candidate_viability(cdu_target))
        endorse_action = f"withdraw_and_endorse_{cdu_target}"
        decision = self.decide("Wuest", DecisionContext(
            actor="Wuest",
            stage="candidacy_choice",
            allowed_actions=("challenge", endorse_action, "remain_ambiguous"),
            features={
                "ambition": ambition, "control": control, "acceptance": acceptance, "timing": timing,
                "endorse_action": endorse_action,
                "endorse_ambition": 0.58 + 0.22 * self.state.resources["Wuest"].future_option_value,
                "endorse_control": clamp(0.76 + 0.22 * target_v),
                "endorse_acceptance": clamp(0.72 + 0.24 * self.state.unity_cost_memory_2021),
                "endorse_timing": clamp(0.63 + 0.28 * target_v),
            },
            visible_world={"viability": {"Merz": merz_v, "Wuest": wuest_v, "Soeder": soeder_v},
                           "unknown": ["content of Merz-Wuest talks", "private promises"]},
            parameters={"control_weight": self.scenario.wuest_control_weight},
        ))
        action = decision.action
        if action == "challenge":
            self.state.nodes["NRW_CDU"].alignment = "Wuest"
            self.state.resources["Wuest"].adjust(public_visibility=0.12, future_option_value=-0.26, union_acceptability=-0.08)
            self.state.resources["Merz"].adjust(union_acceptability=-0.09, landesverband_hausmacht=-0.10)
        elif action.startswith("withdraw_and_endorse_"):
            target = action.removeprefix("withdraw_and_endorse_")
            self.state.nodes["NRW_CDU"].alignment = target
            self.state.resources[target].adjust(landesverband_hausmacht=0.17, union_acceptability=0.10, party_apparatus=0.05)
            self.state.resources["Wuest"].adjust(future_option_value=0.025, union_acceptability=0.035)
            self.state.cdu_bridgehead_soeder = clamp(self.state.cdu_bridgehead_soeder - 0.16)
        self.add_event(
            "Wuest", "information update -> perceived state -> conjunctive threshold",
            {"known": ["NRW organizational resource", "Merz office/fraktion default", "Söder requires CDU bridgehead", "2021 unity cost"],
             "unknown": ["content of Merz-Wuest talks", "private promises or succession bargains"]},
            {"Merz_viability": round(merz_v, 3), "Wuest_viability": round(wuest_v, 3),
             "Soeder_viability": round(soeder_v, 3), "opening": round(opening, 3),
             "control_of_challenge": round(control, 3), "acceptance_of_challenge": round(acceptance, 3),
             "timing": round(timing, 3)},
            decision.rule, dict(decision.utilities), action,
            {"NRW_CDU.alignment": self.state.nodes["NRW_CDU"].alignment,
             "Soeder.CDU_bridgehead": round(self.state.cdu_bridgehead_soeder, 3)},
            "Frei", self.policies["Wuest"].policy_id,
        )

    def frei_response(self) -> None:
        w_action = self.state.actions["Wuest"]
        merz_alignment = 1.0 if self.state.nodes["NRW_CDU"].alignment == "Merz" else 0.0
        organization = 0.88
        loyalty = 0.90
        public_validation = clamp(0.42 * organization + 0.35 * loyalty + 0.23 * merz_alignment)
        silence = clamp(0.52 + 0.18 * (1 - merz_alignment))
        action = "validate_unity_signal" if public_validation >= silence else "remain_internal"
        if action == "validate_unity_signal":
            self.state.nodes["Frei"].alignment = "Merz"
            self.state.resources["Merz"].adjust(fraktion=0.035, union_acceptability=0.025)
        self.add_event(
            "Frei", "organizational response",
            {"observed_input": w_action, "role": "first parliamentary managing director"},
            {"organizational_closure_value": organization, "personal_institutional_loyalty": loyalty,
             "NRW_alignment_with_Merz": merz_alignment},
            "Gestaltung through Organisation plus personal/institutional loyalty: explain and stabilize a legible party signal.",
            {"validate": public_validation, "silence": silence}, action,
            {"Merz.fraktion/acceptability": "small increase" if action.startswith("validate") else "none"},
            "Linnemann",
        )

    def linnemann_implementation(self) -> None:
        candidates = ("Merz", "Wuest", "Soeder")
        viability = {c: self.perceive(self.candidate_viability(c)) for c in candidates}
        leader = max(viability, key=viability.get)
        clarity = clamp(viability[leader] - sorted(viability.values())[-2] + 0.52)
        implement = clamp(0.58 + 0.35 * clarity)
        wait = clamp(0.61 - 0.15 * clarity)
        action = f"organize_CDU_behind_{leader}" if implement >= wait else "seek_more_clarity"
        if action.startswith("organize_CDU_behind_"):
            self.state.nodes["Linnemann"].alignment = leader
            self.state.resources[leader].adjust(party_apparatus=0.045, union_acceptability=0.025)
        self.add_event(
            "Linnemann", "implementation response",
            {"known": "current resource and endorsement configuration", "unknown": "private bargaining content"},
            {"viability": {k: round(v, 3) for k, v in viability.items()}, "clarity": round(clarity, 3)},
            "Wirksamkeit/implementation: when a workable leader is sufficiently clear, convert the signal into party organization.",
            {"implement": implement, "wait": wait}, action,
            {"party_apparatus": f"+0.045 to {leader}" if action.startswith("organize") else "none"},
            "Soeder closure decision",
        )

    def soeder_closure(self) -> None:
        merz_v = self.perceive(self.candidate_viability("Merz"))
        soeder_v = self.perceive(self.candidate_viability("Soeder"))
        bridge = self.perceive(self.state.cdu_bridgehead_soeder)
        bargain = self.state.private_bargain
        decision = self.decide("Soeder", DecisionContext(
            actor="Soeder",
            stage="bilateral_closure",
            allowed_actions=("continue_contest", "bilateral_close_Merz", "propose_Soeder"),
            features={
                "merz_viability": merz_v, "soeder_viability": soeder_v, "bridgehead": bridge,
                "apparatus": self.state.resources["Soeder"].party_apparatus,
                "unity_cost": self.state.unity_cost_memory_2021,
                "future_option": self.state.resources["Soeder"].future_option_value,
                "private_bargain_contingency": bargain,
            },
            visible_world={"NRW_alignment": self.state.nodes["NRW_CDU"].alignment,
                           "CDU_signals": {k: self.state.nodes[k].alignment for k in ("Rhein", "Hagel", "Linnemann")}},
        ))
        action = decision.action
        if action == "bilateral_close_Merz":
            self.state.resources["Merz"].adjust(union_acceptability=0.11, party_apparatus=0.06)
            self.state.resources["Soeder"].adjust(future_option_value=0.03, union_acceptability=0.025)
        elif action == "propose_Soeder":
            self.state.resources["Soeder"].adjust(union_acceptability=0.05)
        self.add_event(
            "Soeder", "bridgehead check -> bilateral closure choice",
            {"known": ["CSU apparatus support", "CDU signals", "NRW alignment", "2021 coordination cost"],
             "unknown_black_box": "bilateral terms/assurances; modeled as bounded contingency only"},
            {"Merz_viability": round(merz_v, 3), "Soeder_viability": round(soeder_v, 3),
             "CDU_bridgehead": round(bridge, 3), "private_bargain_contingency": round(bargain, 3)},
            decision.rule, dict(decision.utilities), action,
            {"Merz.acceptability/apparatus": "increase" if action == "bilateral_close_Merz" else "none"},
            "Merz closure response", self.policies["Soeder"].policy_id,
        )

    def merz_closure(self) -> None:
        merz_v = self.perceive(self.candidate_viability("Merz"))
        soeder_action = self.state.actions["Soeder"]
        agency = 0.92
        decision = self.decide("Merz", DecisionContext(
            actor="Merz",
            stage="bilateral_closure",
            allowed_actions=("assert_candidacy_in_bilateral", "delay_or_seek_alternative"),
            features={"merz_viability": merz_v, "agency": agency, "soeder_action": soeder_action},
            visible_world={"fraktion": self.state.nodes["Bundestagsfraktion"].alignment,
                           "party_implementation": self.state.nodes["Linnemann"].alignment},
        ))
        action = decision.action
        risk_capacity = decision.diagnostics.get("conditional_risk_capacity", clamp(0.48 + 0.45 * merz_v))
        if action == "assert_candidacy_in_bilateral" and soeder_action == "bilateral_close_Merz":
            self.state.closure_candidate = "Merz"
            public = "joint_Merz_Soeder_closure"
        elif action == "assert_candidacy_in_bilateral" and soeder_action == "propose_Soeder":
            public = "open_leadership_contest"
        elif soeder_action == "propose_Soeder":
            self.state.closure_candidate = "Soeder"
            public = "joint_Soeder_proposal"
        else:
            public = "unresolved"
        self.add_event(
            "Merz", "conditional risk decision -> public form",
            {"known": ["own default", "fraktion and party backing", f"Söder action={soeder_action}"],
             "unknown": "exact negotiated division of roles"},
            {"Merz_viability": round(merz_v, 3), "agency_Gestaltung": agency, "conditional_risk_capacity": round(risk_capacity, 3)},
            decision.rule, dict(decision.utilities),
            f"{action}; public={public}",
            {"closure_candidate": self.state.closure_candidate},
            "Guenther and organizational synchronization", self.policies["Merz"].policy_id,
        )

    def synchronization(self) -> None:
        candidate = self.state.closure_candidate
        if candidate:
            consensus = self.perceive(self.candidate_viability(candidate))
            majority = clamp(0.55 + 0.39 * consensus)
            operative = 0.86
            endorse = clamp(0.46 * majority + 0.32 * operative + 0.22 * self.state.unity_cost_memory_2021)
            dissent = clamp(0.62 - 0.27 * majority)
            guenther_action = f"endorse_{candidate}_and_call_for_unity" if endorse >= dissent else "reserve_judgment"
            if guenther_action.startswith("endorse"):
                self.state.nodes["Guenther"].alignment = candidate
            for key in ("Bundestagsfraktion", "Linnemann", "Frei"):
                # Synchronize only if the closure candidate has a viable organizational majority.
                if consensus >= 0.61:
                    self.state.nodes[key].alignment = candidate
            if candidate == "Merz" and consensus >= 0.61:
                # CSU apparatus accepts the joint proposal while retaining distinct identity.
                self.state.nodes["CSU_apparatus"].alignment = "Joint_Merz"
            action = f"Guenther={guenther_action}; organizations synchronize around {candidate}"
            utilities = {"Guenther_endorse": endorse, "Guenther_reserve": dissent}
        else:
            consensus = 0.0
            action = "no synchronization; contest/unresolved state persists"
            utilities = {"synchronize": 0.0, "wait": 1.0}
        self.add_event(
            "Guenther + organizations", "post-closure synchronization",
            {"public_closure_candidate": candidate, "nodes": ["NRW-CDU", "Bundestagsfraktion", "CSU apparatus", "Frei", "Linnemann"]},
            {"consensus_strength": round(consensus, 3)},
            "Günther: Mehrheiten/consensus/operative responsibility. Organizations follow a viable joint closure, not a personality command.",
            utilities, action,
            {k: v.alignment for k, v in self.state.nodes.items()},
            "end",
        )

    def run(self) -> State:
        allowed = set(self.environment_config["allowed_timeline_handlers"])
        for item in self.environment_config["timeline"]:
            handler = item["handler"]
            if handler not in allowed or not hasattr(self, handler):
                raise ValueError(f"Unsafe or unknown environment handler: {handler}")
            getattr(self, handler)()
        return self.state


def classify_path(state: State) -> str:
    w = state.actions.get("Wuest", "")
    s = state.actions.get("Soeder", "")
    synced = state.nodes["Bundestagsfraktion"].alignment == state.closure_candidate if state.closure_candidate else False
    if w == "withdraw_and_endorse_Merz" and s == "bilateral_close_Merz" and state.closure_candidate == "Merz" and synced:
        return "historical_like_sequence"
    if w == "challenge":
        return "Wuest_challenge"
    if state.closure_candidate == "Soeder":
        return "Soeder_closure"
    if "continue_contest" in s or any("open_leadership_contest" in e.action for e in state.events):
        return "open_contest"
    if state.closure_candidate == "Merz":
        return "Merz_closure_other_route"
    return "unresolved_or_other"


def classify_path_blind(state: State) -> str:
    """Outcome-neutral labels; never reads or names the observed historical sequence."""
    wuest = state.actions.get("Wuest", "unknown")
    soeder = state.actions.get("Soeder", "unknown")
    closure = state.closure_candidate or "none"
    if wuest == "challenge":
        opening = "Wuest_challenges"
    elif wuest.startswith("withdraw_and_endorse_"):
        opening = "Wuest_reallocates_NRW"
    elif wuest == "remain_ambiguous":
        opening = "Wuest_holds_option"
    else:
        opening = "Wuest_other"
    if soeder == "continue_contest":
        resolution = "Union_contest_continues"
    elif soeder == "bilateral_close_Merz":
        resolution = "bilateral_closure_for_Merz"
    elif soeder == "propose_Soeder":
        resolution = "Soeder_proposal"
    else:
        resolution = "unresolved"
    return f"{opening}__{resolution}__closure_{closure}"


OBSERVED_COMPARATOR = {
    "Wuest": "withdraw_and_endorse_Merz",
    "Soeder": "bilateral_close_Merz",
    "closure_candidate": "Merz",
    "NRW_CDU": "Merz",
    "Bundestagsfraktion": "Merz",
    "CSU_apparatus": "Joint_Merz",
}


def compare_with_observed(state: State) -> Dict[str, object]:
    actual = {
        "Wuest": state.actions.get("Wuest"),
        "Soeder": state.actions.get("Soeder"),
        "closure_candidate": state.closure_candidate,
        "NRW_CDU": state.nodes["NRW_CDU"].alignment,
        "Bundestagsfraktion": state.nodes["Bundestagsfraktion"].alignment,
        "CSU_apparatus": state.nodes["CSU_apparatus"].alignment,
    }
    matches = {k: actual[k] == v for k, v in OBSERVED_COMPARATOR.items()}
    return {
        "observed_comparator_not_used_by_decisions": True,
        "expected": OBSERVED_COMPARATOR,
        "actual": actual,
        "matches": matches,
        "calibration_result": "PASS_natural_sequence_reproduced" if all(matches.values()) else "MODEL_ERROR_sequence_not_reproduced",
    }


def monte_carlo(
    base: Scenario, runs: int,
    policies: Optional[Mapping[str, PersonalityPolicy]] = None,
    environment_config: Optional[Mapping[str, object]] = None,
    blind: bool = False,
) -> Dict[str, object]:
    counts: Counter[str] = Counter()
    decision_counts: Dict[str, Counter[str]] = {}
    examples: Dict[str, int] = {}
    for i in range(runs):
        s = copy.deepcopy(base)
        s.seed = base.seed + i * 7919
        # Deliberately wide enough to expose nearby branches. These are not
        # estimates of polling error or personality volatility.
        s.perception_sigma = 0.13
        s.contingency_sigma = 0.11
        state = Simulation(s, policies=policies, environment_config=environment_config).run()
        path = classify_path_blind(state) if blind else classify_path(state)
        counts[path] += 1
        examples.setdefault(path, s.seed)
        for event in state.events:
            if event.policy_id == "environment":
                continue
            key = f"{event.node}::{event.stage}::{event.policy_id}"
            decision_counts.setdefault(key, Counter())[event.action] += 1
    return {
        "runs": runs,
        "interpretation_warning": "Simulation frequencies are path shares under model perturbations, not real-world election probabilities.",
        "counts": dict(sorted(counts.items())),
        "shares": {k: round(v / runs, 4) for k, v in sorted(counts.items())},
        "personality_stage_action_counts": {
            key: dict(sorted(values.items())) for key, values in sorted(decision_counts.items())
        },
        "personality_stage_action_shares": {
            key: {action: round(count / runs, 4) for action, count in sorted(values.items())}
            for key, values in sorted(decision_counts.items())
        },
        "example_seed_by_path": examples,
    }


def scenario_set() -> Dict[str, Scenario]:
    return {
        "baseline": Scenario(),
        "no_wuest_control": Scenario(name="no_wuest_control", wuest_control_weight=0.0),
        "no_merz_incumbent_advantage": Scenario(name="no_merz_incumbent_advantage", merz_default_multiplier=0.28),
        "stronger_soeder_CDU_bridgehead": Scenario(name="stronger_soeder_CDU_bridgehead", soeder_cdu_bridgehead_bonus=0.46),
        "fraktion_aligns_soeder": Scenario(name="fraktion_aligns_soeder", fraktion_alignment="Soeder", fraktion_strength=0.82),
        "fraktion_weakly_uncommitted": Scenario(name="fraktion_weakly_uncommitted", fraktion_alignment="Uncommitted", fraktion_strength=0.28),
    }


def state_payload(
    scenario: Scenario, state: State,
    policies: Optional[Mapping[str, PersonalityPolicy]] = None,
    environment_config: Optional[Mapping[str, object]] = None,
    blind: bool = False,
) -> Dict[str, object]:
    active = default_personality_policies()
    if policies:
        active.update(policies)
    payload = {
        "scenario": asdict(scenario),
        "environment_id": (environment_config or load_environment_config())["environment_id"],
        "blind_mode": blind,
        "active_personality_policies": {k: v.policy_id for k, v in active.items()},
        "initialization_note": "Numeric encodings operationalize source-backed ordinal relations; they are not politician ratings.",
        "events": [asdict(e) for e in state.events],
        "final_resources": {k: asdict(v) for k, v in state.resources.items()},
        "final_nodes": {k: asdict(v) for k, v in state.nodes.items()},
        "path_class": classify_path_blind(state) if blind else classify_path(state),
    }
    if not blind:
        payload["observed_comparison"] = compare_with_observed(state)
    return payload


def write_trace(path: Path, payload: Dict[str, object]) -> None:
    lines = [
        f"SCENARIO: {payload['scenario']['name']}",
        f"PATH: {payload['path_class']}",
        "MODE: BLIND (observed comparator disabled)" if payload.get("blind_mode") else
        f"CALIBRATION: {payload['observed_comparison']['calibration_result']}",
        "",
    ]
    for event in payload["events"]:
        lines.extend([
            f"[{event['step']}] {event['node']} — {event['stage']}",
            f"  policy: {event['policy_id']}",
            f"  information_update: {json.dumps(event['information_update'], ensure_ascii=False, sort_keys=True)}",
            f"  perceived_resource_state: {json.dumps(event['perceived_resource_state'], ensure_ascii=False, sort_keys=True)}",
            f"  rule: {event['rule']}",
            f"  utilities: {json.dumps(event['utilities'], ensure_ascii=False, sort_keys=True)}",
            f"  ACTION: {event['action']}",
            f"  redistribution: {json.dumps(event['redistribution'], ensure_ascii=False, sort_keys=True)}",
            f"  next: {event['next_node']}",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5000)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "outputs")
    parser.add_argument(
        "--environment", type=Path, default=DEFAULT_ENVIRONMENT_PATH,
        help="JSON file defining the shared historical background and timeline.",
    )
    parser.add_argument(
        "--blind", action="store_true",
        help="Disable observed-outcome comparison and use outcome-neutral path labels.",
    )
    parser.add_argument(
        "--policy", action="append", default=[], metavar="ACTOR=MODULE:CLASS",
        help="Replace one actor policy without changing the environment; may be repeated.",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    environment_config = load_environment_config(args.environment)

    policy_overrides: Dict[str, PersonalityPolicy] = {}
    for item in args.policy:
        if "=" not in item:
            parser.error(f"Invalid --policy {item!r}; expected ACTOR=MODULE:CLASS")
        actor, spec = item.split("=", 1)
        if actor not in ("Merz", "Wuest", "Soeder"):
            parser.error(f"Unknown actor {actor!r}; choose Merz, Wuest, or Soeder")
        policy_overrides[actor] = load_policy(spec)

    scenarios = scenario_set()
    summary: Dict[str, object] = {}
    for name, scenario in scenarios.items():
        state = Simulation(
            scenario, policies=policy_overrides, environment_config=environment_config
        ).run()
        payload = state_payload(
            scenario, state, policies=policy_overrides,
            environment_config=environment_config,
            blind=args.blind,
        )
        (args.out / f"{name}_trace.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        write_trace(args.out / f"{name}_trace.txt", payload)
        mc = monte_carlo(
            scenario, args.runs, policies=policy_overrides,
            environment_config=environment_config,
            blind=args.blind,
        )
        (args.out / f"{name}_monte_carlo.json").write_text(
            json.dumps(mc, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary[name] = {
            "deterministic_path": payload["path_class"],
            "mode": "blind" if args.blind else "calibration",
            "key_actions": {
                "Merz_initial": state.events[0].action,
                "Wuest": state.actions.get("Wuest"),
                "Soeder": state.actions.get("Soeder"),
                "closure_candidate": state.closure_candidate,
            },
            "monte_carlo": mc,
        }
        if not args.blind:
            summary[name]["calibration"] = payload["observed_comparison"]["calibration_result"]

    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

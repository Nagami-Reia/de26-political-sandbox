"""Plug-in API for actor decision models.

The environment owns facts, timing, visibility, resource accounting, and action
effects. A personality policy sees only a stage-specific DecisionContext and chooses
one of the allowed actions. This keeps background assumptions separate from actor
logic and lets researchers replace one actor without rewriting the world.
"""

from __future__ import annotations

import importlib
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Mapping, Sequence


def bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def weighted_gmean(values: Sequence[float], weights: Sequence[float]) -> float:
    pairs = [(max(v, 1e-9), w) for v, w in zip(values, weights) if w > 0]
    if not pairs:
        return 0.0
    return math.exp(sum(w * math.log(v) for v, w in pairs) / sum(w for _, w in pairs))


@dataclass(frozen=True)
class DecisionContext:
    actor: str
    stage: str
    allowed_actions: tuple[str, ...]
    features: Mapping[str, float | str]
    visible_world: Mapping[str, object]
    parameters: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    utilities: Mapping[str, float]
    rule: str
    diagnostics: Mapping[str, object] = field(default_factory=dict)


class PersonalityPolicy(ABC):
    """Implement this class to insert a different personality decision model."""

    policy_id = "abstract"
    actor = "*"

    @abstractmethod
    def decide(self, context: DecisionContext) -> PolicyDecision:
        raise NotImplementedError

    def choose_max(
        self, context: DecisionContext, utilities: Mapping[str, float], rule: str,
        diagnostics: Mapping[str, object] | None = None,
    ) -> PolicyDecision:
        unknown = set(utilities) - set(context.allowed_actions)
        if unknown:
            raise ValueError(f"{self.policy_id} emitted disallowed actions: {sorted(unknown)}")
        action = max(utilities, key=utilities.get)
        return PolicyDecision(action, dict(utilities), rule, diagnostics or {})


class MerzAgencyPolicy(PersonalityPolicy):
    policy_id = "merz_agency_gestaltung_v1"
    actor = "Merz"

    def decide(self, c: DecisionContext) -> PolicyDecision:
        f = c.features
        if c.stage == "preclosure_positioning":
            hold = bounded(0.44 * float(f["default"]) + 0.31 * float(f["backing"]) + 0.25 * float(f["agency"]))
            declare = bounded(hold - 0.10 - 0.13 * float(f["unity_cost"]))
            return self.choose_max(
                c,
                {"hold_default_and_bilateral_channel": hold, "declare_publicly": declare},
                "Agency/Gestaltung favors candidacy, but incumbent/default advantage raises the threshold for a costly public declaration.",
            )
        if c.stage == "bilateral_closure":
            viability = float(f["merz_viability"])
            risk = bounded(0.48 + 0.45 * viability)
            assert_value = bounded(0.46 * float(f["agency"]) + 0.39 * viability + 0.15 * risk)
            delay_value = bounded(0.68 - 0.30 * viability)
            return self.choose_max(
                c,
                {"assert_candidacy_in_bilateral": assert_value, "delay_or_seek_alternative": delay_value},
                "Agency/Gestaltung supplies the pull; risk tolerance is conditional on organizational backing and the office default.",
                {"conditional_risk_capacity": round(risk, 4)},
            )
        raise ValueError(f"Unsupported Merz stage: {c.stage}")


class WuestAKATPolicy(PersonalityPolicy):
    policy_id = "wuest_ambition_control_acceptance_timing_v1"
    actor = "Wuest"

    def decide(self, c: DecisionContext) -> PolicyDecision:
        if c.stage != "candidacy_choice":
            raise ValueError(f"Unsupported Wuest stage: {c.stage}")
        f = c.features
        control_weight = float(c.parameters.get("control_weight", 1.0))
        challenge = weighted_gmean(
            [float(f["ambition"]), float(f["control"]), float(f["acceptance"]), float(f["timing"])],
            [1.15, control_weight, 1.00, 1.00],
        )
        endorse = weighted_gmean(
            [float(f["endorse_ambition"]), float(f["endorse_control"]),
             float(f["endorse_acceptance"]), float(f["endorse_timing"])],
            [1.15, control_weight, 1.00, 1.00],
        )
        wait = weighted_gmean(
            [0.72, 0.57, 0.55, 0.48],
            [1.15, control_weight, 1.00, 1.00],
        )
        endorse_action = str(f["endorse_action"])
        return self.choose_max(
            c,
            {"challenge": challenge, endorse_action: endorse, "remain_ambiguous": wait},
            "Ambition × Kontrolle × Akzeptanz × Timing. A challenge must clear all four; withdrawal can still exercise control, create acceptance, and preserve future option value.",
        )


class SoederEvidenceBoundedPolicy(PersonalityPolicy):
    policy_id = "soeder_evidence_bounded_resources_v1"
    actor = "Soeder"

    def decide(self, c: DecisionContext) -> PolicyDecision:
        f = c.features
        if c.stage == "availability_signal":
            signal = bounded(0.39 * float(f["visibility"]) + 0.37 * float(f["apparatus"]) + 0.24 * (1 - float(f["bridgehead"])))
            quiet = bounded(0.49 + 0.24 * float(f["bridgehead"]) + 0.10 * float(f["unity_cost"]))
            return self.choose_max(
                c,
                {"signal_availability_conditioned_on_CDU_call": signal, "stay_quiet": quiet},
                "Use only evidenced strategic constraints: signal availability to test/create a CDU call while retaining bilateral agreement language.",
            )
        if c.stage == "bilateral_closure":
            contest = bounded(
                0.34 * float(f["soeder_viability"]) + 0.35 * float(f["bridgehead"])
                + 0.20 * float(f["apparatus"]) - 0.24 * float(f["unity_cost"]) + 0.11
            )
            close_merz = bounded(
                0.30 * float(f["merz_viability"]) + 0.27 * (1 - float(f["bridgehead"]))
                + 0.24 * float(f["unity_cost"]) + 0.14 * float(f["future_option"])
                + float(f["private_bargain_contingency"])
            )
            propose = bounded(contest + 0.14 * (float(f["soeder_viability"]) - float(f["merz_viability"])))
            return self.choose_max(
                c,
                {"continue_contest": contest, "bilateral_close_Merz": close_merz, "propose_Soeder": propose},
                "Evidence-bounded logic only: a CSU path needs a CDU call; absent that, the value of an agreed closure rises. No private psychology is imputed.",
            )
        raise ValueError(f"Unsupported Soeder stage: {c.stage}")


def default_personality_policies() -> Dict[str, PersonalityPolicy]:
    return {
        "Merz": MerzAgencyPolicy(),
        "Wuest": WuestAKATPolicy(),
        "Soeder": SoederEvidenceBoundedPolicy(),
    }


def load_policy(spec: str) -> PersonalityPolicy:
    """Load `module:ClassName`; the class must have a zero-argument constructor."""
    if ":" not in spec:
        raise ValueError("Policy spec must use module:ClassName")
    module_name, class_name = spec.split(":", 1)
    cls = getattr(importlib.import_module(module_name), class_name)
    instance = cls()
    if not isinstance(instance, PersonalityPolicy):
        raise TypeError(f"{spec} is not a PersonalityPolicy")
    return instance


from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .base import (
    CheckBundle, CheckResult, CheckStatus, CompiledRule, LayerCheck,
    Resolution, resolution_for,
)
from .context import CheckContext
from kfrage_model.interaction.intents import Intent


class RuleRegistry:
    """O(1) intent lookup followed by a small fixed predicate set."""

    def __init__(self, rules: Iterable[CompiledRule] = ()) -> None:
        self.rules: dict[str, CompiledRule] = {}
        self.index: dict[str, tuple[str, ...]] = {}
        for rule in rules:
            self.register(rule)

    def register(self, rule: CompiledRule) -> None:
        if rule.rule_id in self.rules:
            raise ValueError(f"duplicate rule_id: {rule.rule_id}")
        self.rules[rule.rule_id] = rule
        for intent_type in rule.intent_types:
            self.index[intent_type] = (*self.index.get(intent_type, ()), rule.rule_id)

    def check(self, context: CheckContext, intent: Intent) -> tuple[CheckResult, ...]:
        rule_ids = self.index.get(intent.intent_type, ())
        if not rule_ids:
            return (CheckResult(CheckStatus.NOT_APPLICABLE, "NO_MATCHING_RULE"),)
        return tuple(self.rules[rule_id].check(context, intent) for rule_id in rule_ids)


class CheckEngine:
    def __init__(self, layers: Mapping[str, RuleRegistry]) -> None:
        self.layers = dict(layers)

    def check(self, context: CheckContext, intent: Intent) -> CheckBundle:
        layers = tuple(
            LayerCheck(name, registry.check(context, intent))
            for name, registry in self.layers.items()
        )
        all_results = tuple(result for layer in layers for result in layer.results)
        return CheckBundle(intent.intent_id, layers, resolution_for(all_results))


@dataclass(frozen=True, slots=True)
class InstitutionalResolution:
    resolution: Resolution
    effects: tuple[str, ...]
    required_procedures: tuple[str, ...]
    reasons: tuple[str, ...]

    def payload(self) -> dict:
        return {
            "resolution": self.resolution.value,
            "effects": list(self.effects),
            "required_procedures": list(self.required_procedures),
            "reasons": list(self.reasons),
        }


class InstitutionalResolver:
    """Aggregate typed check results; never reduce them to a Boolean AND."""

    def resolve(self, bundle: CheckBundle) -> InstitutionalResolution:
        results = [item for layer in bundle.layers for item in layer.results]
        return InstitutionalResolution(
            resolution=bundle.resolution,
            effects=tuple(dict.fromkeys(effect for item in results for effect in item.effects)),
            required_procedures=tuple(dict.fromkeys(
                item.required_procedure for item in results if item.required_procedure
            )),
            reasons=tuple(dict.fromkeys(item.reason for item in results if item.reason)),
        )

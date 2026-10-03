"""Formal rules, informal norms and enforcement strength for a simulation world."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Mapping

from .institutional_logic import clamp01


@dataclass(frozen=True)
class InstitutionalRule:
    key: str
    kind: str
    strength: float
    enforcement: float
    action_permissions: tuple[str, ...] = ()
    source_status: str = "MODEL_ASSUMPTION"

    def __post_init__(self) -> None:
        if self.kind not in {"formal", "informal", "enforcement"}:
            raise ValueError(f"Unknown institutional rule kind: {self.kind}")
        if clamp01(self.strength) != self.strength or clamp01(self.enforcement) != self.enforcement:
            raise ValueError("Rule strength and enforcement must be in 0.000..1.000")


@dataclass(frozen=True)
class InstitutionalMatrix:
    matrix_id: str
    actor_offices: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    office_permissions: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    rules: tuple[InstitutionalRule, ...] = ()

    def permissions_for(self, actor: str) -> set[str]:
        permissions: set[str] = set()
        for office in self.actor_offices.get(actor, ()):
            permissions.update(self.office_permissions.get(office, ()))
        for rule in self.rules:
            if rule.enforcement > 0.0:
                permissions.update(rule.action_permissions)
        return permissions

    def payload(self) -> dict:
        return {
            "matrix_id": self.matrix_id,
            "actor_offices": {key: list(value) for key, value in self.actor_offices.items()},
            "office_permissions": {key: list(value) for key, value in self.office_permissions.items()},
            "rules": [asdict(rule) for rule in self.rules],
        }


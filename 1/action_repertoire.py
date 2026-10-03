"""Objective action menu to actor-role repertoire, without personality choice."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .institutional_matrix import InstitutionalMatrix
from .persona_v2 import ActionOption


@dataclass(frozen=True)
class RepertoireAssessment:
    action: str
    objective_status: str
    role_status: str
    objective_feasibility: float
    resource_coverage: float
    missing_offices: tuple[str, ...]
    missing_permissions: tuple[str, ...]
    reasons: tuple[str, ...]

    def payload(self) -> dict:
        return asdict(self)


class ActionRepertoireFilter:
    def __init__(self, matrix: InstitutionalMatrix):
        self.matrix = matrix

    def apply(
        self,
        actor: str,
        actions: Sequence[ActionOption],
        resources: Mapping[str, float],
    ) -> dict[str, RepertoireAssessment]:
        offices = set(self.matrix.actor_offices.get(actor, ()))
        permissions = self.matrix.permissions_for(actor)
        result: dict[str, RepertoireAssessment] = {}
        for action in actions:
            missing_offices = tuple(sorted(set(action.required_offices) - offices))
            missing_permissions = tuple(sorted(set(action.required_institutional_permissions) - permissions))
            coverage_rows = [
                min(1.0, float(resources.get(key, 0.0)) / need) if need > 0.0 else 1.0
                for key, need in action.required_resources.items()
            ]
            coverage = sum(coverage_rows) / len(coverage_rows) if coverage_rows else 1.0
            reasons: list[str] = []
            if not action.legal:
                reasons.append("environment_illegal")
            if missing_offices:
                reasons.append("missing_required_office")
            if missing_permissions:
                reasons.append("missing_institutional_permission")
            if coverage < 1.0:
                reasons.append("insufficient_resources_soft_constraint")
            role_available = action.legal and not missing_offices and not missing_permissions
            result[action.key] = RepertoireAssessment(
                action=action.key,
                objective_status="AVAILABLE" if action.legal else "UNAVAILABLE",
                role_status="AVAILABLE" if role_available else "UNAVAILABLE",
                objective_feasibility=round(action.objective_feasibility, 3),
                resource_coverage=round(coverage, 3),
                missing_offices=missing_offices,
                missing_permissions=missing_permissions,
                reasons=tuple(reasons),
            )
        return result


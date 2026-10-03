from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Callable, FrozenSet, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import CheckContext
    from ..interaction.intents import Intent


class CheckStatus(str, Enum):
    PASS = "pass"
    BLOCKED = "blocked"
    PENDING = "pending"
    ROUTED = "routed"
    NOT_APPLICABLE = "not_applicable"


class Resolution(str, Enum):
    EXECUTABLE = "executable"
    BLOCKED = "blocked"
    PENDING = "pending"
    REQUIRES_PROCEDURE = "requires_procedure"


@dataclass(frozen=True, slots=True)
class CheckResult:
    status: CheckStatus
    rule_id: str
    reason: str | None = None
    required_procedure: str | None = None
    missing_conditions: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    diagnostics: Mapping[str, object] = field(default_factory=dict)

    def payload(self) -> dict:
        row = asdict(self)
        row["status"] = self.status.value
        return row


CheckFunction = Callable[["CheckContext", "Intent"], CheckResult]


@dataclass(frozen=True, slots=True)
class CompiledRule:
    rule_id: str
    intent_types: FrozenSet[str]
    check: CheckFunction
    authority: str
    citation: str
    source_version: str


@dataclass(frozen=True, slots=True)
class LayerCheck:
    layer: str
    results: tuple[CheckResult, ...]

    def payload(self) -> dict:
        return {"layer": self.layer, "results": [item.payload() for item in self.results]}


@dataclass(frozen=True, slots=True)
class CheckBundle:
    intent_id: str
    layers: tuple[LayerCheck, ...]
    resolution: Resolution

    def payload(self) -> dict:
        return {
            "intent_id": self.intent_id,
            "resolution": self.resolution.value,
            "layers": [layer.payload() for layer in self.layers],
        }


def resolution_for(results: tuple[CheckResult, ...]) -> Resolution:
    statuses = {item.status for item in results}
    if CheckStatus.BLOCKED in statuses:
        return Resolution.BLOCKED
    if CheckStatus.PENDING in statuses:
        return Resolution.PENDING
    if CheckStatus.ROUTED in statuses:
        return Resolution.REQUIRES_PROCEDURE
    return Resolution.EXECUTABLE

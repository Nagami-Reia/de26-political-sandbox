from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ProcedureState:
    procedure_id: str
    procedure_type: str
    stage: str
    started_at_hours: int
    initiators: tuple[str, ...] = ()
    candidate: str | None = None
    target: str | None = None
    votes_yes: int = 0
    votes_no: int = 0
    votes_abstain: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def elapsed_hours(self, now_hours: int) -> int:
        return max(0, int(now_hours) - int(self.started_at_hours))


class ProcedureBook:
    def __init__(self, procedures: Mapping[str, ProcedureState] | None = None) -> None:
        self.procedures = dict(procedures or {})

    def get(self, procedure_id: str | None) -> ProcedureState | None:
        return self.procedures.get(procedure_id) if procedure_id else None

    def active_by_type(self, procedure_type: str) -> tuple[ProcedureState, ...]:
        return tuple(
            item for item in self.procedures.values()
            if item.procedure_type == procedure_type and item.stage not in {"CLOSED", "COMPLETED"}
        )

    def add(self, procedure: ProcedureState) -> None:
        if procedure.procedure_id in self.procedures:
            raise ValueError(f"duplicate procedure_id: {procedure.procedure_id}")
        self.procedures[procedure.procedure_id] = procedure

    def update(self, procedure_id: str, **changes: Any) -> ProcedureState:
        current = self.procedures[procedure_id]
        updated = replace(current, **changes)
        self.procedures[procedure_id] = updated
        return updated

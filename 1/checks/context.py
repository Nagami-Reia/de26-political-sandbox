from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from kfrage_model.procedures.state import ProcedureBook, ProcedureState


@dataclass(frozen=True, slots=True)
class BundestagState:
    statutory_members: int
    current_members: int | None = None

    @property
    def member_majority(self) -> int:
        return self.statutory_members // 2 + 1


@dataclass(frozen=True, slots=True)
class FederalLawExecution:
    law_id: str
    administration_mode: str = "LAND_OWN_AFFAIRS"
    domain: str = "GENERAL"
    federal_legislative_competence: bool = True
    bundesrat_consent: bool = False
    authorizes_individual_instructions: bool = False
    special_administration_rule: str | None = None


@dataclass(slots=True)
class CheckContext:
    """Objective world facts only. Actor beliefs are intentionally absent."""

    now_hours: int
    bundestag: BundestagState
    actor_roles: Mapping[str, frozenset[str]]
    office_holders: Mapping[str, str]
    procedures: ProcedureBook = field(default_factory=ProcedureBook)
    federal_laws: Mapping[str, FederalLawExecution] = field(default_factory=dict)
    facts: Mapping[str, Any] = field(default_factory=dict)

    def has_role(self, actor: str, role: str) -> bool:
        return role in self.actor_roles.get(actor, frozenset())

    def holds_office(self, actor: str, office: str) -> bool:
        return self.office_holders.get(office) == actor

    def procedure_for(self, intent_payload: Mapping[str, Any], procedure_type: str) -> ProcedureState | None:
        explicit = self.procedures.get(intent_payload.get("procedure_id"))
        if explicit is not None:
            return explicit if explicit.procedure_type == procedure_type else None
        active = self.procedures.active_by_type(procedure_type)
        return active[0] if len(active) == 1 else None

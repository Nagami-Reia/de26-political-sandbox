from __future__ import annotations

from ..base import CompiledRule
from .common import GG_AUTHORITY, GG_SOURCE_VERSION, blocked, passed


def check_art62(context, intent):
    chancellor = intent.payload.get("chancellor") or context.office_holders.get("federal_chancellor")
    ministers = tuple(intent.payload.get("ministers", ()))
    if not chancellor:
        return blocked("GG_62", "CHANCELLOR_REQUIRED", "chancellor")
    if not ministers:
        return blocked("GG_62", "FEDERAL_MINISTERS_REQUIRED", "ministers")
    return passed("GG_62", "FEDERAL_GOVERNMENT_COMPOSITION_VALID")


RULES = (
    CompiledRule(
        "GG_62", frozenset({"constitute_federal_government"}), check_art62,
        GG_AUTHORITY, "Art. 62 GG", GG_SOURCE_VERSION,
    ),
)

from __future__ import annotations

from typing import Any

from ..base import CheckResult, CheckStatus
from ..context import CheckContext


GG_AUTHORITY = "Grundgesetz für die Bundesrepublik Deutschland"
GG_SOURCE_VERSION = "GG zuletzt geändert durch Art. 1 G v. 22.03.2025, BGBl. 2025 I Nr. 94"


def routed(rule_id: str, procedure: str, reason: str = "PROCEDURE_REQUIRED", **diagnostics: Any) -> CheckResult:
    return CheckResult(
        CheckStatus.ROUTED,
        rule_id,
        reason=reason,
        required_procedure=procedure,
        diagnostics=diagnostics,
    )


def blocked(rule_id: str, reason: str, *missing: str, alternatives: tuple[str, ...] = ()) -> CheckResult:
    return CheckResult(
        CheckStatus.BLOCKED,
        rule_id,
        reason=reason,
        missing_conditions=tuple(missing),
        alternatives=alternatives,
    )


def pending(rule_id: str, reason: str, *missing: str, **diagnostics: Any) -> CheckResult:
    return CheckResult(
        CheckStatus.PENDING,
        rule_id,
        reason=reason,
        missing_conditions=tuple(missing),
        diagnostics=diagnostics,
    )


def passed(rule_id: str, *effects: str, **diagnostics: Any) -> CheckResult:
    return CheckResult(CheckStatus.PASS, rule_id, effects=tuple(effects), diagnostics=diagnostics)


def majority_diagnostic(context: CheckContext, yes_votes: int) -> dict[str, int]:
    return {
        "yes_votes": int(yes_votes),
        "member_majority": context.bundestag.member_majority,
        "statutory_members": context.bundestag.statutory_members,
    }

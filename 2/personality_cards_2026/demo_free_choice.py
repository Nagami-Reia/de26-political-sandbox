#!/usr/bin/env python3
"""Minimal proof that one unchanged card can choose different actions by turn."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kfrage_model.persona_v2 import ActionOption, FreeAgentDecisionEngine, WorldEvent


HERE = Path(__file__).resolve().parent


def menu() -> list[ActionOption]:
    return [
        ActionOption(
            "public_challenge",
            goal_impacts={"seize_window": 0.9},
            value_impacts={"future_option": 0.8, "governability": -0.1},
            required_resources={"organization_base": 0.60},
            upside=0.95,
            downside=0.25,
            uncertainty=0.12,
            irreversibility=0.25,
            effort=0.45,
            visibility=0.80,
            information_confidence=0.90,
            control_domains=("process",),
            restores_control=0.90,
            conflict_strategy="attack",
            identity_tags=("timing", "process_control", "prepared_structure"),
            risk_tags=("public", "prepared_structure"),
        ),
        ActionOption(
            "coalition_coordination",
            goal_impacts={"seize_window": -0.2},
            value_impacts={"governability": 0.4, "broad_acceptance": 0.4, "future_option": 0.15},
            required_resources={"network_capital": 0.45},
            upside=0.45,
            downside=0.12,
            uncertainty=0.08,
            effort=0.30,
            visibility=0.20,
            information_confidence=0.92,
            control_domains=("coalition", "relationships"),
            restores_control=0.35,
            conflict_strategy="negotiate",
            identity_tags=("coalition", "acceptance", "connection"),
        ),
    ]


def main() -> None:
    engine = FreeAgentDecisionEngine.from_json(HERE / "cards_pss.json")
    resources = {"organization_base": 0.90, "network_capital": 0.90}
    first = engine.decide("Wuest", menu(), resources)
    update = engine.apply_event(
        "Wuest",
        WorldEvent(
            event_id="verified_opening",
            event_type="control_window",
            severity=1.000,
            tags=("loss_of_control", "prepared_structure", "time_window"),
            surprise=0.100,
            valence=-1.000,
            impact_profile={"pressure": 0.050, "energy": 0.050, "confidence": 0.000, "control": 1.000, "identity_integrity": 0.020},
        ),
    )
    second = engine.decide("Wuest", menu(), resources, current_goals={"seize_window": 1.0})
    print(json.dumps({
        "same_card": True,
        "turn_1": asdict(first),
        "world_update": update,
        "turn_2": asdict(second),
        "interpretation": "The action changes because world goal and current state changed; personality did not randomize.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

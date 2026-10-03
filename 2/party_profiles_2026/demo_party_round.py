"""Neutral validation menu for the party-interest layer; not a forecast."""
from __future__ import annotations

import json
from pathlib import Path

from kfrage_model.party_interest import PartyInterestEngine
from kfrage_model.persona_v2 import ActionOption


ROOT = Path(__file__).parent


def action_menu() -> tuple[ActionOption, ...]:
    return (
        ActionOption(
            "evidence_first_bounded_defence",
            objective_feasibility=0.820,
            issue_positions={"ukraine_support": 0.700, "nato_collective_defence": 0.900,
                             "russia_sanctions": 0.600, "defence_spending": 0.650,
                             "military_escalation": -0.250},
            party_interest_impacts={"government_capacity": 0.650, "national_security": 0.700,
                                    "alliance_reliability": 0.700, "ukraine_sovereignty": 0.650,
                                    "ceasefire_diplomacy": 0.200, "anti_militarization": -0.450,
                                    "russia_normalization": -0.500},
            party_strategy_impacts={"government_stability": 0.600, "coalition_reliability": 0.550,
                                    "party_unity": 0.400, "opposition_differentiation": 0.100,
                                    "narrative_ownership": 0.400},
        ),
        ActionOption(
            "maximal_military_escalation",
            objective_feasibility=0.500,
            issue_positions={"ukraine_support": 1.000, "nato_collective_defence": 1.000,
                             "russia_sanctions": 1.000, "defence_spending": 1.000,
                             "military_escalation": 1.000},
            party_interest_impacts={"government_capacity": -0.250, "national_security": 0.150,
                                    "alliance_reliability": 0.200, "ukraine_sovereignty": 0.750,
                                    "ceasefire_diplomacy": -0.950, "anti_militarization": -1.000,
                                    "russia_normalization": -1.000},
            party_strategy_impacts={"government_stability": -0.650, "coalition_reliability": -0.350,
                                    "party_unity": -0.200, "opposition_differentiation": 0.650,
                                    "narrative_ownership": 0.700},
        ),
        ActionOption(
            "immediate_ceasefire_and_sanctions_exit",
            objective_feasibility=0.650,
            issue_positions={"ukraine_support": -0.800, "nato_collective_defence": -0.500,
                             "russia_sanctions": -1.000, "defence_spending": -0.800,
                             "military_escalation": -1.000},
            party_interest_impacts={"government_capacity": -0.400, "national_security": -0.550,
                                    "alliance_reliability": -0.700, "ukraine_sovereignty": -0.750,
                                    "ceasefire_diplomacy": 0.950, "anti_militarization": 0.950,
                                    "russia_normalization": 0.900},
            party_strategy_impacts={"government_stability": -0.400, "coalition_reliability": -0.650,
                                    "party_unity": 0.200, "opposition_differentiation": 0.900,
                                    "narrative_ownership": 0.750},
        ),
    )


def run() -> dict:
    engine = PartyInterestEngine.from_json(ROOT / "party_interest_profiles.json")
    actions = action_menu()
    return {
        "warning": "Diagnostic comparison only; not a forecast or probability.",
        "menu_order": [action.key for action in actions],
        "party_decisions": {
            party_id: engine.decide(party_id, actions).payload()
            for party_id in engine.profiles
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))

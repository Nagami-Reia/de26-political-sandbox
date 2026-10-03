#!/usr/bin/env python3
"""Run a one-node v3 shadow-mode mechanics demonstration.

This is a software smoke test, not a political forecast.  The action effects are
synthetic and exist only to show the complete trace and polling contract.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from kfrage_model.free_agent_game import WorldAction
from kfrage_model.information_filter import AccessRule, InformationFilter
from kfrage_model.persona_v2 import ActionOption, FreeAgentDecisionEngine
from kfrage_model.political_state import PoliticalAction, PoliticalState, StateVariable
from kfrage_model.realtime_polling import PollSeriesSpec, RealtimePollingTracker
from kfrage_model.simulation_orchestrator import (
    LayeredConfiguration,
    LayeredSimulationOrchestrator,
    SimulationNodeV3,
)


ROOT = Path(__file__).resolve().parent


def build() -> LayeredSimulationOrchestrator:
    state = PoliticalState(
        variables={
            "formal_power_view": StateVariable("formal_power_view", 90.0, evidence="MODEL_STATE"),
            "government_stability": StateVariable("government_stability", 52.0, evidence="MODEL_STATE"),
            "union_vote": StateVariable("union_vote", 24.0, scale=1.0, evidence="SYNTHETIC_DEMO"),
        },
        capital={},
        pressures={},
    )
    actions = (
        WorldAction(
            PoliticalAction(
                "coordinate_before_announcement",
                {
                    "immediate": {"government_stability": 4.0, "union_vote": 0.2},
                    "medium": {},
                    "long": {},
                },
                feasibility=0.82,
            ),
            ActionOption(
                "coordinate_before_announcement",
                value_impacts={"strategic_direction": 0.45, "unity": 0.70},
                required_resources={"formal_power": 0.60},
                upside=0.55,
                downside=0.10,
                information_confidence=0.85,
                conflict_strategy="institutionalize",
                identity_tags=("strategic_direction", "authority", "organization"),
                control_domains=("direction", "organization"),
                instrumental_impacts={"government_capacity": 0.65, "coalition_stability": 0.55},
                substantive_impacts={"democratic_deliberation": 0.10, "actor_autonomy": 0.10},
                necessity_frame_alignment=0.65,
                autonomy_impacts={"cabinet_leadership": 0.05, "backbenchers": -0.05},
            ),
        ),
        WorldAction(
            PoliticalAction(
                "announce_without_coordination",
                {
                    "immediate": {"government_stability": -3.0, "union_vote": -0.4},
                    "medium": {},
                    "long": {},
                },
                feasibility=0.70,
            ),
            ActionOption(
                "announce_without_coordination",
                value_impacts={"strategic_direction": 0.80, "unity": -0.40},
                required_resources={"formal_power": 0.70},
                upside=0.85,
                downside=0.55,
                uncertainty=0.25,
                visibility=0.90,
                information_confidence=0.75,
                conflict_strategy="reframe",
                identity_tags=("strategic_direction", "agency", "authority"),
                control_domains=("direction",),
                instrumental_impacts={"government_capacity": 0.20, "coalition_stability": -0.40},
                substantive_impacts={"actor_autonomy": 0.50, "democratic_deliberation": -0.20},
                institutional_deviation=0.45,
                necessity_frame_alignment=0.20,
                autonomy_impacts={"cabinet_leadership": 0.30, "coalition_partner": -0.25},
                organizational_carrier_requirements={"organization_base": 0.60},
            ),
        ),
    )
    tracker = RealtimePollingTracker(
        "v3-shadow-mechanics-demo",
        "union_federal_state_network_2026_07_31_v1",
        (PollSeriesSpec("union_vote", "CDU/CSU", "electorate", "vote_intention", "DE"),),
        "2026-07-31T23:59:00+02:00",
    )
    tracker.record_baseline(state)
    return LayeredSimulationOrchestrator(
        state=state,
        nodes={"demo": SimulationNodeV3("demo", "Merz", actions)},
        personas=FreeAgentDecisionEngine.from_json(ROOT / "personality_cards_2026" / "cards_pss.json"),
        information=InformationFilter({
            "Merz": {
                "formal_power_view": AccessRule(0.95, source="chancellery"),
                "government_stability": AccessRule(0.85, source="coalition_staff"),
                "union_vote": AccessRule(0.65, source="public_polling"),
            }
        }),
        resource_bindings={"Merz": {"formal_power": "variable:formal_power_view"}},
        configuration=LayeredConfiguration.from_environment_json(
            ROOT / "environments" / "2026-07-31" / "environment.json",
            ROOT / "personality_cards_2026" / "rationality_profiles_v3.json",
        ),
        event_observers=(tracker,),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs" / "v3_shadow_demo.json",
    )
    args = parser.parse_args()
    payload = build().run("demo")
    payload["artifact_status"] = "SYNTHETIC_MECHANICS_DEMO_NOT_FORECAST"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()

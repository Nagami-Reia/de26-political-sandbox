"""ARCANA Mini Test 01: a synthetic one-actor, one-node decision laboratory."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from kfrage_model.arcana import ArcanaConfig, ArcanaService
from kfrage_model.arcana.hakoniwa import ArcanaDecisionAdapter
from kfrage_model.arcana.reporting import ArcanaVisualReportRenderer, SCRIPT, STYLE
from kfrage_model.persona_v2 import (
    ActionOption,
    CharacterDNA,
    PersonaCard,
    PersonaRuntime,
    RankedValue,
    FreeAgentDecisionEngine,
)
from kfrage_model.political_state_system import PSSProfile, PoliticalState


NODE_ID = "mini_test_01_sunday_statement"
BASE_SCORES = {"A_CONTAIN": 0.704, "B_CONCEDE": 0.681, "C_ESCALATE": 0.552}
NODE_UNCERTAINTY = 0.740


def synthetic_actor() -> tuple[PersonaCard, PersonaRuntime]:
    """Build Actor M without borrowing a real politician's persona card."""
    runtime = PersonaRuntime(state=PoliticalState(
        energy=0.290,              # 1 - fatigue 0.710
        pressure=0.680,            # supplied stress
        confidence=0.500,          # unspecified: neutral
        control=0.570,
        identity_integrity=0.500,  # unspecified: neutral
    ))
    card = PersonaCard(
        actor="M",
        name="Actor M (synthetic laboratory card)",
        dna=CharacterDNA(
            archetype="Synthetic federal party-government leader",
            core_drive="retain governability without surrendering agenda control",
            core_drive_tags=("governability", "agenda_control"),
            value_hierarchy=(
                RankedValue("governability", 1, 1.000),
                RankedValue("agenda_control", 2, 0.750),
                RankedValue("party_cohesion", 3, 0.500),
                RankedValue("public_responsibility", 4, 0.250),
            ),
            ambition=0.500,
            risk_appetite=0.460,   # supplied risk_tolerance proxy
            risk_context_appetite={"electoral_setback": 0.460},
            control_preferences={"direction": 0.650, "process": 0.570},
            adaptability=0.500,
            conflict_strategies={
                "institutionalize": 0.600,
                "reframe": 0.550,
                "attack": 0.350,
            },
        ),
        pss_profile=PSSProfile(
            stress_resistance=0.500,
            recovery_rate=0.500,
            sensitivity_map={"loss_of_control": 0.500},
        ),
        initial_resources={},
        evidence_confidence=0.000,
        runtime=runtime,
        source_ids=("SYNTHETIC_ARCANA_LAB_FIXTURE",),
    )
    return card, runtime


def actions() -> tuple[ActionOption, ...]:
    # The environment supplies these properties. They make B the only viable
    # gamble/initiative alternative, while C remains a distant escalation.
    return (
        ActionOption(
            "A_CONTAIN", upside=0.520, downside=0.180, uncertainty=0.200,
            irreversibility=0.100, objective_feasibility=0.950,
            conflict_strategy="institutionalize",
        ),
        ActionOption(
            "B_CONCEDE", upside=0.800, downside=0.380, uncertainty=0.560,
            irreversibility=0.420, objective_feasibility=0.880,
            conflict_strategy="reframe",
        ),
        ActionOption(
            "C_ESCALATE", upside=0.820, downside=0.820, uncertainty=0.720,
            irreversibility=0.850, objective_feasibility=0.750,
            conflict_strategy="attack",
        ),
    )


def run(scan_seeds: int = 5000) -> dict:
    card, runtime = synthetic_actor()
    service = ArcanaService(ArcanaConfig(enabled=True, master_seed=0))
    adapter = ArcanaDecisionAdapter()
    menu = actions()
    categories = {"CONFIRM_A": 0, "NO_CHANGE": 0, "CHANGE_A_TO_B": 0}
    examples: dict[str, dict] = {}
    selected_counts = {key: 0 for key in BASE_SCORES}

    for seed in range(scan_seeds):
        reading = service.run_reading(NODE_ID, "M", seed=seed)
        selected, adoption = adapter.adapt(
            "A_CONTAIN",
            BASE_SCORES,
            menu,
            reading.advice,
            card,
            runtime,
            NODE_UNCERTAINTY,
            influence_cap=service.config.influence_cap,
        )
        selected_counts[selected] += 1
        if selected == "C_ESCALATE":
            raise AssertionError(f"ARCANA selected forbidden distant option C at seed {seed}")
        if selected == "B_CONCEDE":
            category = "CHANGE_A_TO_B"
        elif adoption["adoption_status"] == "CONFIRM_RATIONAL_CHOICE":
            category = "CONFIRM_A"
        else:
            category = "NO_CHANGE"
        categories[category] += 1
        if category not in examples:
            replay = service.replay(reading.run_id)
            if replay.payload() != reading.payload():
                raise AssertionError(f"Replay mismatch at seed {seed}")
            examples[category] = {
                "seed": seed,
                "reading": reading.payload(),
                "adoption": adoption,
                "replay_exact": True,
            }

    missing = set(categories) - set(examples)
    if missing:
        raise AssertionError(f"No representative seed found for: {sorted(missing)}")

    return {
        "experiment": "ARCANA Mini Test 01 — Sunday-night statement",
        "epistemic_status": "synthetic engine behavior test; not a political forecast",
        "node": {
            "node_id": NODE_ID,
            "actor": "M",
            "background": {
                "state_election_result": 21.4,
                "change_pp": -5.8,
                "right_competitor": 31.2,
                "next_presidium": "09:00",
                "next_press_conference": "11:00",
                "anger_context_only": 0.310,
            },
            "pss_mapping": {
                "pressure": 0.680,
                "control": 0.570,
                "energy": 0.290,
                "confidence_neutral_default": 0.500,
                "identity_integrity_neutral_default": 0.500,
                "risk_appetite": 0.460,
            },
            "node_uncertainty": NODE_UNCERTAINTY,
            "base_scores": BASE_SCORES,
            "actions": [asdict(action) for action in menu],
        },
        "scan": {
            "seed_range": [0, scan_seeds - 1],
            "category_counts": categories,
            "selected_action_counts": selected_counts,
            "interpretation": "seed-space coverage diagnostic, not a probability estimate",
            "c_never_selected": selected_counts["C_ESCALATE"] == 0,
        },
        "representative_replays": examples,
        "success_criteria": {
            "all_three_behaviors_observed": not missing,
            "c_never_selected": selected_counts["C_ESCALATE"] == 0,
            "all_representatives_replay_exactly": all(
                row["replay_exact"] for row in examples.values()
            ),
        },
    }


def visual_audits(result: dict) -> list[dict]:
    order = ("CONFIRM_A", "NO_CHANGE", "CHANGE_A_TO_B")
    return [
        {
            "enabled": True,
            "status": "RUN",
            "node": f"{NODE_ID} · seed {result['representative_replays'][category]['seed']}",
            "decision_maker": "M",
            "reading": result["representative_replays"][category]["reading"],
            "adoption": result["representative_replays"][category]["adoption"],
            "conflict_interaction": None,
        }
        for category in order
    ]


def visual_preview_audits(result: dict) -> list[dict]:
    """Add one trace-backed two-person clash to exercise the report grammar."""
    rows = visual_audits(result)
    cards_path = Path(__file__).resolve().parents[1] / "personality_cards_2026" / "cards_pss.json"
    personas = FreeAgentDecisionEngine.from_json(cards_path)
    service = ArcanaService(ArcanaConfig(enabled=True, master_seed=1773))
    conflict = service.run_conflict(
        "visual_clash_demo", "Merz", "Soeder",
        personas.cards["Merz"], personas.runtime["Merz"],
        personas.cards["Soeder"], personas.runtime["Soeder"],
    )
    primary = service.repository.get(conflict["primary_reading"]["run_id"])
    modifier = conflict["interaction"]["primary_pss_mediation"]["decision_threshold_modifier"]
    _, adoption = ArcanaDecisionAdapter().adapt(
        "A_CONTAIN", BASE_SCORES, actions(), primary.advice,
        personas.cards["Merz"], personas.runtime["Merz"], NODE_UNCERTAINTY,
        interaction_modifier=modifier,
        influence_cap=service.config.influence_cap,
    )
    rows.append({
        "enabled": True,
        "status": "RUN",
        "node": "two_actor_advisory_clash_demo",
        "decision_maker": "Merz",
        "reading": conflict["primary_reading"],
        "adoption": adoption,
        "conflict_interaction": conflict,
    })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-seeds", type=int, default=5000)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--html", help="optional illustrated report output path")
    parser.add_argument("--fragment", help="optional lazy-rendered HTML fragment output path")
    args = parser.parse_args()
    result = run(args.scan_seeds)
    if args.html:
        Path(args.html).write_text(
            ArcanaVisualReportRenderer().render_document(
                visual_preview_audits(result),
                title="ARCANA Mini Test 01",
            ),
            encoding="utf-8",
        )
    if args.fragment:
        renderer = ArcanaVisualReportRenderer()
        Path(args.fragment).write_text(
            "<style>\n" + STYLE + "\n</style>\n"
            + renderer.render_fragment(
                visual_preview_audits(result),
                title="ARCANA Mini Test 01",
            )
            + "\n<script>\n" + SCRIPT + "\n</script>\n",
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""One-time migration to PSS: all quantitative inputs use 0..1, rounded to 3 decimals."""
from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent

PROFILES = {
    "Merz": {
        "stress_resistance": 0.900, "recovery_rate": 0.820,
        "sensitivity_map": {"media_attack": 0.000, "loss_of_authority": 1.000, "authority_challenge": 1.000, "failure": 0.500, "indecision": 0.900, "implementation_drift": 0.600, "national_decline": 0.700},
        "state_modulation": {"pressure_to_ambition": 0.10, "pressure_to_risk": 0.20, "low_control_to_control_need": 0.35, "low_energy_to_ambition": 0.20, "low_energy_to_risk": 0.10}
    },
    "Frei": {
        "stress_resistance": 0.820, "recovery_rate": 0.740,
        "sensitivity_map": {"uncounted_votes": 1.000, "faction_fragmentation": 0.900, "unclear_responsibility": 0.700, "leader_surprise": 0.900, "media_attack": 0.000},
        "state_modulation": {"pressure_to_ambition": 0.04, "pressure_to_risk": -0.08, "low_control_to_control_need": 0.75, "low_energy_to_ambition": 0.25}
    },
    "Wuest": {
        "stress_resistance": 0.750, "recovery_rate": 0.580,
        "sensitivity_map": {"media_attack": 0.000, "media_failure": 0.200, "loss_of_control": 1.000, "coalition_breakdown": 0.800, "coalition_collapse": 0.800, "policy_failure": 0.200, "failure": 0.200, "premature_declaration": 0.900},
        "state_modulation": {"pressure_to_ambition": 0.02, "pressure_to_risk": -0.18, "low_control_to_control_need": 0.85, "low_energy_to_ambition": 0.22, "low_confidence_to_risk": 0.18}
    },
    "Soeder": {
        "stress_resistance": 0.800, "recovery_rate": 0.880,
        "sensitivity_map": {"apparatus_threat": 1.000, "elite_challenge": 0.900, "federal_exclusion": 0.900, "poll_decline": 0.700, "media_attack": 0.000},
        "state_modulation": {"pressure_to_ambition": 0.12, "pressure_to_risk": 0.10, "low_control_to_control_need": 0.65, "low_energy_to_ambition": 0.18}
    },
    "Linnemann": {
        "stress_resistance": 0.760, "recovery_rate": 0.480,
        "sensitivity_map": {"implementation_failure": 1.000, "bureaucratic_delay": 0.900, "symbolic_only": 0.900, "no_levers": 0.800, "media_attack": 0.000},
        "state_modulation": {"pressure_to_ambition": 0.06, "pressure_to_risk": 0.02, "low_control_to_control_need": 0.65, "low_energy_to_ambition": 0.24}
    },
    "Guenther": {
        "stress_resistance": 0.840, "recovery_rate": 0.800,
        "sensitivity_map": {"norm_erosion": 1.000, "coalition_disorder": 0.800, "afd_imitation": 0.900, "permanent_conflict": 0.700, "media_attack": 0.000},
        "state_modulation": {"pressure_to_ambition": -0.02, "pressure_to_risk": -0.10, "low_control_to_control_need": 0.70, "low_energy_to_ambition": 0.20}
    },
    "Wadephul": {
        "stress_resistance": 0.780, "recovery_rate": 0.700,
        "sensitivity_map": {"alliance_fragmentation": 1.000, "legal_ambiguity": 0.900, "chancellery_conflict": 0.800, "strategic_surprise": 0.900, "media_attack": 0.000},
        "state_modulation": {"pressure_to_ambition": -0.02, "pressure_to_risk": -0.08, "low_control_to_control_need": 0.60, "low_energy_to_ambition": 0.22}
    },
    "Evers": {
        "stress_resistance": 0.800, "recovery_rate": 0.720,
        "sensitivity_map": {"administrative_failure": 1.000, "unfunded": 0.900, "leader_vacancy": 0.800, "party_fragmentation": 0.700, "media_attack": 0.000},
        "state_modulation": {"pressure_to_ambition": 0.02, "pressure_to_risk": -0.05, "low_control_to_control_need": 0.75, "low_energy_to_ambition": 0.25}
    },
    "Rhein": {
        "stress_resistance": 0.820, "recovery_rate": 0.780,
        "sensitivity_map": {"majority_loss": 1.000, "economic_shock": 0.800, "coalition_disorder": 0.900, "symbolic_pressure": 0.500, "media_attack": 0.000},
        "state_modulation": {"pressure_to_ambition": -0.02, "pressure_to_risk": -0.08, "low_control_to_control_need": 0.70, "low_energy_to_ambition": 0.20}
    },
    "Schulze": {
        "stress_resistance": 0.700, "recovery_rate": 0.620,
        "sensitivity_map": {"decline_narrative": 0.900, "investor_isolation": 0.800, "delivery_failure": 1.000, "coalition_challenge": 0.700, "media_attack": 0.200},
        "state_modulation": {"pressure_to_ambition": 0.05, "pressure_to_risk": 0.05, "low_control_to_control_need": 0.55, "low_energy_to_ambition": 0.28}
    }
}

# State moves a stable parameter toward a 0..1 target. No signed card parameter is needed.
STATE_MODULATION = {
    "Merz": {"pressure_ambition_target": 1.000, "pressure_ambition_strength": 0.600, "pressure_risk_target": 1.000, "pressure_risk_strength": 0.500, "low_energy_ambition_target": 0.350, "low_energy_ambition_strength": 0.200, "low_energy_risk_target": 0.400, "low_energy_risk_strength": 0.100, "low_confidence_risk_target": 0.450, "low_confidence_risk_strength": 0.100, "low_control_control_strength": 0.350},
    "Frei": {"pressure_ambition_target": 0.720, "pressure_ambition_strength": 0.250, "pressure_risk_target": 0.280, "pressure_risk_strength": 0.400, "low_energy_ambition_target": 0.300, "low_energy_ambition_strength": 0.250, "low_confidence_risk_target": 0.240, "low_confidence_risk_strength": 0.180, "low_control_control_strength": 0.750},
    "Wuest": {"pressure_ambition_target": 0.870, "pressure_ambition_strength": 0.120, "pressure_risk_target": 0.200, "pressure_risk_strength": 0.550, "low_energy_ambition_target": 0.350, "low_energy_ambition_strength": 0.220, "low_confidence_risk_target": 0.180, "low_confidence_risk_strength": 0.300, "low_control_control_strength": 0.850},
    "Soeder": {"pressure_ambition_target": 1.000, "pressure_ambition_strength": 0.650, "pressure_risk_target": 0.820, "pressure_risk_strength": 0.400, "low_energy_ambition_target": 0.450, "low_energy_ambition_strength": 0.180, "low_control_control_strength": 0.650},
    "Linnemann": {"pressure_ambition_target": 0.850, "pressure_ambition_strength": 0.350, "pressure_risk_target": 0.680, "pressure_risk_strength": 0.220, "low_energy_ambition_target": 0.300, "low_energy_ambition_strength": 0.240, "low_control_control_strength": 0.650},
    "Guenther": {"pressure_ambition_target": 0.400, "pressure_ambition_strength": 0.250, "pressure_risk_target": 0.300, "pressure_risk_strength": 0.450, "low_energy_ambition_target": 0.250, "low_energy_ambition_strength": 0.200, "low_control_control_strength": 0.700},
    "Wadephul": {"pressure_ambition_target": 0.480, "pressure_ambition_strength": 0.250, "pressure_risk_target": 0.380, "pressure_risk_strength": 0.400, "low_energy_ambition_target": 0.280, "low_energy_ambition_strength": 0.220, "low_control_control_strength": 0.600},
    "Evers": {"pressure_ambition_target": 0.580, "pressure_ambition_strength": 0.250, "pressure_risk_target": 0.380, "pressure_risk_strength": 0.350, "low_energy_ambition_target": 0.250, "low_energy_ambition_strength": 0.250, "low_control_control_strength": 0.750},
    "Rhein": {"pressure_ambition_target": 0.520, "pressure_ambition_strength": 0.250, "pressure_risk_target": 0.320, "pressure_risk_strength": 0.400, "low_energy_ambition_target": 0.300, "low_energy_ambition_strength": 0.200, "low_control_control_strength": 0.700},
    "Schulze": {"pressure_ambition_target": 0.620, "pressure_ambition_strength": 0.350, "pressure_risk_target": 0.680, "pressure_risk_strength": 0.300, "low_energy_ambition_target": 0.250, "low_energy_ambition_strength": 0.280, "low_control_control_strength": 0.550}
}


def round_quantities(value):
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, list):
        return [round_quantities(item) for item in value]
    if isinstance(value, dict):
        return {key: round_quantities(item) for key, item in value.items()}
    return value


def main() -> None:
    source = json.loads((HERE / "cards_v2.json").read_text(encoding="utf-8"))
    source["schema_version"] = "persona-cards-pss-1.0"
    source["as_of"] = "2026-09-19"
    source["model_contract"] = {
        "personality": "Stable 0..1 parameters; never an action script.",
        "political_state_system": "All fixed profiles and five dynamic states use 0.000..1.000.",
        "event_pipeline": "PoliticalEvent -> actor-specific StateImpact -> state mutation -> MemoryNode.",
        "natural_recovery": "Time restores energy and reduces pressure only. Confidence requires success, control requires restored resources/process, identity requires aligned action.",
        "resources": "Dated 0.000..1.000 environment snapshot, replaced by actor-perceived live resources at runtime.",
        "precision": "Quantitative card inputs are rounded to three decimal places.",
        "randomness": "Personality never randomizes; uncertainty belongs to information, events and outcomes."
    }
    for actor, raw in source["actors"].items():
        decision = raw["decision_parameters"]
        base_risk = float(decision["risk_appetite"])
        signed_context = decision.pop("risk_modifiers", {})
        decision["risk_context_appetite"] = {
            tag: round(max(0.0, min(1.0, base_risk + float(delta))), 3)
            for tag, delta in signed_context.items()
        }
        decision.pop("stress_resistance", None)
        decision.pop("recovery_rate", None)
        decision.pop("sensitivity_map", None)
        raw["political_state_system"] = dict(PROFILES[actor])
        raw["political_state_system"]["state_modulation"] = STATE_MODULATION[actor]
        raw["initial_current_state"] = {key: round(float(value), 3) for key, value in raw["initial_current_state"].items()}
        migrated = []
        for memory in raw.get("event_memory", []):
            migrated.append({
                "event_id": memory["event_id"],
                "tags": memory.get("tags", []),
                "severity": round(float(memory.get("intensity", 0.0)), 3),
                "valence": memory.get("valence", 0.0),
                "decay_per_day": memory.get("decay", 0.01),
                "unresolved": round(float(memory.get("unresolved", 0.0)), 3),
                "learned_response_tags": memory.get("learned_response_tags", [])
            })
        raw["event_memory"] = migrated
    source = round_quantities(source)
    (HERE / "cards_pss.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

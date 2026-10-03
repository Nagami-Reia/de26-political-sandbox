"""Dependency-free CLI and JSON protocol for the political sandbox."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any, Mapping, Sequence

from .persona_v2 import ActionOption, ActionOutcome, FreeAgentDecisionEngine, WorldEvent
from .arcana import ArcanaConfig, ArcanaService
from .arcana.hakoniwa import ArcanaDecisionAdapter
from .political_state_system import quantize3


PACKAGE = Path(__file__).resolve().parent
DEFAULT_CARDS = PACKAGE / "personality_cards_2026" / "cards_pss.json"
SCENARIOS = {
    "germany-russia-risk-2026": {
        "module": "kfrage_model.scenarios.germany_russia_risk_2026.run_scenario",
        "description": "Reversible Germany–Russia escalation-risk sandbox",
        "parameters": True,
    },
    "germany-russia-defence-case": {
        "module": "kfrage_model.scenarios.germany_russia_defence_case.run_scenario",
        "description": "Legacy constitutional defence-case stress scenario",
        "parameters": False,
    },
    "mv-cdu-amthor-aftermath": {
        "module": "kfrage_model.scenarios.mv_cdu_amthor_aftermath.run_scenario",
        "description": "Mecklenburg-Vorpommern CDU succession aftermath",
        "parameters": False,
    },
    "october-2026-three-state": {
        "module": "kfrage_model.scenarios.october_2026_three_state.run_scenario",
        "description": "October 2026 three-state and federal-policy sequence",
        "parameters": False,
    },
}
TUPLE_ACTION_FIELDS = {
    "control_domains", "identity_tags", "event_tags", "risk_tags",
    "required_offices", "required_institutional_permissions",
}
TUPLE_EVENT_FIELDS = {"tags"}
TUPLE_OUTCOME_FIELDS = {"tags"}


def _emit(value: Any, pretty: bool = False) -> None:
    print(json.dumps(quantize3(value), ensure_ascii=False, indent=2 if pretty else None))


def _load_engine(cards: str | Path) -> FreeAgentDecisionEngine:
    return FreeAgentDecisionEngine.from_json(cards)


def _dataclass_from_dict(cls, raw: Mapping[str, Any], tuple_fields: set[str]):
    allowed = {item.name for item in fields(cls)}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"Unknown {cls.__name__} fields: {', '.join(unknown)}")
    values = dict(raw)
    for key in tuple_fields:
        if key in values:
            values[key] = tuple(values[key])
    return cls(**values)


def _action(raw: Mapping[str, Any]) -> ActionOption:
    return _dataclass_from_dict(ActionOption, raw, TUPLE_ACTION_FIELDS)


def _event(raw: Mapping[str, Any]) -> WorldEvent:
    return _dataclass_from_dict(WorldEvent, raw, TUPLE_EVENT_FIELDS)


def _outcome(raw: Mapping[str, Any]) -> ActionOutcome:
    return _dataclass_from_dict(ActionOutcome, raw, TUPLE_OUTCOME_FIELDS)


def _read_json(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _apply_history(engine: FreeAgentDecisionEngine, actor: str, history: Sequence[Mapping[str, Any]]) -> list[dict]:
    trace = []
    for index, item in enumerate(history, start=1):
        kind = item.get("type")
        if kind == "event":
            result = engine.apply_event(actor, _event(item["data"]))
        elif kind == "outcome":
            result = engine.apply_outcome(actor, _outcome(item["data"]))
        elif kind == "advance_time":
            result = engine.advance_time(actor, int(item["days"]), float(item.get("workload", 0.0)))
        else:
            raise ValueError(f"history[{index}] has unsupported type: {kind!r}")
        trace.append({"index": index, "type": kind, "result": result})
    return trace


def _decision_payload(
    engine: FreeAgentDecisionEngine,
    actor: str,
    request: Mapping[str, Any],
    arcana: ArcanaService | None = None,
) -> dict:
    if actor not in engine.cards:
        raise ValueError(f"Unknown actor {actor!r}; run `actors` to list valid keys")
    history = _apply_history(engine, actor, request.get("history", ()))
    actions = tuple(_action(item) for item in request.get("actions", ()))
    if not actions:
        raise ValueError("request.actions must contain at least one action")
    decision = engine.decide(
        actor,
        actions,
        request.get("resources", engine.cards[actor].initial_resources),
        current_goals=request.get("goals", {}),
        scene_tags=tuple(request.get("scene_tags", ())),
        soft_resource_constraints=bool(request.get("soft_resource_constraints", False)),
    )
    arcana_payload = {"enabled": False, "status": "DISABLED"}
    selected_action = decision.chosen_action
    if arcana is not None and arcana.config.enabled:
        node_id = str(request.get("node_id", f"cli:{actor}:{engine.runtime[actor].turn}"))
        node_uncertainty = float(request.get(
            "node_uncertainty",
            sum(action.uncertainty for action in actions) / len(actions),
        ))
        counterparty = request.get("conflict_actor")
        interaction_modifier = 0.000
        if counterparty is not None:
            if counterparty not in engine.cards:
                raise ValueError(f"Unknown conflict_actor {counterparty!r}")
            conflict = arcana.run_conflict(
                node_id, actor, str(counterparty),
                engine.cards[actor], engine.runtime[actor],
                engine.cards[str(counterparty)], engine.runtime[str(counterparty)],
            )
            run = arcana.repository.get(conflict["primary_reading"]["run_id"])
            interaction_modifier = conflict["interaction"]["primary_pss_mediation"]["decision_threshold_modifier"]
            reading = conflict["primary_reading"]
        else:
            run = arcana.run_reading(node_id, actor)
            conflict = None
            reading = run.payload()
        normalized_scores = {
            key: 1.000 / (1.000 + math.exp(-max(-60.0, min(60.0, row.total)) / 18.000))
            for key, row in decision.scores.items()
        }
        selected_action, adoption = ArcanaDecisionAdapter().adapt(
            decision.chosen_action, normalized_scores, actions, run.advice,
            engine.cards[actor], engine.runtime[actor], node_uncertainty,
            interaction_modifier,
            arcana.config.influence_cap,
        )
        arcana_payload = {
            "enabled": True,
            "status": "RUN",
            "reading": reading,
            "adoption": adoption,
            "conflict_interaction": conflict,
        }
    return {
        "protocol_version": "political-sandbox-cli-1.0",
        "actor": actor,
        "history_trace": history,
        "decision": asdict(decision),
        "selected_action_after_arcana": selected_action,
        "arcana": arcana_payload,
        "state_after_history": asdict(engine.runtime[actor].state),
        "relationships_after_history": {
            key: asdict(value) for key, value in engine.runtime[actor].relationships.items()
        },
    }


def cmd_actors(args) -> int:
    engine = _load_engine(args.cards)
    rows = [
        {
            "actor": key,
            "name": card.name,
            "archetype": card.dna.archetype,
            "evidence_confidence": card.evidence_confidence,
        }
        for key, card in engine.cards.items()
    ]
    if args.json:
        _emit({"count": len(rows), "actors": rows}, args.pretty)
    else:
        for row in rows:
            print(f'{row["actor"]:12} {row["name"]:24} {row["archetype"]}')
    return 0


def cmd_card(args) -> int:
    engine = _load_engine(args.cards)
    if args.actor not in engine.cards:
        raise ValueError(f"Unknown actor {args.actor!r}")
    card = engine.cards[args.actor]
    payload = {
        "actor": args.actor,
        "name": card.name,
        "fixed_card": {
            "dna": asdict(card.dna),
            "pss_profile": asdict(card.pss_profile),
            "initial_resources": dict(card.initial_resources),
            "evidence_confidence": card.evidence_confidence,
            "source_ids": card.source_ids,
        },
        "initial_runtime": asdict(engine.runtime[args.actor]),
    }
    _emit(payload, args.pretty or not args.json)
    return 0


def cmd_validate(args) -> int:
    engine = _load_engine(args.cards)
    errors = []
    for actor, card in engine.cards.items():
        if len(card.dna.value_hierarchy) < 4:
            errors.append(f"{actor}: fewer than four ranked values")
        if not card.source_ids:
            errors.append(f"{actor}: no source_ids")
        for counterpart, relation in engine.runtime[actor].relationships.items():
            if set(relation.dependency) != {"organizational", "informational", "electoral", "personal_trust"}:
                errors.append(f"{actor}->{counterpart}: incomplete dependency dimensions")
            if set(relation.alternative_capacity) != {"organizational", "informational", "electoral"}:
                errors.append(f"{actor}->{counterpart}: incomplete alternative_capacity dimensions")
    payload = {
        "valid": not errors,
        "actor_count": len(engine.cards),
        "actors": sorted(engine.cards),
        "errors": errors,
    }
    _emit(payload, args.pretty or not args.json)
    return 0 if not errors else 2


def cmd_decide(args) -> int:
    engine = _load_engine(args.cards)
    arcana = ArcanaService(ArcanaConfig(enabled=args.arcana, master_seed=args.arcana_seed))
    payload = _decision_payload(engine, args.actor, _read_json(args.request), arcana)
    _emit(payload, args.pretty)
    return 0


def cmd_protocol(args) -> int:
    example = {
        "node_id": "example_merz_frei_node",
        "node_uncertainty": 0.650,
        "conflict_actor": "Frei",
        "resources": {"formal_power": 0.900, "organization_base": 0.750},
        "scene_tags": ["authority_challenge"],
        "history": [{
            "type": "event",
            "data": {
                "event_id": "example_shock",
                "event_type": "example_pattern",
                "severity": 0.700,
                "tags": ["authority_challenge"],
                "relationship_deltas": {"Frei": {"trust": -0.150}},
            },
        }],
        "actions": [
            {
                "key": "repair",
                "value_impacts": {"unity": 0.700},
                "upside": 0.500,
                "downside": 0.200,
                "conflict_strategy": "negotiate",
                "target_actor": "Frei",
                "relationship_posture": "repair",
            },
            {
                "key": "set_boundary",
                "value_impacts": {"political_authority": 0.800},
                "upside": 0.650,
                "downside": 0.450,
                "conflict_strategy": "institutionalize",
                "target_actor": "Frei",
                "relationship_posture": "boundary",
            },
        ],
    }
    _emit({
        "protocol_version": "political-sandbox-cli-1.0",
        "usage": "python -m kfrage_model [--arcana --arcana-seed 1773] decide Merz --request request.json --pretty",
        "stdin_usage": "cat request.json | python -m kfrage_model [--arcana] decide Merz --request -",
        "arcana_contract": {
            "default": "disabled",
            "request_fields": ["node_id", "node_uncertainty", "conflict_actor"],
            "conflict_semantics": "independent readings; PSS mediates posture collision; cards never directly mutate PSS",
            "output": "full reading, historical rules, advice derivation, adoption trace, and optional interaction",
        },
        "relationship_postures": ["neutral", "repair", "boundary", "rupture", "comply", "exit"],
        "request_example": example,
    }, True)
    return 0


def cmd_scenarios(args) -> int:
    rows = [{"scenario": key, **value} for key, value in SCENARIOS.items()]
    if args.json:
        _emit({"count": len(rows), "scenarios": rows}, args.pretty)
    else:
        for row in rows:
            print(f'{row["scenario"]:34} {row["description"]}')
    return 0


def cmd_run_scenario(args) -> int:
    spec = SCENARIOS[args.scenario]
    command = [sys.executable, "-m", spec["module"]]
    if spec["parameters"]:
        command.extend(["--runs", str(args.runs)])
        if args.seed is not None:
            command.extend(["--seed", str(args.seed)])
        if args.arcana:
            command.append("--arcana")
    elif args.seed is not None or args.runs != 10000 or args.arcana:
        raise ValueError(f"{args.scenario} is a legacy fixed scenario and accepts no seed/runs/arcana options")
    return subprocess.run(command, check=False).returncode


def cmd_play(args) -> int:
    """Persistent JSONL mode intended for another AI or orchestration process."""
    engine = _load_engine(args.cards)
    arcana = ArcanaService(ArcanaConfig(enabled=args.arcana, master_seed=args.arcana_seed))
    if args.actor not in engine.cards:
        raise ValueError(f"Unknown actor {args.actor!r}")
    _emit({
        "type": "ready",
        "protocol_version": "political-sandbox-jsonl-1.0",
        "actor": args.actor,
        "commands": ["event", "decide", "outcome", "advance_time", "state", "quit"],
    })
    for line_number, line in enumerate(sys.stdin, start=1):
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            command = request.get("command")
            if command == "event":
                response = engine.apply_event(args.actor, _event(request["data"]))
            elif command == "outcome":
                response = engine.apply_outcome(args.actor, _outcome(request["data"]))
            elif command == "advance_time":
                response = engine.advance_time(args.actor, int(request["days"]), float(request.get("workload", 0.0)))
            elif command == "decide":
                response = _decision_payload(engine, args.actor, request, arcana)
            elif command == "state":
                response = {
                    "state": asdict(engine.runtime[args.actor].state),
                    "relationships": {key: asdict(value) for key, value in engine.runtime[args.actor].relationships.items()},
                    "turn": engine.runtime[args.actor].turn,
                }
            elif command == "quit":
                _emit({"type": "bye", "actor": args.actor})
                return 0
            else:
                raise ValueError(f"Unsupported command: {command!r}")
            _emit({"type": "result", "command": command, "data": response})
        except Exception as exc:  # JSONL keeps the session alive after a bad command.
            _emit({"type": "error", "line": line_number, "error": str(exc)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kfrage-sim",
        description="Political sandbox cards, decisions and reproducible scenarios.",
    )
    parser.add_argument("--cards", default=str(DEFAULT_CARDS), help="canonical persona-card JSON")
    parser.add_argument("--arcana", action="store_true", help="enable ARCANA Petit Etteilla advisory readings")
    parser.add_argument("--arcana-seed", type=int, default=0, help="master seed for reproducible ARCANA readings")
    sub = parser.add_subparsers(dest="command", required=True)

    actors = sub.add_parser("actors", help="list runnable actors")
    actors.add_argument("--json", action="store_true")
    actors.add_argument("--pretty", action="store_true")
    actors.set_defaults(func=cmd_actors)

    card = sub.add_parser("card", help="show one full card and initial runtime")
    card.add_argument("actor")
    card.add_argument("--json", action="store_true")
    card.add_argument("--pretty", action="store_true")
    card.set_defaults(func=cmd_card)

    validate = sub.add_parser("validate", help="validate the canonical card deck")
    validate.add_argument("--json", action="store_true")
    validate.add_argument("--pretty", action="store_true")
    validate.set_defaults(func=cmd_validate)

    decide = sub.add_parser("decide", help="run one AI-supplied JSON decision request")
    decide.add_argument("actor")
    decide.add_argument("--request", required=True, help="JSON file or - for stdin")
    decide.add_argument("--pretty", action="store_true")
    decide.set_defaults(func=cmd_decide)

    protocol = sub.add_parser("protocol", help="print the AI JSON request contract and example")
    protocol.set_defaults(func=cmd_protocol)

    scenarios = sub.add_parser("scenarios", help="list bundled runnable scenarios")
    scenarios.add_argument("--json", action="store_true")
    scenarios.add_argument("--pretty", action="store_true")
    scenarios.set_defaults(func=cmd_scenarios)

    run_scenario = sub.add_parser("run-scenario", help="run a bundled scenario")
    run_scenario.add_argument("scenario", choices=sorted(SCENARIOS))
    run_scenario.add_argument("--seed", type=int)
    run_scenario.add_argument("--runs", type=int, default=10000)
    run_scenario.set_defaults(func=cmd_run_scenario)

    play = sub.add_parser("play", help="persistent JSONL session for an AI client")
    play.add_argument("actor")
    play.set_defaults(func=cmd_play)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        _emit({"type": "error", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

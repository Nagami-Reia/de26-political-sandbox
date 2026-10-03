#!/usr/bin/env python3
"""Apply a transparent pollster observation layer to a latent event effect.

This does not reproduce proprietary pollster algorithms. It translates one
latent scenario delta into pollster-specific central releases using disclosed
fieldwork cadence plus explicitly labelled retention/rounding assumptions.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = HERE / "pollster_observation_models_2026.json"


def round_grid(value: float, grid: float) -> float:
    units = Decimal(str(value)) / Decimal(str(grid))
    return float(units.quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal(str(grid)))


def project(last_value: float, latent_delta: float, retention: float, grid: float) -> dict[str, float]:
    continuous = last_value + latent_delta * retention
    return {
        "last_value": last_value,
        "latent_delta": latent_delta,
        "retained_delta": round(latent_delta * retention, 3),
        "continuous_central": round(continuous, 3),
        "published_central": round_grid(continuous, grid),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pollster", required=True)
    parser.add_argument("--last", required=True, type=float)
    parser.add_argument("--delta", required=True, type=float)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()
    payload = json.loads(args.model.read_text(encoding="utf-8"))
    spec = payload["pollsters"][args.pollster]["our_observation_assumptions"]
    retention = spec.get("retention", spec.get("retention_projection"))
    result = project(args.last, args.delta, retention, spec["publication_grid_pp"])
    print(json.dumps({"pollster": args.pollster, **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

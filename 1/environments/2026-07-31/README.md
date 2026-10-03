# CDU/CSU future environment — 2026-07-31

This directory is a **forecast-origin snapshot**, not a forecast and not a reconstruction of a later outcome.

## Cut-off discipline

- Information state closes at **23:59 CEST on 31 July 2026**.
- Later pages may be used only when they explicitly document an event that had already occurred by the cut-off.
- Later appointments, election results, and retrospective interpretations are excluded from the state.
- `OBSERVED` means publicly verifiable. `INFERRED_RESOURCE` is a conservative institutional inference. `UNKNOWN` is deliberately left unresolved.

## Files

- `DOSSIER.md` — narrative map of the cabinet, CDU/CSU parliamentary group, CSU system and CDU state-government systems.
- `environment.json` — machine-readable institutional graph and actor resource inventory.
- `SOURCE_LEDGER.md` — evidence register with source type, date and what each source can support.
- `OPEN_QUESTIONS.md` — black boxes that future research or personality plug-ins must not silently fill.
- `observed_updates_through_2026-09-18.json` — append-only observations after the cut-off, with source IDs and directional resource effects.
- `CURRENT_RESOURCE_ANALYSIS_2026-09-18.md` — current resource assessment; inferences are explicitly separated from observations.
- `current_telemetry.json` / `current_telemetry_chart.html` — generated decision/event telemetry and its first-quadrant chart.

Later observations never overwrite the information available at the forecast origin. A correction to a fact that already pre-dated the cut-off is recorded explicitly as `OBSERVED_CORRECTION`.

## Modelling boundary

The environment owns offices, institutional powers, public signals, visibility and event constraints. Personality plug-ins may decide how an actor interprets those inputs and chooses among allowed actions. They may not alter offices, invent loyalties, or read information that was not publicly or institutionally visible at the cut-off.

## Political-simulation 3.0 layer

`environment.json` now also contains:

- the institutional matrix of offices, permissions and rule strength;
- an explicitly modelled institutional logic;
- actor-specific Agency Horizon starting states;
- inactive feature flags for v3 shadow diagnostics.

Institutional-logic and Agency Horizon values are tagged
`MODEL_ASSUMPTION_SHADOW_ONLY`. They are not reported facts, personality scores
or mental-health measures. In shadow mode they cannot change an actor's choice
or mutate the world. Actor rationality weights remain outside the environment in
`../../personality_cards_2026/rationality_profiles_v3.json`.

Activation order is fixed: perceived feasibility, then deviation cost, then
opponent response, and only then system-state mutation. Each activation requires
a baseline comparison and an isolated sensitivity run.

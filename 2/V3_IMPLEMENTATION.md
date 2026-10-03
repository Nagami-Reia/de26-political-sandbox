# Political simulation 3.0 implementation contract

## Status

Phase 1 (compatibility refactor) and phase 2 (shadow diagnostics) are implemented.
All v3 feature flags in the 2026-07-31 environment are deliberately `false`.

The current v3 trace can diagnose action-menu compression, instrumental versus
substantive conflict and system reproduction without changing the archived v2
decision.  This is the calibration baseline for later activation.

## Module ownership

| File | Owns | Must not own |
|---|---|---|
| `political_state.py` | world truth and transitions | actor preferences |
| `institutional_matrix.py` | offices, permissions, rules | action choice |
| `institutional_logic.py` | dominant necessity/rationality regime | personality |
| `action_repertoire.py` | objective-to-role menu | cognitive evaluation |
| `information_filter.py` | actor belief state | true consequences |
| `action_perception.py` | perceived feasibility and consideration | final choice |
| `decision_space.py` | perception/goal/strategy/style generation and outcome distributions | personality choice or world truth |
| `political_agency.py` | dynamic political action horizon | PSS control |
| `persona_v2.py` | stable decision logic, PSS and memories | world mutation |
| `rationality_evaluation.py` | dual evaluation and final comparison data | institutional facts |
| `system_feedback.py` | reproduction/erosion/transformation diagnostics | operational settlement |
| `simulation_orchestrator.py` | order, trace and feature gates | scenario facts |

## Generated decision-space contract

A `SimulationNodeV3` may continue to contain static `actions`, or it may contain
an empty action tuple plus a `DecisionEvent`. Generated mode requires an explicit
`DecisionSpaceGenerator`; no silent fallback to an empty/static menu is allowed.

```text
DecisionEvent
  -> PerceptionAssessment[]
  -> GoalAssessment[]
  -> GeneratedAction[] (StrategyTemplate x ExecutionStyleTemplate)
  -> Persona v2 choice
  -> OutcomeResolver
  -> PoliticalAction settlement
```

The event owns domain, tags, severity, ambiguity, observable signal variables and
per-strategy effect models. The library owns reusable political repertoires. The
card/runtime shape goal salience and style fit. Consequences remain environment
objects and are never invented by the personality card.

The actor does not choose a perception frame. The generator records a weighted
distribution and uses the dominant currently perceived frame to construct the
menu. Alternative frames stay in the trace for audit and later Bayesian updates.

Outcome weights are conditional simulation branches, not empirical probabilities.
An outcome seed can change settlement but is applied only after the deterministic
actor choice; changing the seed must not change the selected action.

## Compatibility guarantees

1. `ActionOption` v3 fields have neutral defaults.
2. Persona resource shortages remain hard constraints for v2 callers.
3. V3 active mode may request soft resource constraints; the shortfall remains
   visible in `resource_coverage` and choice feasibility.
4. Shadow mode delegates the authoritative choice to Persona v2.
5. System feedback is calculated but not applied unless its flag is enabled.
6. `roguelike_engine.py` and `free_agent_game.py` stay available for archived runs.

## Activation protocol

Activate only one mechanism per branch of a sensitivity run:

1. `institutional_logic_affects_choice` — use perceived feasibility in the final
   comparison while holding Agency Horizon neutral.
2. `agency_horizon_affects_choice` — enable actor-specific action-horizon effects.
3. `strategic_response_uses_perceived_menu` — rebuild every forecast actor's menu
   from that actor's information and institutional position. In phases 1-2 this
   path is diagnostic and does not acquire an invented payoff; a scenario must
   separately supply a calibrated strategic continuation value before it can
   affect the current actor's choice.
4. `system_feedback_mutates_world` — allow slow logic and agency state changes.

For each activation, archive the old and new chosen path, full node trace and the
six standard counterfactuals: no necessity claim, fully legible alternatives, no
career deviation cost, stronger organizational carrier, same actors under a
different logic, and different actors under the same logic.

## Epistemic warning

Institutional logic, Agency Horizon and reproduction types are model constructs.
They must be traceable to assumptions and sensitivity ranges, never presented as
observed psychological measurements or real-world probabilities.

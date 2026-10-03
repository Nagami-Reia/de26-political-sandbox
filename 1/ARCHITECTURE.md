# Environment/personality separation

## Party-interest layer

External parties do not require fictional leader personas. `party_interest.py`
models them as collective strategic actors built from programme positions,
common organisational interests and a dynamic role state. Union individuals
retain their persona cards and may receive a separately reported CDU/CSU common-
interest overlay. The overlay is opt-in through
`party_interest_affects_choice`; weight `0.000` is exact backward compatibility.

Party profiles never create world facts, legal permissions, voter reactions or
outcomes. Missing action metrics remain neutral and are reported diagnostically.

## Canonical v3 pipeline

New scenarios use `simulation_orchestrator.py` and emit
`political-simulation-3.0`.  The authoritative order is:

```text
HistoricalWorldState
  -> long / medium / short causal layers
  -> historical mechanism library
  -> risk decomposition + trigger
  -> generated historical event
  -> PoliticalState truth
  -> InstitutionalMatrix
  -> InstitutionalLogic
  -> DecisionEvent
  -> perception distribution (FoW + source trust + memory)
  -> active goal set (values + PSS + live goals)
  -> generated strategy families x execution styles
  -> objective action menu
  -> ActionRepertoireFilter
  -> InformationFilter
  -> ActionPerceptionFilter + AgencyHorizon
  -> Persona v2 / PSS
  -> strategic continuation input
  -> actor choice
  -> outcome distribution settlement
  -> world transition
  -> narrative/media route (parallel actor moves)
  -> audience interpretation + agenda ownership
  -> public legitimacy / support feedback
  -> operational feedback + system feedback
  -> polling / resources / relationships / institutions
```

`roguelike_engine.py` and `free_agent_game.py` are compatibility paths.  They
remain tested because archived results must stay reproducible, but no new
scenario should make either one its top-level engine.

For generated nodes, `decision_space.py` replaces a hand-authored action list
with a reusable action grammar. The scenario supplies the event and the factual
effect model for each applicable strategy; the generator supplies actor-specific
perceptions, live goals, strategy/style combinations and conditional outcome
branches. Perception is inferred, never selected by the actor. Personality chooses
an action deterministically. Only `OutcomeResolver` may sample a branch.

`historical_dynamics.py` is upstream of this pipeline. It must preserve causal
decomposition: a trigger is recorded separately and cannot be relabelled as the
whole cause. Its generated event exposes both a `DecisionEvent` for FoW/action
generation and a `WorldEvent` for actor-specific PSS and memory processing.

`narrative_media.py` is a separate route after a fact/event/outcome becomes
available. Facts never mutate public support directly. Actors choose frames and
channels in parallel; heterogeneous audiences then update interpretation from
source trust, evidence fit, identity fit, emotional force, reach, competition and
saturation. Only the settled narrative outcome may update public legitimacy,
support and poll state. `SystemFeedback.legitimacy_delta` remains an institutional
diagnostic and must not be silently treated as this public-legitimacy channel.

The v3 default is **shadow mode**.  Its diagnostics do not change the v2 choice.
The environment feature flags separately enable perceived-menu effects, agency
effects, system mutation and strategic perceived-menu forecasting.  Never turn
all channels on in one calibration change.

Actor-specific rationality weights live beside personality cards in
`personality_cards_2026/rationality_profiles_v3.json`; they are not environment
facts.  Institutional-logic and agency values carry explicit epistemic labels.

Every v3 node records objective, role-filtered and perceived menus, both
instrumental and substantive evaluation, the v2 persona decomposition, the
chosen action, operational transition, system reproduction classification,
logic/agency before and after, PSS and polling snapshots.

## Ownership boundary

| Concern | Environment owns it | Personality policy owns it |
|---|---:|---:|
| Historical initial resources | Yes | No |
| Formal offices and organization nodes | Yes | No |
| Information visibility and unknown black boxes | Yes | No |
| Timeline and next node | Yes | No |
| Allowed actions at a stage | Yes | No |
| Event-to-strategy effect models | Yes | No |
| Perception weights from accessible information | Generated | No |
| Strategy and style preference | No | Yes |
| Consequences/resource redistribution of an action | Yes | No |
| How visible inputs are weighted | No | Yes |
| Threshold/risk logic | No | Yes |
| Choice among allowed actions | No | Yes |
| Diagnostic utility values and rule explanation | No | Yes |

This boundary prevents a personality plug-in from “winning” by silently giving itself more resources or knowledge.

## Current personality stages

| Actor | Stage | Allowed actions |
|---|---|---|
| Merz | `preclosure_positioning` | hold default/bilateral channel; declare publicly |
| Merz | `bilateral_closure` | assert candidacy; delay/seek alternative |
| Wüst | `candidacy_choice` | challenge; withdraw and endorse the currently selected viable CDU target; remain ambiguous |
| Söder | `availability_signal` | signal conditional availability; stay quiet |
| Söder | `bilateral_closure` | continue contest; close for Merz; propose Söder |

Frei, Linnemann, Rhein, Hagel and Günther remain environment/organizational policies in this version. They can be promoted to the same plug-in API later without changing the three current actor policies.

## Current default plug-ins

- `merz_agency_gestaltung_v1`
- `wuest_ambition_control_acceptance_timing_v1`
- `soeder_evidence_bounded_resources_v1`

Every trace event records the `policy_id` that made the decision. Complete runs also record the active policy map and `environment_id`, so results from different personality/environment combinations cannot be confused.

Every full v3 scenario also has a mandatory end-report contract. It contains a
baseline plus one point after every node for (a) PSS pressure for each persona
card actually used and (b) latent and pollster-like realtime polling. The
orchestrator fails loudly when a full scenario omits either chart. Narrow unit
tests may explicitly opt into `ScenarioReportingPolicy.diagnostics_only()`;
that opt-out is not valid for a scenario report.

## Objective constitutional precheck

`checks/`, `procedures/` and `interaction/` form a parallel objective
environment. Persona cards may generate legally mistaken or impossible
intentions. The canonical orchestrator sends a selected action's optional
`Intent` through the compiled check registry only after the actor chooses it.
`BLOCKED`, `PENDING` and `ROUTED` actions remain in the trace but their proposed
world effects are not applied. The same gate also runs inside strategic
counterfactual response paths, preventing forecasts from silently assuming an
institutionally impossible action succeeded.

## Programmatic use

```python
from kfrage_model.kfrage_sim import Scenario, Simulation
from my_models import AlternativeWuest

state = Simulation(
    Scenario(seed=20240917),
    policies={"Wuest": AlternativeWuest()},
).run()
```

The alternative class must inherit `PersonalityPolicy` and implement `decide(context)`.

## Extension rule

For a static compatibility node, first add an action's consequences to the
environment, then expose it in `allowed_actions`, and only then let personality
policies choose it. For a generated node, add or reuse a strategy/style grammar
entry and give the event a `StrategyEffectModel`; do not hand-author every
strategy/style combination. A plug-in must never directly mutate `State`.

## Roguelike decision layer

`roguelike_engine.py` adds a reusable layer above the environment/personality split.
At every node the environment supplies actions and their effects on explicit state
variables. Every visible actor evaluates every changed variable, but only the node
owner chooses. The trace preserves, for every actor/action/variable:

- value before, delta and value after;
- actor-specific salience weight;
- direct interest contribution;
- distance from that actor's expected/target state;
- downside penalty and upside-option value;
- action feasibility and total comparison score.

Personality changes the weighting and nonlinear risk rule, never the facts or action
consequences. The deterministic baseline contains no random personality draw. Monte
Carlo may perturb only hidden information, implementation contingency and response.

## POMDG v2

The v1 variable scorer is now the bottom settlement layer. The operational engine is
a partially observable, multi-horizon dynamic game:

1. `political_state.py` owns reality, immediate/medium/long effects, scoped political
   capital, pressure tracks, pending effects and irreversible route locks.
2. `information_filter.py` produces actor-specific belief states from access, bias,
   source and confidence. Counterfactual observations never mutate real beliefs.
3. `strategic_game.py` evaluates nonlinear risk and hard thresholds, then searches a
   bounded opponent-response tree. Future actors choose through their own model,
   not through the current actor's preferences.
4. The scenario runner supplies only facts, assumed action consequences, access
   rules, personality parameters and the decision graph.

Utility is nested rather than a single linear sum. Horizon-specific contributions,
target fit, uncertainty/tail-risk, upside option value, political capital, pressure,
irreversibility and hard feasibility gates remain separately visible in the trace.
The deterministic baseline contains no random event draw. Structural pressure
triggers events when thresholds are crossed; stochastic sensitivity may vary noisy
signals and contingencies without randomizing personality.

## Parliamentary and routine-activity layer

`parliamentary_vote.py`, `political_activity.py`, `legislative_cycle.py` and
`realtime_polling.py` extend POMDG v2 without moving political facts into the
personality plug-in.

The legislative sequence is:

```text
actor decision
  -> public/committee debate signals
  -> bloc attendance + yes/no/abstention forecast
  -> explicit vote conclusion and uncertainty run
  -> settled vote result
  -> outcome-class feedback to people, factions, coalition and environment
```

Vote rules distinguish simple majority of votes cast, absolute member majority,
two-thirds of members and two-thirds of votes cast. A forecast always reports its
expected counts, required threshold, margin, conclusion, swingable blocs and the
status of every assumption. Monte Carlo changes only attendance, hidden defections
and late whip contingencies. The resulting run shares remain conditional model
frequencies, not real-world passage probabilities.

Routine political activity is represented in two separate steps:

1. a seeded calendar generates ordinary speeches, interviews, faction meetings,
   endorsements or visits from the actor's declared activity mix;
2. an attention function applies reach, issue salience, audience fit, credibility,
   competing news, saturation and novelty.

This allows an activity to consume time or political capital while producing no
detectable poll effect. Personality does not change randomly: the activity mix and
message remain actor-policy inputs, while occurrence, reach and news competition
are contingencies.

Every applied decision and event must call a `RealtimePollingTracker`. It records:

- the continuous latent support state after the event;
- a retained and publication-grid-rounded model nowcast;
- any real survey release separately as `OBSERVED` with a source id.

Therefore an unchanged chart point can mean that an event occurred but its effect
was below the publication grid. The standard run bundle ends with a first-quadrant
line chart generated from this append-only telemetry.

## Personality v2 ownership boundary

The v2 free-agent layer in `persona_v2.py` tightens the original boundary:

- the world owns the action menu, legality, consequences, resource truth and
  actor-specific information access;
- the card owns stable value order, control preference, conditional risk style,
  conflict style, stress resistance and recovery rules;
- the runtime owns mutable energy, pressure, confidence, control, identity
  integrity, event memory and relationship memory;
- the actor chooses the highest-scoring legal action from the menu; no card may
  encode a stage-to-action lookup.

Each action trace exposes six components: goal alignment, resource feasibility,
risk calculation, current-state modifier, memory modifier and identity
consistency. Hard institutional/resource requirements dominate all six scores.

The mutable layer is formally named the **Political State System (PSS)**. It is
implemented in `political_state_system.py`; no code or output should label it
"SAN". Card and state inputs use a single `0.000..1.000` scale with three-decimal
external precision. A world event is immutable input, an actor-specific impact is
calculated from resistance, sensitivity and memory resonance, and only that impact
may mutate the five political-state channels.

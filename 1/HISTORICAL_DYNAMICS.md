# Historical Knowledge and Event Generation

`historical_dynamics.py` models the production of political events without
reducing history to a trigger or letting an actor's personality create reality.

## Causal layers

```text
LongTermFactor        changes the risk terrain slowly
MediumTermChange      changes direction and momentum
ShortTermPressure     accumulates acute pressure and decays quickly
TriggerEvent          adds a short shock but is not relabelled as the cause
HistoricalMechanism   transforms interactions among current systems
```

All external intensities use `0.000..1.000`. Every risk result keeps separate
`base`, `long_term`, `medium_term`, `short_term`, `mechanisms`, and `triggers`
fields plus individual source contributions.

## Mechanism library

The initial reusable mechanisms are:

- **Security dilemma**: military buildup × threat perception raises security
  risk, reduces mutual trust and recursively increases perceived threat.
- **Commitment trap**: alliance commitment × reputation cost raises escalation
  and exit costs.
- **Miscalculation**: information uncertainty × decision urgency degrades
  decision quality and increases crisis risk.

Mechanisms are deterministic transformations of world state. They are not
historical laws and their coefficients remain model assumptions suitable for
sensitivity analysis.

## Event generation

`HistoricalEventGenerator` calculates risk before inspecting the event pool.
Candidates enter the pool only after their domain threshold is crossed. A
candidate may additionally require a matching trigger tag. In deterministic mode
the highest activation score is selected; stochastic mode samples among already
eligible candidates and represents external contingency only.

A trigger by itself can therefore fail to generate an event when the underlying
risk terrain remains low.

## Connection to actors

A `GeneratedHistoricalEvent` has two projections of the same occurrence:

```python
decision_event = generated.to_decision_event()
pss_event = generated.to_pss_event()
```

Apply `pss_event` to affected actors before deliberation, then give
`decision_event` to `DecisionSpaceGenerator`. This preserves the order:

```text
historical causality
  -> event
  -> actor-specific state impact and memory
  -> FoW perception
  -> goals
  -> strategies and styles
  -> deterministic actor choice
  -> contingent outcome
  -> narrative/media competition
  -> audience interpretation and public reaction
  -> historical-system feedback
```

`HistoricalWorldEngine.record_outcome()` writes the result back into system
variables and may create new long-, medium- or short-term factors. Failed
negotiations can therefore become future pressure without scripting the next
event.

## Scale bridge

Historical system variables use normalized `0.000..1.000`; the existing FoW
world uses `0..100`. `HistoricalWorldState.as_political_variables()` performs the
explicit conversion and propagates `information_uncertainty` into each observable
state variable.

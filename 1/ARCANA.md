# ARCANA v0.1

ARCANA is an optional, reproducible Petit Etteilla advisory subsystem. It is
off by default. It is neither a factual predictor nor a second decision engine:
the political model selects a rational baseline first, and ARCANA may change
only a viable near-tie through the actor's uncertainty, risk profile and current
Political State System (PSS) state.

## Run it

Global flags must precede the subcommand:

```bash
python3 -m kfrage_model --arcana --arcana-seed 1773 \
  decide Merz --request request.json --pretty
```

Without `--arcana`, the same request follows the pre-existing decision path.
The master seed, node id, actor id and occurrence number produce an independent
seed for each reading. `replay(run_id)` reconstructs the reading without
advancing the sequence.

For a two-actor node, add:

```json
{
  "node_id": "merz_soeder_conflict_01",
  "node_uncertainty": 0.720,
  "conflict_actor": "Soeder"
}
```

The two actors receive independent readings. Their advisory postures are then
compared. Each actor's pressure, control, confidence and risk appetite mediate
the collision. This interaction can alter a decision threshold, but the cards
do not directly mutate PSS. Only the realized political action and outcome may
apply pressure, memory or relationship changes.

## Historical boundary

`arcana/historical/` contains only rules visually checked against the 1773
scan. `arcana/interpretation/` and `arcana/hakoniwa/` contain our explicitly
non-historical mappings from old vocabulary to advisory motifs and actor
receptivity.

The implemented spread is the first `coup de douze`: mixed upright/reversed
orientation, shuffled 33-card pack, twelve laid cards, the next turned card and
the bottom card. Implemented historical relations are:

- the Forename meanings of all 32 piquet cards plus Carte Blanche;
- adjacent numbered meetings whose numbers sum to 31;
- exact same-rank multiples by count and orientation.

Surname, proximity, sequence, pairing, mute-card and timing rules remain
`SOURCE_REQUIRED`. They are deliberately absent instead of being completed from
modern generic cartomancy or by language-model inference.

## Output contract

Every simulation node always contains an `arcana` field. Disabled runs record
`DISABLED`. Enabled runs record:

1. seed, spread and every draw with orientation and position;
2. historical Forename resolution and its page-level provenance;
3. triggered meeting/multiple rules;
4. provisional identity echoes, clearly marked custom;
5. motif extraction, tally, recommendation and confidence;
6. actor receptivity, PSS snapshot, gamble threshold and action-score gaps;
7. whether advice changed, confirmed or failed to change the rational choice;
8. for conflict nodes, the second complete reading and the PSS-mediated
   interaction diagnosis.

The simulation trace remains the complete forensic and replay record. The
scenario-report compiler separately emits `arcana_report_trace`, a compact
presentation schema. Nodes keep short card and rule references; historical
meanings and rule provenance are stored once in shared dictionaries. PSS is a
first snapshot followed by per-actor deltas.

HTML is not stored in the simulation JSON and is never written by an LLM. A
deterministic renderer consumes `arcana_report_trace` when an HTML report is
requested. Initial DOM contains only Summary, Chronicle and collapsed node
rows. Opening a node mounts its complete ReadingTable; closing or opening
another node removes the former detail DOM. Consequently no more than one full
table exists at a time, even for a 500-node report. Explanatory sentences use
fixed templates and presentation labels never expose Python enum names.

```text
full simulation trace -> compact arcana_report_trace -> deterministic HTML
```

## Causal limits

- A large rational score gap cannot be overturned.
- Illegal or unavailable actions cannot be created.
- Identity-card assignments are provisional and do not alter historical card
  meanings.
- ARCANA randomness represents the optional oracle subsystem, not random
  personality.
- Outputs are game-state diagnostics, not claims about real politicians or
  real-world probabilities.

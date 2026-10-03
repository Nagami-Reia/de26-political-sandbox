# Party-interest layer: source and epistemic notes

Cutoff: **2026-09-23**. This file documents inputs; it does not claim that a
party has a single mind. Programme text is treated as the stable layer, recent
leadership or parliamentary statements as current signals, and every numeric
weight as a model assumption.

## Source classes

| ID | Status | Source |
|---|---|---|
| `UNION_WP_2025` | observed programme | [CDU/CSU 2025 election programme](https://www.cdu.de/wahlprogramm-von-cdu-und-csu/) |
| `UNION_COALITION_2025` | observed governing constraint | [CDU/CSU–SPD coalition agreement](https://www.cdu.de/downloads/koalitionsvertrag-2025/) |
| `CDU_MERZ_REFORMS_2026` | current leadership signal | [CDU: Merz on Europe and reforms](https://www.cdu.de/aktuelles/europapolitik/merz-regierungserklaerung-zu-europa-und-reformen/) |
| `SPD_WP_2025` | observed programme | [SPD 2025 government programme](https://www.spd.de/fileadmin/Dokumente/Beschluesse/Programm/2025_SPD_Regierungsprogramm.pdf) |
| `SPD_COALITION_2025` | observed governing constraint | [CDU/CSU–SPD coalition agreement, SPD copy](https://www.spd.de/fileadmin/Dokumente/Koalitionsvertrag_2025.pdf) |
| `SPD_KLINGBEIL_SECURITY_LINE` | leadership line, older than cutoff | [Klingbeil: security and peace in Europe](https://www.spd.de/aktuelles/detail/news/zeitenwende-sicherheit-und-frieden-in-europa/19/10/2022) |
| `GRUENE_WP_2025` | observed programme | [Greens 2025 election programme](https://www.gruene.de/artikel/zusammen-wachsen) |
| `GRUENE_FOREIGN_POLICY_2025` | observed party resolution | [Foreign policy for peace and freedom](https://cms.gruene.de/uploads/assets/Aussenpolitik-Fuer-Frieden-und-Freiheit-Beschluss-BDK-11-2025.pdf) |
| `GRUENE_SECURITY_2026` | current signal family | [Greens: securing peace in freedom](https://www.gruene.de/artikel/wir-sichern-frieden-in-freiheit) |
| `AFD_WP_2025` | observed programme | [AfD 2025 election programme](https://www.afd.de/wp-content/uploads/2025/02/AfD_Bundestagswahlprogramm2025_web.pdf) |
| `AFD_FOREIGN_POLICY_2025` | observed programme summary | [AfD foreign and defence policy](https://www.afd.de/wahlprogramm-aussen-verteidigungspolitik/) |
| `AFD_LEIPZIG_EVIDENCE_2026` | recent actor signal; not stable doctrine | [ZDF summary of party reactions](https://www.zdfheute.de/politik/ausland/drohne-vorfall-leipzig-eu-nato-reaktionen-100.html) |
| `LINKE_WP_2025` | observed programme | [Die Linke 2025 election programme](https://www.die-linke.de/bundestagswahl-2025/wahlprogramm/) |
| `LINKE_BUDGET_2026` | recent leadership signal | [Schwerdtner on the 2027 draft budget](https://www.die-linke.de/start/presse/detail/news/kanonen-statt-butter-politik-beenden) |
| `LINKE_PARTY_CONGRESS_2026` | recent collective signal | [Potsdam party-congress speeches](https://www.die-linke.de/partei/parteidemokratie/parteitag/potsdamer-parteitag/potsdamer-parteitag/reden/) |
| `BSW_WP_2025` | observed programme | [BSW short 2025 election programme](https://hb.bsw-vg.de/bsw-kurzwahlprogramm-zur-bundestagswahl-2025/) |
| `BSW_UKRAINE_2026` | recent party-board resolution | [BSW board on the fourth anniversary of the war](https://th.bsw-vg.de/beschluss-des-bsw-parteivorstands-zum-4-jahrestag-des-ukraine-kriegs/) |
| `BSW_LEIPZIG_2026` | recent Land-party signal | [BSW Saxony on the Leipzig drone case](https://bsw-vg-sachsen.de/bsw-unabhaengige-aufklaerung-drohnen-leipzig/) |
| `FDP_WP_2025` | observed programme | [FDP 2025 election programme](https://www.fdp.de/sites/default/files/2024-12/fdp-wahlprogramm.pdf) |
| `FDP_UKRAINE_NATO` | observed policy demand | [FDP on Ukraine and NATO](https://www.fdp.de/forderung/aufnahme-der-ukraine-die-nato) |
| `FDP_SUPPLEMENT_2025` | observed programme supplement | [FDP supplementary resolutions](https://www.fdp.de/sites/default/files/2025-01/2025-01-13_ergaenzende-beschluesse-zum-bundestagswahlprogramm-2025.pdf) |

## What is observed, inferred, or unknown

- **Observed:** programme directions, coalition commitments, and the cited
  public statements.
- **Model assumption:** every `0.000–1.000` importance weight, signed position,
  internal-cohesion value, electoral pressure and aggregation coefficient.
- **Unknown black boxes:** private bargaining mandates, internal vote counts,
  willingness to trade one programme objective for another, and reactions to a
  novel crisis. These must enter a scenario as information uncertainty or
  sensitivity ranges, not as invented facts.
- **Not encoded as personality:** rhetorical style, leader temperament and
  presumed emotional reactions. External parties are collective strategic
  actors only.

## Use contract

An environment must describe every action on the same policy axes and must add
signed party-interest and strategic impacts independently of menu order. Missing
metrics remain neutral and are emitted in diagnostics. The engine must never
infer that the first action is the responsible or programme-conforming action.


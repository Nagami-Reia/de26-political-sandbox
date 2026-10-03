# Grundgesetz check environment

This package is an objective, deterministic precheck layer. It does not score
actors, read beliefs, infer intentions, or prevent a persona from proposing an
impossible action. It runs only after an `Intent` has been selected and before
world effects are applied.

```text
persona / beliefs / PSS -> Intent
                              |
objective WorldState -> constitutional registry
                              |
                 PASS / BLOCKED / PENDING / ROUTED
                              |
                  institutional resolver -> world effects
```

The registry uses direct intent indexing. It does not scan or ask a model to
interpret the Grundgesetz during a run. The same objective context and intent
produce the same result.

## Implemented first tranche

| Rules | Implemented checks |
|---|---|
| Art. 30, 35, 37 | Land default competence; administrative/emergency assistance; federal coercion |
| Art. 58 | Countersignature and the expressly listed exceptions |
| Art. 62-66 | Federal Government composition, Chancellor election, minister appointment/dismissal, guideline/portfolio/cabinet competences, defence command, incompatibilities |
| Art. 67-69 | Constructive vote of no confidence, confidence motion/dissolution window, deputy and caretaker government |
| Art. 83-86 | Default Land execution, Land execution on federal commission, federal direct administration, supervision, regulations and individual instructions |
| Art. 87 | Creation of federal authorities and constitutional special-domain routing |

Special administration domains are recognized for routing, but detailed rules
under Arts. 87a-91e are not yet fully compiled.

## Deliberately not inferred from the GG

- motion-signature thresholds, agenda placement and other Bundestag procedure;
- details of the Federal Government's rules of procedure;
- ministry portfolios and statutory delegations at a particular date;
- ordinary federal and Land administrative law;
- coalition agreements, party statutes and political conventions;
- disputed doctrine or Federal Constitutional Court jurisprudence;
- actual vote counts, attendance, office holders or factual emergencies.

Those belong in separate parliamentary, government, statutory, party,
coalition or factual-world layers. A missing layer must remain visible in the
`CheckBundle`; it must not be replaced with an invented constitutional rule.

## Version lock

The compiled source version is the official text last amended by Article 1 of
the Act of 22 March 2025 (BGBl. 2025 I No. 94). The supplied PDF and the official
`gesetze-im-internet.de` pages showed the same version when this package was
compiled on 21 September 2026.

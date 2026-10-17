# Hakoniwa

Hakoniwa is an auditable political decision sandbox. It separates world facts,
institutions, incomplete information, actor-specific personality/PSS, strategic
interaction, party interests, media narratives, outcomes, and feedback.

## Download

- `00_FULL_PORTABLE_APP.zip` — recommended complete package.
- `01`–`07` — smaller topical packages for inspection or selective use.
- `SHA256SUMS.txt` — integrity hashes for every downloadable ZIP.
- `UPLOAD_PLAN.md` — exact replacement list for this release.

Unzip the full package, open `AI_START_HERE.md`, then run:

```bash
python3 -m hakoniwa validate --pretty
python3 -m hakoniwa actors
python3 -m hakoniwa scenarios
```

ARCANA is optional and disabled unless explicitly enabled. Scenario reports and
caches are generated locally and are not shipped in the source archives.

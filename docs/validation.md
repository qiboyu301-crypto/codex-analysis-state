# Release validation

## Review fixes — 2026-10-22

Runtime commit `77064fa26967691d8f752cd29824affb3fddbb86` passed clean wheel
installation, **21 behavioral tests** (0 failures, 0 skipped), and the three-turn
CLI example. The environment matches the initial validation below. There were
no resource-package declaration warnings and no model calls.

Four new regressions cover changed published descriptions, data rewrites with
updated metadata facts, raw context-only inputs used as computational sources,
and legitimate same-turn dependencies published together. The first two review
issues were reproduced against the initial installed package before fixing them.

The `review_fix_validation` record in
[evidence/validation.json](../evidence/validation.json) preserves this result and
artifact hashes alongside the original source-preparation evidence. Validation
applies to the recorded source commit, not automatically to later changes.

## Initial source preparation — 2026-10-22

Clean-environment validation passed for runtime/build source
commit `928a6aa0d28885a428305ebf6328240ec27ab5b5`, version `0.1.0.dev0`.
The original results below are retained as a historical validation snapshot.

| Check | Result |
|---|---|
| Source archive and wheel build | Passed; resource-package declaration warnings resolved |
| Install wheel into a new virtual environment | Passed |
| Behavioral tests against the installed wheel | **17 passed**, 0 failures, 0 skipped |
| Three-turn CLI demo outside the source checkout | Passed |
| Skill Creator frontmatter/scaffold validator | Passed |
| Local documentation links and unmodified StateM source hashes | Passed |

The installed module was loaded from the new environment's `site-packages`, not
from the source tree. Validation cleared inherited Python module paths.

Tested environment: Linux x86_64, kernel 5.15.0, glibc 2.35, Python **3.12.13**;
pandas **3.0.6**, PyArrow **26.0.0**, NumPy **2.5.4**, python-dateutil **3.0.0**,
six **1.17.0**, tzdata **2026.5**. Other supported Python versions and operating
systems have not been validated in this release preparation.

The tests cover complete historical membership, display changes, temporary
definition expiry, restoring earlier standing state, stale raw/derived inputs,
changed scripts and requests, missing historical reads, publication ordering,
and workspace paths containing spaces. Numeric helper checks cover tied ranks
and equal allocation after group deduplication.

The worked example preserved three candidates across all turns. January's
display was North/South. Temporary February measurements displayed North/West
and totaled 260, with no candidate entrants or exits. The next turn restored
January and totaled 240.

Artifact identities and a compact result record are in
[evidence/validation.json](../evidence/validation.json). Reproduce the mechanics
with `bash scripts/validate_release.sh`; dependency resolution can change over
time, so compare the emitted dependency list when comparing environments.

These checks made **zero model calls**. They do not establish live Codex skill
discovery, model-driven task completion or benchmark accuracy. Those remain
separate public-trial/research checks in the roadmap.

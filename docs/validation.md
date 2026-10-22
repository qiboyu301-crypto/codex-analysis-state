# Release validation

Clean-environment validation passed on **2026-10-22** for runtime/build source
commit `928a6aa0d28885a428305ebf6328240ec27ab5b5`, version `0.1.0.dev0`.
Subsequent source-preparation commits only record these results in documentation
and evidence; the validated runtime and packaging sources are unchanged.

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

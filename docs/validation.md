# Release validation

This source-preparation version has not yet completed clean-environment runtime
validation. Run `bash scripts/validate_release.sh` on the designated validation
server before treating the first stage as complete.

The validation script builds a wheel and source archive, installs the wheel in
a fresh environment, runs behavioral tests against the installed package, and
executes the three-turn demo from outside the checkout. It also checks the
skill's required frontmatter and repository-local documentation links.

Validation makes no model calls and cannot establish live Codex behavior or
benchmark accuracy. Record the source commit, Python/dependency versions,
test count and outcome here after execution. Live Codex skill discovery and a
model-driven example are separate checks in the public-trial roadmap.

# Codex Analysis State

Explicit analysis definitions, historical data selection, and replayable Python
calculations for multi-turn data analysis with Codex CLI.

[中文说明](README.zh-CN.md) · [Quickstart](docs/quickstart.md) ·
[Method](docs/method.md) · [Historical results](docs/results.md) ·
[Validation](docs/validation.md) · [Maintainer contributions](docs/maintainer-contributions.md)

When a later request changes a metric or time window, keep track of what should
change and what should stay fixed. The extension separates the population being
analyzed, the measurement definition, historical comparison results, and display
limits. It stores useful tables with descriptions and replays calculations before
publishing them for the next request.

This is an independent research project. Codex CLI supplies the model and tools;
this package supplies a project-scoped skill and a small workflow adapter built
on the attributed [StateM runtime](https://github.com/henryqin1997/statem).

## Historical case studies

Two separate Netflix task2 experiments motivated this extraction:

| Experiment | Before | After | Interpretation |
|---|---:|---:|---|
| Native vs. analysis extension | 13/34 (38.24%) | 27/34 (79.41%) | One task, one run per arm; compute budgets were not aligned |
| Initial vs. iterated development workflow | 1/34 (2.94%) | 29/34 (85.29%) | Reference-informed tuning on the same development task |

These are historical measurements of predecessor workflows. The standalone
package has not been benchmarked as equivalent to either frozen experiment.
The development case is not an independent held-out test. Broader results show
both gains and regressions; see [results and limitations](docs/results.md).

## Install from source

Use Python 3.11 or newer in a virtual environment. Commands below use a POSIX
shell. Codex CLI is installed and authenticated separately for live model use.

```sh
git clone https://github.com/qiboyu301-crypto/codex-analysis-state.git
cd codex-analysis-state
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

## Try the three-turn example

```sh
analysis-state demo /tmp/analysis-state-demo
```

Choose a new output directory. This runs hand-written calculations over six
synthetic rows; it makes **zero model calls** and is not an agent accuracy test.

| Turn | What changes | Expected result |
|---|---|---|
| 1 | Establish January candidates; show two leaders | Three retained members; North and South displayed |
| 2 | Temporarily measure February, keeping original membership | Three retained members; North and West displayed; total 260 |
| 3 | Use the standing window again | January restored; three members; total 240 |

Inspect `turns/NNN/answer.json`, `analysis_receipt.json`, `verification.json`,
and the published `data_index.json` inside the generated workspace.

## Use with Codex CLI

Create a **new** workspace from a directory of your input data:

```sh
analysis-state init /tmp/my-analysis --data /path/to/input-tables
cd /tmp/my-analysis
codex
```

Keep the package virtual environment active when launching Codex. The init
command copies and fingerprints your raw files, installs the skill under
`.agents/skills/analysis-state`, and adds workspace instructions. In Codex, ask:

```text
Use $analysis-state to analyze these tables. First establish the complete
candidate population; show only the top five. Later I will change the metric
while continuing to refer to this original group.
```

The skill guides `inspect -> solve -> retain -> verify -> handoff`. It uses
`analysis-state begin`, `next`, `run`, and `complete`. The runtime does not
configure a model, alter your account, or install global Codex settings.
See [step-by-step usage](docs/quickstart.md).

## Scope

The checks establish input identities, fresh execution, retained data facts,
and declared dataset reads. They do not establish semantic correctness,
automatic error correction, or exact agreement between a saved computation and
Codex's final reply. The package runs ordinary Python under existing permissions;
it is not a sandbox. Use a fresh workspace for a new input snapshot.

The first release focuses on tabular, multi-turn analysis. Historical benchmark
evaluation infrastructure, model gateways and production services are outside
this package. [Method and architecture](docs/method.md) explain what is enforced
and what remains an analyst/agent responsibility.

## Maintainer and upstream contributions

Maintained by [qiboyu301-crypto](https://github.com/qiboyu301-crypto). Related
upstream work includes five AgentScope issue reports, one submitted AgentScope
fix PR, and two Wren AI SQL-correctness reports. See the
[contribution record](docs/maintainer-contributions.md) for reproductions,
community follow-up, and the status of each contribution.

## Development and attribution

Run `bash scripts/validate_release.sh` to build and install the wheel in a clean
environment, execute behavioral tests, and run the example outside the source
tree. The script makes no model calls. Current verification status is recorded
in [validation.md](docs/validation.md).

See [CONTRIBUTING.md](CONTRIBUTING.md), [ROADMAP.md](ROADMAP.md), and
[CHANGELOG.md](CHANGELOG.md). Code is Apache-2.0. StateM and research-code origins,
source commits, and changes are recorded in [NOTICE](NOTICE) and
[PROVENANCE.json](PROVENANCE.json).

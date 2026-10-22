# Quickstart

Install the package from the repository as shown in the README. Keep the
virtual environment active for `analysis-state` and when launching Codex.

## Deterministic example

```sh
analysis-state demo /tmp/analysis-state-demo
```

Use a new path for each run. The installed package includes the synthetic
fixture and three worked calculations, so the command works outside the
source checkout. It makes no API calls. Inspect the JSON printed by the command
and the generated workspace:

```text
raw/sales.csv
.agents/skills/analysis-state/
.analysis-state/                  # active request and StateM runtime
data_index.json                   # published data IDs
data/t001/candidates.parquet
data/t001/candidates.meta.json
memory.md
turns/001/                        # definition, selection, script, review, receipts
turns/002/
turns/003/
```

Turn 1 retains North, South and West. Its display has North and South. Turn 2
uses February measurements temporarily, preserving all three members even
though South's revenue falls below the original eligibility threshold. The
leaders become North and West, but candidate entrants/exits are both empty.
Turn 3 inherits January again and reports 240. This distinguishes a fixed
historical population from a current measurement and a display projection.

## Live Codex usage

Create a directory containing only the raw input files you want copied. Then:

```sh
analysis-state init /tmp/my-analysis --data /path/to/input-tables
cd /tmp/my-analysis
codex
```

The output directory must not exist yet. It includes a frozen copy of raw data;
editing that copy invalidates selected input fingerprints. For new input data,
initialize a new workspace. Inputs are copied locally, with no model configured
or called by this command.

Invoke `$analysis-state` in your Codex request. The workspace has the complete
skill and supporting references. Discovery uses the documented project location
`.agents/skills`; if it is not visible in the current session, restart Codex.
See [OpenAI's skill documentation](https://learn.chatgpt.com/docs/build-skills).

Use the same workspace for follow-up questions. The script and replay use the
Python environment in which the package was installed. If Codex cannot find
`analysis-state`, activate that environment and restart the CLI from it.

## Manual command sequence

The skill performs this sequence on behalf of the user:

1. Save the current request in a file and run `analysis-state begin --request-file request.md`.
2. Write the active turn's `analysis.json`, `selection.json`, and `plan.md`.
3. Run `analysis-state next solve` to pin effective definitions and inputs.
4. Write `solve.py`, `review.md`, and a retention plan; use `analysis-state run` to inspect calculations.
5. Run `analysis-state next retain` and finalize exports and `retention.json`.
6. Run `analysis-state next verify` to replay in a fresh Python process.
7. Review output and update `memory.md`, then run `analysis-state next handoff`.
8. Run `analysis-state complete`, then deliver the checked results to the user.

Commands return JSON, except `run`, which streams the calculation's output.
`analysis-state status` reports the current turn and allowed next nodes. For
schema details, see the installed skill's `references/workflow.md` and
`references/reusable-data.md`.

Before completing a turn, return to inspect for input/definition changes, solve
for calculation changes, or retain for export changes; replay after changes.
After completion, corrections use a new turn. A finished workspace can be moved
and the next turn will bind to its new path. Do not move an unfinished workflow;
its active run is tied to the original workspace and interpreter.

## Version and evaluation boundaries

The package requires Python 3.11+. The release validation record lists the
environment actually tested; untested platforms should not be assumed covered.
Model selection, authentication, permissions and accounting remain in Codex.

The demo is a deterministic worked example. It verifies mechanics, not model
interpretation or accuracy. Live agent behavior must be evaluated separately
using the actual final replies and explicit access/compute controls.

# Turn files and commands

All paths below are relative to the workspace. Commands may be run from any
subdirectory inside it. The active turn number comes from `analysis-state status`.

## Inspect

Write `turns/NNN/analysis.json`:

```json
{
  "updates": {
    "window": {"value": "2026-01", "reason": "The user requested January."},
    "display_limit": {"value": 2, "reason": "Show the two leaders."}
  },
  "temporary": {},
  "checks": ["Use all retained candidates before applying the display limit."]
}
```

On later turns, empty `updates` inherits the previous published standing state.
Use `temporary` for a change explicitly limited to this request. Optional
`restore_from_turn: 1` starts from turn 1's standing definitions before applying
updates and temporary overrides. Natural-language checks are review obligations;
the runtime does not implement them automatically.

Write `selection.json`:

```json
{
  "inputs": [
    {"data_id": "t001_candidates", "role": "historical_result", "purpose": "Original membership", "reason": "The request keeps the earlier group."},
    {"file": "raw/sales.csv", "purpose": "Current measurements", "reason": "Recompute revenue for the requested month."}
  ]
}
```

For first-turn raw analysis, select only raw files. Each input has exactly one
of `file` and `data_id`. Dataset roles are `data` (default), `historical_result`
and `context`; the first two must be loaded during replay. A no-input request
uses `inputs: []` and a nonempty `notes` explanation.

Write `plan.md` with the inherited rules, requested changes, source identities
and required answer fields. Run `analysis-state next solve`. The runtime writes
the effective definitions and input fingerprints to receipts. Read these;
do not edit them.

## Solve and retain

Example script structure:

```python
import json
import pandas as pd
from codex_analysis_state import data

state = data.analysis_context()
sales = pd.read_csv(data.raw_path("raw/sales.csv"))
current = sales.loc[sales["month"].eq(state["window"])]
answer = {"window": state["window"], "revenue": float(current["revenue"].sum())}
print(json.dumps(answer, allow_nan=False))
```

Run `analysis-state run` after preparing `retention.json` if the script exports
tables. Write `review.md` with concrete checks and their independent evidence,
then run `analysis-state next retain`. Complete the retention plan and exports
as explained in [reusable-data.md](reusable-data.md).

## Verify and complete

`analysis-state next verify` removes only the current unpublished turn's
derived exports, reruns `solve.py`, writes `answer.json`, and validates exports
and required dataset reads. Replays time out after 300 seconds. Review the
actual result, update `review.md` and `memory.md`, and run:

```sh
analysis-state next handoff
analysis-state complete
```

`complete` requires StateM's handoff node, rechecks evidence, updates the
catalog, and records publication. The next request can then begin. Published
turns cannot be replayed in place. Corrections to completed work are new turns.

Before publication, repair with `next inspect` for definitions/inputs,
`next solve` for calculations, or `next retain` for exports. Repeat the normal
transitions, including fresh replay. Errors are visible and stop the transition.

The standalone adapter records the request text supplied to `begin`; it does
not independently attest to a Codex transcript. It also does not intercept
Codex's final response. Evaluate actual final responses separately when running
model benchmarks.

# Retained data and descriptions

Adapted from the longDS-codex analysis protocol. Read this when deciding which
results to keep or selecting a historical result.

`data_index.json` maps published IDs to their name, summary, `created_turn`,
Parquet `file` and `metadata_file`. Inspect relevant descriptions before
choosing inputs. The `analysis-state complete` command publishes the index;
analysis scripts do not edit it.

Select an exact `data_id` in `selection.json`. A historical entity set, current
measurements and a fixed comparison baseline may come from three different
sources. When a multi-view table contains a union, identify which membership
column or predicate selects the requested set. A displayed Top-K is not the
complete retained population.

## Retention plan

Write `turns/NNN/retention.json` before running a script that exports data:

```json
{
  "keep": [
    {"name": "candidates", "reason": "Later requests refer to this complete original group."}
  ]
}
```

A pure query usually needs no new data:

```json
{"keep": [], "skip_reason": "Query the published candidates without a new reusable transformation."}
```

Prefer zero or one table. The ordinary-turn budget is two. More than two
requires an `exception_reason` and an `independent_reason` on every kept item.
Initialization is exempt from this count budget, but every table needs a reason.
These reason fields are review material, not automatic proof of necessity.

## Export API

Use `from codex_analysis_state import data`. `data.save_dataset` requires a
pandas DataFrame, a lowercase name with underscores, and a description:

```python
data.save_dataset(candidates, "candidates", {
    "summary": "Complete January candidate membership and revenue",
    "sources": [{"file": "raw/sales.csv", "usage": "January measurements"}],
    "processing_steps": ["Select January", "Apply the revenue eligibility rule"],
    "semantics": {
        "grain": "One row per region",
        "population": "All qualifying January regions",
        "filters": "month = 2026-01 and revenue >= 60",
        "metrics": {"revenue": "January revenue in currency units"}
    },
    "usage": {"purpose": "Keep the original group for later comparisons", "scope": "standing"}
})
```

The first turn produces `t001_candidates`,
`data/t001/candidates.parquet`, and `data/t001/candidates.meta.json`.
The helper records actual row count, columns, dtypes, hashes and source
identities. It binds the description to the effective analysis definitions.
Use `{ "data_id": "t001_candidates", "usage": "Original group" }` for a
published source in a later description. Sources must be selected inputs or
another explicitly retained current-turn product. `context` inputs cannot be
claimed as computational sources.

Retain complete working tables with full numeric precision. Do not save
multiple display-only copies or resave an unchanged historical set. A temporary
calculation may still produce a useful table, but label its scope accurately.
Do not turn temporary choices or unverified assumptions into standing rules.

## Historical reads

Use `data.load_dataset("t001_candidates")` for selected published tables.
It verifies the selected identity and records the read during formal replay.
Use `data.raw_path("raw/sales.csv")` to resolve selected raw inputs before
ordinary pandas reads. Previewing data before selection can use ordinary file
reads; solve.py must use the selected sources.

For a named historical group under a new measurement, take membership from the
historical group and measurements from the requested view. Compute membership
changes over full sets with `data.membership_change(previous, current)`, then
apply display limits. A fixed historical threshold retains its saved value;
a threshold defined over a current pool is recomputed with that formula.

Numeric helpers are conditional on the requested convention:

- `data.rank_percentiles(values)` implements average one-based rank divided by
  nonmissing count times 100. Use it only when that is the intended formula.
- `data.unique_group_weights(mapped_labels)` gives equal weights to distinct
  already-mapped groups. For A/A/B it returns A=0.5, B=0.5.

## Evidence boundaries

Fresh replay checks the script, selected inputs, derived outputs and required
published-table reads. Hashes identify artifacts; source declarations describe
intended lineage. Neither hashes nor a successful read prove that Python used
a table correctly or that the interpretation matches the user. Inspect the
actual computation and answer against independent evidence.

The standalone package has no filesystem sandbox or final-response interceptor.
The user's configured Codex permissions still apply. Historical benchmark
scores belong to frozen predecessor runs, not to this repackaged distribution.

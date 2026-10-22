# Method and implementation boundary

The package extracts a research protocol from longDS-codex. It uses the pinned
StateM runtime for transition ordering and supplies a portable adapter and
analysis data layer. No model API client or proxy is included.

## Four separate bindings

| Binding | Example | Stored evidence |
|---|---|---|
| Entity set | The complete original candidate group | Published Parquet ID and membership field |
| Measurement | February revenue for those entities | Effective analysis definitions and solve.py |
| Historical comparison | January values or a fixed past threshold | Explicit earlier data IDs and source fields |
| Display | Show the top two rows | A separate display limit applied after calculation |

`analysis.json` carries persistent `updates`, explicitly turn-only `temporary`
overrides, and optional `restore_from_turn`. The plan transition resolves these
into standing and effective definitions. Historical dataset selection is a
separate decision; restoring definitions does not automatically pick a data
version.

## Five stages

| Transition | Runtime check |
|---|---|
| inspect → solve | Validate definition structure and pin concrete input identities |
| solve → retain | Require the computation script and review material |
| retain → verify | Replay the script; validate retained tables, descriptions and required historical reads |
| verify → handoff | Reject stale scripts, inputs, outputs or receipts |
| handoff → complete | Recheck evidence, publish the catalog and close the turn |

StateM supplies the transition engine. `workspace.py` supplies portable setup,
active-request binding and publication. `data.py` is the adapted described-data
protocol. The skill supplies the analysis guidance. `PROVENANCE.json` identifies
the predecessor files and pinned upstream runtime.

## What the checks mean

Hashes check artifact identity. Replaying `solve.py` checks fresh execution.
Required dataset reads check that declared historical tables were loaded.
Parquet metadata checks row counts, columns, dtypes and associated descriptions.

These checks do not prove that the chosen interpretation is right, that a
loaded table materially affected the calculation, or that a source declaration
is a complete causal lineage. Natural-language checks in `analysis.json` are
review obligations. They are not automatically executed as assertions.

The wrapper records the request supplied to `begin`; it does not independently
verify that text against a Codex transcript. `answer.json` records computation.
It does not replace the user's actual answer or certify that the final reply
includes every required value. Historical experiments scored actual agent
finals through a separate runner.

## What changed during extraction

- Fixed container paths became portable workspace-relative `raw/` identities.
- A small `raw_path` helper resolves and checks selected raw inputs.
- A standalone command manages turn identity and enforces handoff before publication.
- The workflow is generated for the installed Python environment.
- The skill was shortened and moved detailed schemas into references.

The existing StateM implementation remains attributed. The repackaged version
is not asserted to reproduce predecessor model scores without new experiments.
It uses normal filesystem permissions and a single sequential active turn.
It does not include the old benchmark container isolation or recovery runner.

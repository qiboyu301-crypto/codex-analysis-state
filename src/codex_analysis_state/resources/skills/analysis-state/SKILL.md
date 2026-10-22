---
name: analysis-state
description: Analyze supplied tabular data across successive requests with explicit analysis definitions, historical result selection, and replayable Python calculations. Use in an initialized analysis-state workspace when later requests reuse or change earlier analysis.
---

# Analysis state

Run `analysis-state status` from the analysis workspace. If the command is
unavailable, follow the package installation instructions before proceeding.
The workspace must already have been created with `analysis-state init`.

Preserve four separate things: the entity set being analyzed, the current
measurement definition, the historical comparison result, and the rows shown
to the user. A change to one does not automatically change the others.

## Start or resume a request

If there is an unfinished turn, continue it. For a new request, write its text
to a file outside `turns/` and run `analysis-state begin --request-file FILE`.
This records the supplied request and returns the new `turns/NNN/` directory.
Do not edit that recorded request. Materially changed requests need a new turn
after the current turn is completed; ask the user if their intended handling
is ambiguous.

Follow `inspect -> solve -> retain -> verify -> handoff`, using
`analysis-state next NODE`. The transition commands perform the checks. Read
[workflow.md](references/workflow.md) for the file formats and repair path.

## Inspect definitions and historical inputs

Read the current request, `memory.md`, and relevant entries in `data_index.json`.
Inspect matching `.meta.json` descriptions and data when needed. Choose a
historical version by its analytic purpose, not by recency alone.

Write `analysis.json` with persistent `updates`, explicitly turn-only
`temporary` overrides, and meaningful `checks`. Unchanged definitions carry
forward. Replacing a method normally persists; comparison alone does not make
it temporary. `restore_from_turn` restores standing definitions, while data
versions are selected separately.

Record concrete inputs in `selection.json`, and a short `plan.md`. Bind named
historical populations to their complete saved membership. Separate eligibility
and retained-candidate limits from display limits. A fixed historical threshold
stays fixed when current measurements change unless the user changes it.

Run `analysis-state next solve`, then review `analysis_receipt.json.effective`
and the selected input identities.

## Compute and retain

Write `turns/NNN/solve.py` using `from codex_analysis_state import data`.
Read effective definitions with `data.analysis_context()`. Read selected
published tables with `data.load_dataset(ID)`; resolve selected raw files with
`data.raw_path("raw/FILE")`. The script must load its own inputs so it can run
in a fresh process. Use `analysis-state run` to execute it with the active
turn environment.

Compare complete sets before limiting display rows. When measuring an earlier
group under a new definition, keep its historical IDs and compute the new
measurements. Preserve requested boundaries, denominators, units, tie rules,
and full numeric precision. Record independently grounded checks in `review.md`.
Print exactly one JSON answer to stdout; send diagnostics to stderr.

Run `analysis-state next retain`. Read
[reusable-data.md](references/reusable-data.md) before writing `retention.json`
and adding useful exports through `data.save_dataset`. A pure query may retain
zero tables. Preserve complete reusable results and their explanations.

## Verify and hand off

Run `analysis-state next verify` to replay the script in a fresh process.
Compare `answer.json`, saved tables and receipts with the actual request.
Check required answer fields, membership, measurement versions and units.
Successful replay establishes execution consistency, not semantic correctness;
loading a table alone does not prove that the calculation uses it correctly.

Update `review.md` and concise `memory.md` with confirmed definitions and IDs.
If a defect remains, return to inspect, solve or retain, then replay again.
Run `analysis-state next handoff` followed by `analysis-state complete` to
publish verified data. Do not write receipts or `data_index.json` manually.
Answer the user with the reviewed results and necessary qualifications.
`answer.json` is computational evidence, not a substitute for the actual reply.

This workflow runs ordinary Python with the user's existing permissions.
Keep published history unchanged. It does not authorize sending data elsewhere,
installing unrelated tools, or overriding the user's sandbox decisions.

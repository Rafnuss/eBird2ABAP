# Research project guidance

This is a small scientific analysis project for one researcher. Favor short reusable functions, explicit intermediate tables, linear runnable scripts, and reproducible checks. Do not add documentation sites, public-release machinery, web applications, complex configuration, or extra folder layers.

## Working layout

- `eBird2ABAP/`: scientific functions for conversion, shared events/effort, pentads, taxonomy, and local reporting.
- `scripts/`: EBD report, explicit taxonomy update, and official KML audit.
- `tests/`: offline regression checks; `check_notebooks.py` executes all notebook defaults.
- `notebook/`: active research notebooks using package functions and synthetic offline defaults. Keep them runnable, output-free, and explicit about real input/version/exports. Legacy originals stay in ignored `archive/notebooks/`.
- `docs/`: only methods, taxonomy, and unresolved-issue working notes. README is the entry point.
- `data/`, `export/`, `archive/`, `references/`: preserve existing research inputs, generated outputs, legacy notebook copies, and papers. Do not reorganize or discard unrelated user data.

## Scientific policy

Follow `docs/methods.md` and `docs/taxonomy.md`. Shared groups are one event, unioned by original Avibase concept, with deterministic representative metadata and all member IDs preserved. Conflicts stay visible. Only complete Stationary/Traveling events establish effort; overlapping time counts once, midnight and five-day boundaries are explicit, and missing quantities remain missing.

Spatial containment is a screen conditional on reported locality/distance, not a track proof. Pentads use signed northwest corners and south/east shared-edge assignment. Do not add website label overrides. Unknown accuracy, detection order, habitat coverage, nocturnal effort, receiving accounts, and ADU mapping are not inferred.

Declare EBD taxonomy explicitly. The active source is eBird 2025 and target eBird 2026/AviList v2026. Require the published code link and identical concept ID; no name-only, fuzzy, parent-species, legacy-file, or ADU fallback. Failed freshness checks mean unverified, not up to date.

## Execution

```bash
uv sync --frozen
uv run python tests/run_all_tests.py
uv run ruff check eBird2ABAP scripts tests
uv run --group notebooks python tests/check_notebooks.py
```

Use an explicit EBD file or release directory. Sampling metadata is not a species input. Prefix reads can truncate groups/checklists and are smoke tests only. Reports stream observations but retain checklist metadata. Raw EBD, raw taxonomy snapshots, and real generated reports stay ignored and local. No automatic publishing or uploads.

Inspect Git status before editing. Preserve prior user changes. Keep prose and list items on one source line. Update concise working notes and meaningful scientific regressions when behavior changes. Track genuinely unresolved inputs/assumptions in `docs/issues.md` rather than claiming that passing tests resolve them.

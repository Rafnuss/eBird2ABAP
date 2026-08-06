# Development guide

## Tests

Run the pentad test suite from the repository root:

```bash
uv run python tests/run_all_tests.py
```

Individual tests are in `tests/`.

## Notebooks

- `notebook/pipeline.ipynb`: end-to-end EBD-to-ABAP workflow.
- `notebook/eBird2Card.ipynb`: conversion exploration.
- `notebook/species_match.ipynb`: eBird-to-ABAP species matching.
- `notebook/pentad_naming_convention.ipynb`: pentad ID conventions.
- `notebook/pentad_generation_test.ipynb`: regional pentad grids.

## Repository layout

- `eBird2ABAP/`: package code and packaged species mapping.
- `tests/`: script-based package tests.
- `data/`: local inputs; see [the data guide](data.md).
- `archive/`: legacy material outside the active workflow.
- `export/`: generated outputs.
- `references/`: supporting literature.

Use `uv sync` after dependency changes. Keep transformation-rule changes reproducible and record the EBD release used for analysis.

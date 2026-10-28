# eBird2ABAP

Research tools for turning eBird observations into inspectable atlas-card candidates. This is a small working analysis project: reusable Python functions, a few runnable scripts, regression tests, and explicit scientific assumptions. It is not an operational ABAP submission service.

## Setup

Python 3.11.8+ (safe archive extraction); run from this repository:

```bash
uv sync --frozen
uv run python tests/run_all_tests.py
```

`uv.lock` fixes the environment. NumPy/pandas and the spatial libraries support conversion; the development environment also includes matplotlib for reports, openpyxl for taxonomy updates, and Ruff for basic checks. No documentation generator, application framework, or release publishing workflow is installed. Notebook support is an optional environment group.

## Research notebooks

Keep and edit the notebooks in `notebook/`. Install the lightweight execution environment with `uv sync --frozen --group notebooks`, then select `.venv` in Positron or your notebook editor. For a browser editor, run `uv run --group notebooks --with jupyterlab jupyter lab notebook` explicitly; JupyterLab is not a core dependency.

- `pipeline.ipynb`: current conversion stages and intermediate tables.
- `eBird2Card.ipynb`: shared-event, timing, effort, and spatial diagnostics.
- `species_match.ipynb`: direct eBird/AviList matches, unresolved concepts, and reference manifest.
- `comparison.ipynb`: candidate counts and an explicitly selected external summary; no assumed ADU equivalence.
- `heatmap.ipynb`: independent-event and elapsed-effort coverage by pentad.
- `pentad_naming_convention.ipynb`: northwest-corner examples and round trips.
- `pentad_generation_test.ipynb`: consistent grids for an explicit polygon or local boundary file.

Defaults use offline synthetic data and leave exports disabled. Set `EBD_file`, source taxonomy, and row limit explicitly for real data. Existing legacy explorations are preserved in ignored `archive/notebooks/` and Git history. No obsolete dependencies, embedded pipeline implementations, or legacy ADU files are needed.

```bash
uv run --group notebooks python tests/check_notebooks.py
```

This executes every notebook from top to bottom without saving outputs into the tracked files.

## Explore a release

```python
from eBird2ABAP import read_EBD, add_avilist_taxonomy, ebd2chk, chk2valid_card

observations, members = read_EBD('data/ebd/your-release/', return_members=True)
issues = add_avilist_taxonomy(observations, ebird_version='2025', return_unmatched=True)
checklists = ebd2chk(observations)
card_starts = chk2valid_card(checklists)
```

Use `nrows=10000` in `read_EBD()` for an initial smoke test. A prefix can truncate checklists and shared groups; its counts are not complete-release estimates. Inputs are explicit `.txt`, `.txt.gz`, or release directories; sampling reports are not species inputs. Project 1056 headers are normalized automatically.

For a repeatable local HTML/CSV diagnostic report:

```bash
uv run python scripts/report_ebd.py \
  --input data/ebd/your-release/ \
  --ebird-version 2025 \
  --output export/report
```

Add `--nrows 10000` for a labelled prefix. Omit it to read the entire supplied file in observation chunks. Reports contain input/reference hashes, taxonomy outcomes, independent/shared-event counts, missing effort, spatial-screen statuses, and candidate-card counts. They stay local under `export/`; checklist metadata still grows in memory with dataset size.

## Convert after inspecting the issues

```python
from eBird2ABAP import ebird2abap

cards = ebird2abap(
    'data/ebd/your-release/',
    JSON_file='export/cards.json',
    ebird_version='2025',
    exportCSV=True,
)
```

Strict taxonomy checks stop on unresolved concepts and write diagnostics. Explicit `strict_taxonomy=False` retains original Avibase keys with blank AviList metadata and a status. Receiving account values are supplied with `observer_email=` and `observer_no=` when known.

The current reference chain is **eBird 2025 → eBird 2026 / AviList v2026**. Source taxonomy is declared, never inferred from observation dates. No ADU mapping, old-file fallback, parent-species roll-up, or name-only AviList match is used. [Taxonomy notes](docs/taxonomy.md) give the update command and diagnostic statuses.

Shared groups count once with all member IDs preserved. Only complete Stationary/Traveling events establish effort; overlapping time within an observer/pentad counts once. Unknown distance, habitat coverage, nocturnal effort, positional accuracy, and detection order remain unknown. Spatial evidence is a conservative screen, not a track. See [methods and references](docs/methods.md) and [open issues](docs/issues.md).

## Folder layout

| Path | Purpose |
| --- | --- |
| `eBird2ABAP/` | Reusable scientific functions and the single active taxonomy bundle |
| `notebook/` | Editable, output-free research workflows using current functions |
| `scripts/` | Explicit report, taxonomy update, and official KML audit scripts |
| `tests/` | Offline scientific regression checks |
| `docs/` | Three working notes: methods, taxonomy, unresolved issues |
| `data/` | Local EBD inputs and reference sources; existing research data are preserved |
| `export/` | Local generated tables and reports, ignored by Git |
| `archive/` | Existing legacy work and retired notebook copies, ignored by Git |
| `references/` | Supporting papers |

Existing proposal/reference/data files are retained. No new application or site folder is needed. Keep a prototype web application in its own repository if it develops beyond a local experiment.

```bash
uv run ruff check eBird2ABAP scripts tests
```

The two v0.4 bug fixes are committed separately. Current metadata remains `0.5.0.dev0` to identify the changed analysis behavior; it does not imply a public release. No report or package is automatically uploaded.

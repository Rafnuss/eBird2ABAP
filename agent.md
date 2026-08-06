# Agent guidance for eBird2ABAP

## Project purpose

This repository is a research-oriented Python package for converting eBird Basic Dataset (EBD) observations into ABAP full-protocol cards and for working with SABAP 5-minute pentads. Prioritize clear, reproducible, inspectable changes over production-style abstraction.

## Repository map

- `eBird2ABAP/ebird2card.py`: EBD loading, species mapping, checklist filtering, card discovery, and ABAP-shaped export.
- `eBird2ABAP/pentad.py`: coordinate/pentad conversions, polygon construction, and regional grid generation.
- `eBird2ABAP/matched_species.csv`: packaged eBird taxon concept ID to ABAP species mapping.
- `tests/`: script-based tests for pentad behaviour.
- `notebook/`: exploratory and pipeline notebooks; use these to understand intended intermediate data objects.
- `data/`: raw EBD inputs, reference data, and generated project data. Keep raw eBird data under `data/ebd/`, with general releases separate from Project 1056 exports.
- `archive/`: legacy material and archived Kenya Bird Map data; do not use it as an active input without explicit review.
- `export/`: generated outputs and examples.
- `references/`: supporting references.
- `pyproject.toml`, `uv.lock`, `.python-version`: reproducible `uv` environment and dependency configuration.

## Working style

- Inspect existing notebooks and intermediate tables before changing transformation logic.
- Keep analysis code linear and easy to run section-by-section.
- Prefer pandas/NumPy/GeoPandas/Shapely idioms already used in the project.
- Preserve existing column names and output schemas unless the change explicitly requires a migration.
- Keep functions small and transparent; avoid introducing wrappers or defensive layers that hide the data flow.
- Use `here`-like reproducible paths in notebooks where practical, but remember that the package’s existing download helper uses paths relative to the process working directory.
- Do not silently change taxonomy mappings, pentad naming conventions, observer defaults, or card-validity rules.

## Important domain assumptions

- A pentad is a 5-minute by 5-minute cell.
- Pentad IDs encode latitude, longitude, and quadrant using `_`, `a`, `b`, or `c`.
- `pentad2polygon()` follows the named pentad ID, while `latlng2polygon()` follows the exact coordinate cell; they can differ at naming-convention boundaries.
- A valid card requires complete species reporting, an accepted protocol, pentad validity, positive duration, and at least two hours across a rolling five-day window for one observer and pentad.
- The current output hard-codes the ABAP observer email/number and defaults `InclNight` and `AllHabitats` to zero. Treat these as project assumptions, not universal truth.

## Setup and verification

Use `uv` for development and notebook work. The project pins Python to 3.11 and keeps the package and notebook dependencies in `pyproject.toml`.

```bash
uv python install 3.11
uv sync
```

Run commands through the managed environment:

```bash
uv run python tests/run_all_tests.py
uv run jupyter notebook
```

For an interactive shell:

```bash
source .venv/bin/activate
```

When dependencies change, update the lockfile and environment:

```bash
uv lock
uv sync
```

The project includes `openpyxl` because the taxonomy notebooks read Excel workbooks. If tests cannot run, report the missing dependency explicitly rather than treating that as a code failure.

## Data handling

- Raw EBD files can be very large and are ignored by Git.
- Follow `docs/data.md` to download the latest or a specific African EBD release; do not commit the raw archive or extracted EBD file.
- `eBird2ABAP.DEFAULT_EBD_DIR` is the explicit default download location (`data/ebd`, relative to the current working directory). Pass `output_dir=` to `download_EBD()` when using another location.
- With no release arguments, `download_EBD()` checks the previous month and up to three older months, since the newest archive may not yet be published. Explicit release arguments do not fall back silently.
- EBD-reading functions must receive an explicit input file or extracted release directory; do not make `ebird2abap()` or `read_EBD()` guess which release to use. Build paths from `DEFAULT_EBD_DIR` when appropriate.
- `ebird2abap()` and `read_EBD()` accept an EBD `.txt`, `.txt.gz`, or extracted release directory. For a directory, they select the single species-level file and ignore filenames containing `sampling`; ambiguous directories should raise an error.
- `read_EBD()` accepts standard EBD files (`.txt` or `.txt.gz`) and the species-level African Bird Atlas Project 1056 report. It normalizes the project's `PROTOCOL NAME` column to `PROTOCOL TYPE` before applying the shared workflow.
- The Project 1056 sampling report is checklist-level metadata and is not a direct input to the species-card conversion workflow. The project report is already project-specific; do not add implicit project filtering while making unrelated changes.
- Do not commit private or restricted EBD-derived data.
- Generated exports and local data should remain untracked unless they are intentionally curated examples.
- `archive/` is retained for possible future reference but is outside the active data workflow.
- The data layout is `data/ebd/` for package-downloaded all-African releases, `data/ebd/project_1056_african_bird_atlas/` for Project 1056 exports, `data/reference/` for source taxonomies/ABAP/geography, and `data/generated/` for derived files.
- When modifying species matching, record the source taxonomy release and inspect unmatched taxa with `add_ADU(..., return_unmatched=True)`.
- EBD records provide `SCIENTIFIC NAME` and Avibase-based `TAXON CONCEPT ID`; `eBird2ABAP/matched_species.csv` is the curated runtime mapping from taxon concept to ABAP `ADU`.

## Change checklist

Before handing off a change:

1. Check `git status` and avoid modifying unrelated user data.
2. Update the README when public usage, output fields, or assumptions change.
3. Run the pentad test suite when dependencies are available.
4. For card-pipeline changes, test with a small EBD sample (`read_EBD(..., nrows=...)`) before attempting a full release.
5. Summarize any unrun tests, data assumptions, or known limitations.

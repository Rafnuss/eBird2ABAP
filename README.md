[![PyPI version](https://img.shields.io/pypi/v/eBird2ABAP.svg)](https://pypi.org/project/eBird2ABAP/) [![GitHub stars](https://img.shields.io/github/stars/Rafnuss/eBird2ABAP.svg)](https://github.com/Rafnuss/eBird2ABAP)

# eBird2ABAP

`eBird2ABAP` converts eBird Basic Dataset (EBD) observations into ABAP full-protocol card records. It also provides utilities for working with SABAP pentads.

The conversion combines complete eBird checklists from one observer and pentad when they provide at least two hours of effort within five days.

## Installation

From the repository root:

```bash
uv python install 3.11
uv sync
```

Run notebooks with:

```bash
uv run jupyter notebook
```

## Workflow

1. Obtain general EBD data or a Project 1056 export as described in [the data guide](docs/data.md).
2. Point the converter to the extracted release folder or its `.txt`/`.txt.gz` file:

```python
from eBird2ABAP import ebird2abap

ebird2abap(
    "data/ebd/ebd_AFR_relJun-2026/",
    JSON_file="export/ebd_AFR_relJun-2026_cards.json",
    exportCSV=True,
)
```

For Project 1056, use its species-level export folder:

```python
ebird2abap(
    "data/ebd/project_1056_african_bird_atlas/",
    JSON_file="export/project-1056_cards.json",
)
```

See [the conversion reference](docs/conversion.md) for card rules, output fields, species matching, and limitations.

## Pentad utilities

```python
from eBird2ABAP import latlng2pentad, pentad2latlng, pentad2polygon

pentad = latlng2pentad([-1.2864], [36.8172])[0]
lat, lng = pentad2latlng(pentad)
polygon = pentad2polygon(pentad)
```

Pentads use the documented northwest-corner rule in all hemispheres. See [pentad naming and geometry](docs/pentads.md) for sources, shared-edge assignment, and known disagreements with published website labels. Regenerate northern/western grids and card IDs produced by older versions.

## Tests

```bash
uv run python tests/run_all_tests.py
```

## Documentation

- [Data guide](docs/data.md): EBD downloads, Project 1056 exports, and data layout.
- [Conversion reference](docs/conversion.md): processing rules, ABAP output fields, and limitations.
- [Development guide](docs/development.md): notebooks, tests, and repository layout.

## Data and contribution notes

Do not commit raw EBD downloads, private data, generated exports, or notebook checkpoints. Keep changes to transformation rules reproducible by recording the EBD release and relevant notebook or script.

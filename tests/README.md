# Package tests

Run all committed test scripts with `uv run python tests/run_all_tests.py`. The runner discovers `test_*.py` and returns a failing exit code if any script fails.

| File | Coverage |
| --- | --- |
| `test_card_selection.py` | Failed-window recovery, non-overlapping successful windows, the exact two-hour/five-day thresholds, empty selection, eligibility flags, separate observer/pentad effort, and an independent deterministic reference |
| `test_pentad_conversions.py` | Coordinate/ID examples, vectors, and round trips in all four quadrants |
| `test_pentad_polygons.py` | Cell sizes, containment, vectors, and agreement between named and coordinate-derived cells |
| `test_pentad_bounds.py` | Six reference bounds, distinguishing logical IDs from exceptional published KML labels |
| `test_pentad_consistency.py` | Published northwest-corner examples; equator/meridian cells; exact shared edges; 5,000 deterministic random points; generated grids; no implicit website overrides |

The external KML is not needed for the offline suite. To audit it independently, run `uv run python scripts/audit_pentad_kml.py /path/to/all_download.kml /tmp/pentad-audit`. See [the naming reference](../docs/pentads.md) and [KML audit](../docs/pentad-kml-audit.md).

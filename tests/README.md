# Research checks

Run all tests with `uv run python tests/run_all_tests.py`. The runner discovers `test_*.py` scripts and fails if any script fails. No raw EBD files, credentials, or live downloads are needed.

| File | Coverage |
| --- | --- |
| `test_checklist_effort.py` | Shared provenance/unions/conflicts; elapsed-time union; missing effort; midnight and five-day clipping; calendar-date normalization; spatial screens; cross-pentad conflict flags; empty reports; report chunk invariance and sample labels |
| `test_card_selection.py` | Taxonomy-independent card-window regressions, empty selections, eligibility flags, separate observer/pentad effort, and an independent deterministic reference |
| `test_card_pipeline.py` | Synthetic EBD to JSON/CSV; five-day boundaries; two-hour threshold; failed windows; empty inputs; observer/pentad separation; protocol/completeness/spatial rules; shared effort; unresolved taxonomy; missing distance; Project 1056 protocol normalization; gzip/folder inputs; archive traversal and HTTP errors |
| `test_taxonomy_mapping.py` | Direct concept-ID and published-code matching; no parent/name fallback; source versions; reports; ambiguous references; bundle hashes; failed network updates |
| `test_pentad_consistency.py` | Published northwest-corner examples; all quadrants; exact grid edges; 5,000 deterministic random round trips; generated grid coherence; website exceptions do not override the regular rule |
| `test_pentad_conversions.py` | Coordinate/ID examples, vector inputs, selected round trips |
| `test_pentad_polygons.py` | Cell size, containment, vectors, numerical agreement in every quadrant |
| `test_pentad_bounds.py` | Six reference polygon bounds |

The card-window tests compare the optimized implementation with a simple independent reference on 30 deterministic random date/effort series. Network tests use mocked responses and in-memory archives. The suite uses the standard-library `unittest` runner for new pipeline tests and retains the existing pentad scripts.

Run only the pipeline regressions with `uv run python tests/test_card_pipeline.py`.

The pentad rule and its references are documented in [pentad naming](../docs/methods.md). The optional `scripts/audit_pentad_kml.py` compares an external official KML against the same rule; the 185 MB source is not needed for the offline suite. Website labels that disagree with the rule remain explicit audit differences, not naming overrides.

Run `uv run --group notebooks python tests/check_notebooks.py` to execute all seven notebooks on their default offline synthetic inputs. Executed copies are temporary; source notebooks remain output-free.

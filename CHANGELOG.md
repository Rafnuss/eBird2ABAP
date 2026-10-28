# Changelog

## 0.5.0.dev0 — unreleased development

### Changed

- Preserve source Avibase concepts and use the explicit eBird 2025 → eBird 2026 / AviList v2026 chain. Require direct published-code and concept-ID agreement; ship a checksummed reference bundle with provenance and reports. No ADU, legacy-file, name-only, or parent fallback.
- Collapse shared events deterministically, retain the union of source concepts and all member IDs, and exclude contradictory event metadata from card effort. Representative-account grouping does not imply individual participation credit.
- Count only complete Stationary/Traveling effort, union overlapping timers, split midnight crossings, clip five-day endpoints, and normalize imported date fields to calendar days. Supplementary observations do not inflate effort.
- Preserve unknown distance, accuracy, nocturnal effort, habitat coverage, detection sequence, and receiving-account details. Add candidate-validation markers and separate stable record indexes from biological detection order.
- Retain and update all seven research notebooks to current functions, with explicit source versions, synthetic offline defaults, and opt-in exports. Preserve older explorations in the archive. Keep a local HTML/CSV quality report with source hashes and diagnostics; simplify documentation to the README and three working notes. Remove Sphinx, Pages, installed CLI, and publishing machinery.
- Keep one locked research environment, explicit Python exports, basic linting, and scientific regression tests. Keep 0.5.0.dev0 as an analysis version marker, without public-release automation.

### Compatibility

Regenerate derived cards and grids. Output keys and unknown-value semantics differ from older versions; the package exports atlas-card candidates, not validated ADU-based submissions. Updated notebooks remain active; their older copies are preserved locally under ignored archive/notebooks/ and in Git history. No release has been published by these changes.

## v0.4 branch — unreleased bug fixes

### Fixed

- Correct pentad IDs north of the equator and west of Greenwich using the documented northwest corner. Align coordinate polygons, decoded centres, and generated grids in every quadrant; explicitly assign shared edges south/east. Add published examples, 5,000 deterministic random checks, and a reproducible audit of the supplied 372,499-cell KML. Regenerate affected grids and card IDs from earlier versions. The 293 published label/geometry disagreements remain audit findings rather than naming overrides. See [the naming reference](docs/methods.md).

- Recover later valid five-day cards after an earlier window fails the two-hour threshold. Successful windows remain non-overlapping; empty selections keep their schema. Replace the quadratic date-distance matrix with sorted endpoint searches and cumulative effort, with eight independent selection regression tests.

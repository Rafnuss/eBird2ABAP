# Open questions and checks

The code bugs below have regression tests; missing scientific evidence remains visible rather than guessed.

## Fixed behavior

- Northwest-corner pentad encoding in every quadrant, verified against all 372,499 KML geometries within source precision. The 293 irregular published labels are not overrides.
- Failed card windows no longer skip later valid starts; successful windows remain non-overlapping.
- Empty selections and exports; Project 1056 date fields containing a time component; missing start times stay unknown.
- Shared groups count once, retain all member IDs and the union of Avibase concepts, and flag conflicting metadata.
- Only complete Stationary/Traveling events establish effort. Overlapping intervals count once, split at midnight, and are clipped to card periods.
- Missing or incomplete distance totals remain unknown. GPS accuracy, true detection sequence, nocturnal effort, habitat coverage, and account defaults are not invented.
- Taxonomy requires the explicit eBird source release, published AviList code link, and identical concept ID. No ADU, name-only, parent, fuzzy, or legacy-file fallback.
- Taxonomy reports, input/reference hashes, deterministic tests, safe archive extraction, and explicit output paths support repeatability.

## Still unresolved

- The authoritative Avibase → ADU mapping and receiving-server acceptance are unavailable. JSON contains intermediate candidate records.
- Some source taxa, especially ISSFs with parent-name EBD representations, cannot be directly linked with the available API fields. Reports distinguish missing links and concept disagreements.
- Python requests to the AviList website return HTTP 403. Freshness is unverified when a check fails, never implicitly up to date.
- Selected localities and total distance do not prove pentad containment. Tracks or field evidence are needed for exact validation.
- Member IDs do not establish equal observer participation. Representative-account grouping does not identify a stable party across different shared events.
- Simultaneous checklists in different pentads are now flagged as `CROSS PENTAD TIME CONFLICT` and counted in the report. They cannot be allocated confidently from clocks alone; the flag does not silently change their duration or eligibility. Review flagged cards before interpreting hours across cells.
- True detection order/hour, identification proficiency, habitat coverage, nocturnal activity, and positional accuracy cannot be reconstructed from the current fields.
- Reports stream observations but retain checklist metadata in memory. Conversion reads all observations; full African-release memory/performance has not been benchmarked.
- The verified ID format covers African longitudes; full-globe three-digit longitudes and poles are outside scope.

## Run checks

```bash
uv sync --frozen
uv run python tests/run_all_tests.py
uv run ruff check eBird2ABAP scripts tests
```

Tests use synthetic input, deterministic random coordinates, mocked network failures, and no private observations. A real-data report is a useful additional check, not proof that the unresolved items above have disappeared.

The earlier v0.4 bug-fix commits remain `48c8265` (pentads) and `1d3f377` (card windows). Current work is local research development, with no automatic publishing or public report upload.

Version `0.5.0` is the local research checkpoint containing these behaviors and notebook updates. The unresolved scientific inputs above remain open; a version tag does not establish server acceptance or resolve source ambiguity.

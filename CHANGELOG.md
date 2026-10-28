# Changelog

## Unreleased — v0.4

### Fixed

- Correct pentad IDs north of the equator and west of Greenwich using the documented northwest corner. Align coordinate polygons, decoded centres, and generated grids in every quadrant; explicitly assign shared edges south/east. Add published examples, 5,000 deterministic random checks, and a reproducible audit of the supplied 372,499-cell KML. Regenerate affected grids and card IDs from earlier versions. The 293 published label/geometry disagreements remain audit findings rather than naming overrides. See [the naming reference](docs/pentads.md).

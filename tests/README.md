# Pentad Module Tests

This directory contains comprehensive tests for the pentad module functions.

## Running Tests

To run all tests:

```bash
python tests/run_all_tests.py
```

To run individual test files:

```bash
python tests/test_pentad_conversions.py  # Coordinate <-> ID conversions
python tests/test_pentad_polygons.py     # Polygon generation
python tests/test_pentad_bounds.py       # Specific bounds validation
```

## Test Files

### `test_pentad_conversions.py`
Tests core conversion functions:
- `latlng2pentad`: Convert coordinates to pentad IDs
- `pentad2latlng`: Convert pentad IDs to center coordinates
- Round-trip consistency
- Vectorization support

### `test_pentad_polygons.py`
Tests polygon generation:
- `pentad2polygon`: Create polygons from pentad IDs
- `latlng2polygon`: Create polygons from coordinates
- Center/point containment
- Polygon size validation (5 arcminutes)
- Coherence between methods

### `test_pentad_bounds.py`
Validates exact bounds from KML data:
- 6 test cases covering edge cases
- Equator and prime meridian crossings
- All quadrants (N/S, E/W)
- High precision validation (≈1 meter accuracy)

Includes comprehensive documentation about pentad ID interpretation.

## Test Coverage

The tests verify:
- ✓ All quadrants (Southern/Northern, Eastern/Western)
- ✓ Equator crossing (lat = 0°)
- ✓ Prime meridian crossing (lng = 0°)
- ✓ Grid boundaries
- ✓ Vectorization with arrays
- ✓ Round-trip consistency
- ✓ Polygon containment
- ✓ Exact geometric bounds

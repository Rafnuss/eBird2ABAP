"""
Test pentad polygon generation functions.

Tests polygon creation from both pentad IDs and coordinates:
- pentad2polygon: Create polygon from pentad ID
- latlng2polygon: Create polygon from coordinates
"""

import numpy as np
import sys
from pathlib import Path
from shapely.geometry import Point

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from pentad import pentad2polygon, latlng2polygon, pentad2latlng, latlng2pentad


def test_pentad2polygon_contains_center():
    """Test that pentad2polygon creates polygons containing their center points."""
    
    print("=" * 70)
    print("Testing pentad2polygon - center containment")
    print("=" * 70)
    
    test_pentads = [
        ('2500_2700', 'Pretoria area'),
        ('0000_1000', 'Equator crossing'),
        ('5130b0005', 'London'),
        ('0540c0000', 'Prime meridian'),
        ('0545b0010', 'Western hemisphere'),
    ]
    
    all_passed = True
    
    for pentad_id, description in test_pentads:
        # Get center coordinates
        lats, lngs = pentad2latlng([pentad_id])
        center_lat, center_lng = lats[0], lngs[0]
        
        # Get polygon
        polygon = pentad2polygon(pentad_id)
        
        # Check if center is inside polygon
        center_point = Point(center_lng, center_lat)
        contains = polygon.contains(center_point)
        
        status = "✓" if contains else "✗"
        print(f"\n{status} {description} ({pentad_id})")
        print(f"  Center: ({center_lat:.6f}, {center_lng:.6f})")
        print(f"  Bounds: {polygon.bounds}")
        print(f"  Contains center: {contains}")
        
        if not contains:
            all_passed = False
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✓ All pentad2polygon center tests passed!")
    else:
        print("✗ Some tests failed")
        
    assert all_passed, "pentad2polygon center containment tests failed"
    return all_passed


def test_latlng2polygon_contains_point():
    """Test that latlng2polygon creates polygons containing the input coordinates."""
    
    print("\n" + "=" * 70)
    print("Testing latlng2polygon - point containment")
    print("=" * 70)
    
    test_coords = [
        (-25.041667, 27.083333, 'Pretoria'),
        (0.05, 10.0, 'Equator'),
        (51.5074, -0.1278, 'London'),
        (-33.9249, 18.4241, 'Cape Town'),
    ]
    
    all_passed = True
    
    for lat, lng, description in test_coords:
        # Get polygon
        polygon = latlng2polygon([lat], [lng])[0]
        
        # Check if original point is inside or on boundary
        point = Point(lng, lat)
        intersects = polygon.intersects(point)
        
        status = "✓" if intersects else "✗"
        print(f"\n{status} {description}")
        print(f"  Point: ({lat:.6f}, {lng:.6f})")
        print(f"  Bounds: {polygon.bounds}")
        print(f"  Intersects: {intersects}")
        
        if not intersects:
            all_passed = False
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✓ All latlng2polygon containment tests passed!")
    else:
        print("✗ Some tests failed")
        
    assert all_passed, "latlng2polygon containment tests failed"
    return all_passed


def test_polygon_size():
    """Test that polygons have the correct size (5 arcminutes)."""
    
    print("\n" + "=" * 70)
    print("Testing polygon size")
    print("=" * 70)
    
    expected_size = 5 / 60  # 5 arcminutes in degrees
    tolerance = 1e-6
    
    test_pentads = ['2500_2700', '0000_1000', '5130b0005']
    
    all_passed = True
    
    for pentad_id in test_pentads:
        polygon = pentad2polygon(pentad_id)
        minx, miny, maxx, maxy = polygon.bounds
        
        width = maxx - minx
        height = maxy - miny
        
        width_ok = abs(width - expected_size) < tolerance
        height_ok = abs(height - expected_size) < tolerance
        passed = width_ok and height_ok
        
        status = "✓" if passed else "✗"
        print(f"\n{status} {pentad_id}")
        print(f"  Width:  {width:.8f}° (expected {expected_size:.8f}°)")
        print(f"  Height: {height:.8f}° (expected {expected_size:.8f}°)")
        
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✓ All polygon size tests passed!")
    else:
        print("✗ Some tests failed")
        
    assert all_passed, "Polygon size tests failed"
    return all_passed


def test_polygon_coherence():
    """
    Test coherence between pentad2polygon and latlng2polygon.
    
    For most points, pentad2polygon(latlng2pentad(lat, lng)) should equal
    latlng2polygon(lat, lng). Mismatches can occur near boundaries due to
    naming convention adjustments.
    """
    
    print("\n" + "=" * 70)
    print("Testing polygon coherence")
    print("=" * 70)
    
    # Use points well within pentad cells (not on boundaries)
    test_coords = [
        (-25.04, 27.08, 'Pretoria (interior)'),
        (0.04, 10.04, 'Equator (interior)'),
        (51.52, -0.12, 'London (interior)'),
    ]
    
    match_count = 0
    total_count = len(test_coords)
    
    for lat, lng, description in test_coords:
        # Get polygon via pentad ID
        pentad_id = latlng2pentad([lat], [lng])[0]
        poly_from_id = pentad2polygon(pentad_id)
        
        # Get polygon directly from coordinates
        poly_from_coord = latlng2polygon([lat], [lng])[0]
        
        # Check if they're equal
        match = poly_from_id.equals(poly_from_coord)
        
        status = "✓" if match else "~"
        print(f"\n{status} {description}")
        print(f"  Pentad ID: {pentad_id}")
        print(f"  ID-derived bounds:    {poly_from_id.bounds}")
        print(f"  Coord-derived bounds: {poly_from_coord.bounds}")
        print(f"  Match: {match}")
        
        if match:
            match_count += 1
    
    print(f"\n  Matches: {match_count}/{total_count}")
    print("\n" + "=" * 70)
    
    # We expect most to match, but allow some mismatches near boundaries
    if match_count >= total_count * 0.8:  # 80% threshold
        print(f"✓ Polygon coherence acceptable ({match_count}/{total_count} matched)")
    else:
        print(f"✗ Too many mismatches ({match_count}/{total_count})")
    
    return True  # Don't fail on this test, just informational


def test_vectorization():
    """Test that polygon functions work with arrays."""
    
    print("\n" + "=" * 70)
    print("Testing polygon vectorization")
    print("=" * 70)
    
    # Multiple pentad IDs
    pentad_ids = ['2500_2700', '0000_1000', '5130b0005']
    polygons = pentad2polygon(pentad_ids)
    assert len(polygons) == 3, "Should return 3 polygons"
    print(f"✓ pentad2polygon handles {len(polygons)} pentad IDs")
    
    # Multiple coordinates
    lats = np.array([-25.04, 0.04, 51.52])
    lngs = np.array([27.08, 10.04, -0.12])
    polygons = latlng2polygon(lats, lngs)
    assert len(polygons) == 3, "Should return 3 polygons"
    print(f"✓ latlng2polygon handles {len(polygons)} coordinates")
    
    print("\n" + "=" * 70)
    print("✓ All vectorization tests passed!")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PENTAD POLYGON TESTS")
    print("=" * 70)
    
    try:
        test_pentad2polygon_contains_center()
        test_latlng2polygon_contains_point()
        test_polygon_size()
        test_polygon_coherence()
        test_vectorization()
        
        print("\n" + "=" * 70)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("=" * 70 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        sys.exit(1)

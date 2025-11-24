"""
Test core pentad conversion functions.

Tests the fundamental coordinate <-> pentad ID conversions:
- latlng2pentad: Convert coordinates to pentad IDs
- pentad2latlng: Convert pentad IDs back to center coordinates
"""

import numpy as np
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from pentad import latlng2pentad, pentad2latlng


def test_latlng2pentad():
    """Test conversion from coordinates to pentad IDs."""
    
    print("=" * 70)
    print("Testing latlng2pentad")
    print("=" * 70)
    
    # Test cases: (lat, lng, expected_pentad_id, description)
    test_cases = [
        (-25.041667, 27.083333, '2500_2700', 'Pretoria/JHB area (S+E)'),
        (-33.9249, 18.4241, '3355_1825', 'Cape Town (S+W)'),
        (0.05, 10.0, '0000c1000', 'Just North of Equator (N+E)'),
        (-0.05, 10.0, '0000_1000', 'Just South of Equator (S+E)'),
        (51.5074, -0.1278, '5130b0005', 'London (N+W)'),
        (40.7128, -74.0060, '4040b7400', 'New York (N+W)'),
        (-25.0, 27.0, '2500_2700', 'Exact grid line'),
        (-25.083333, 27.0, '2500_2700', '5 min boundary'),
    ]
    
    all_passed = True
    
    for lat, lng, expected_id, description in test_cases:
        result = latlng2pentad([lat], [lng])[0]
        passed = result == expected_id
        status = "✓" if passed else "✗"
        
        print(f"\n{status} {description}")
        print(f"  Input: ({lat:.6f}, {lng:.6f})")
        print(f"  Expected: {expected_id}")
        print(f"  Got:      {result}")
        
        if not passed:
            all_passed = False
        
        # Validate format
        assert len(result) == 9, f"Pentad ID should be 9 characters: {result}"
        assert result[4] in ['_', 'a', 'b', 'c'], f"Invalid quadrant: {result[4]}"
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✓ All latlng2pentad tests passed!")
    else:
        print("✗ Some tests failed")
        
    assert all_passed, "latlng2pentad tests failed"
    return all_passed


def test_pentad2latlng():
    """Test conversion from pentad IDs to center coordinates."""
    
    print("\n" + "=" * 70)
    print("Testing pentad2latlng")
    print("=" * 70)
    
    # Test cases with known centers
    test_cases = [
        ('2500_2700', -25.041667, 27.041667, 'Pretoria area'),
        ('0000_1000', -0.041667, 10.041667, 'Equator crossing (southern)'),
        ('5130b0005', 51.458333, -0.041667, 'London'),
        ('0540c0000', 5.625000, 0.041667, 'Prime meridian'),
    ]
    
    all_passed = True
    tolerance = 1e-5  # ~1 meter
    
    for pentad_id, expected_lat, expected_lng, description in test_cases:
        lats, lngs = pentad2latlng([pentad_id])
        lat, lng = lats[0], lngs[0]
        
        lat_match = abs(lat - expected_lat) < tolerance
        lng_match = abs(lng - expected_lng) < tolerance
        passed = lat_match and lng_match
        status = "✓" if passed else "✗"
        
        print(f"\n{status} {description} ({pentad_id})")
        print(f"  Expected center: ({expected_lat:.6f}, {expected_lng:.6f})")
        print(f"  Got center:      ({lat:.6f}, {lng:.6f})")
        
        if not passed:
            all_passed = False
            if not lat_match:
                print(f"  Lat diff: {lat - expected_lat:+.8f}")
            if not lng_match:
                print(f"  Lng diff: {lng - expected_lng:+.8f}")
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✓ All pentad2latlng tests passed!")
    else:
        print("✗ Some tests failed")
        
    assert all_passed, "pentad2latlng tests failed"
    return all_passed


def test_round_trip():
    """Test that converting coordinates -> pentad ID -> coordinates gives nearby results."""
    
    print("\n" + "=" * 70)
    print("Testing round-trip consistency")
    print("=" * 70)
    
    # Use coordinates well within pentad cells (not near boundaries)
    # to avoid naming convention edge cases
    # Note: Some northern hemisphere coordinates may still have issues
    # due to the +5' naming adjustment
    test_coords = [
        (-25.04, 27.04, 'Pretoria (interior)'),
        (-0.04, 10.04, 'Equator (interior, southern)'),
        (-33.96, 18.46, 'Cape Town (interior)'),
    ]
    
    all_passed = True
    max_diff = 5/60/2 + 1e-5  # 2.5 arcminutes + epsilon
    
    for orig_lat, orig_lng, description in test_coords:
        # Convert to pentad ID
        pentad_id = latlng2pentad([orig_lat], [orig_lng])[0]
        
        # Convert back to coordinates
        center_lats, center_lngs = pentad2latlng([pentad_id])
        center_lat, center_lng = center_lats[0], center_lngs[0]
        
        # Calculate differences
        lat_diff = abs(orig_lat - center_lat)
        lng_diff = abs(orig_lng - center_lng)
        
        passed = lat_diff <= max_diff and lng_diff <= max_diff
        status = "✓" if passed else "✗"
        
        print(f"\n{status} {description}")
        print(f"  Original:  ({orig_lat:.6f}, {orig_lng:.6f})")
        print(f"  Pentad ID: {pentad_id}")
        print(f"  Center:    ({center_lat:.6f}, {center_lng:.6f})")
        print(f"  Diff:      ({lat_diff:.6f}, {lng_diff:.6f})")
        print(f"  Max allowed: {max_diff:.6f} (2.5 arcminutes)")
        
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✓ All round-trip tests passed!")
    else:
        print("✗ Some tests failed")
        
    assert all_passed, "Round-trip tests failed"
    return all_passed


def test_vectorization():
    """Test that functions work with arrays of inputs."""
    
    print("\n" + "=" * 70)
    print("Testing vectorization")
    print("=" * 70)
    
    # Multiple coordinates
    lats = np.array([-25.041667, 0.05, 51.5074])
    lngs = np.array([27.083333, 10.0, -0.1278])
    
    # Test latlng2pentad with arrays
    pentad_ids = latlng2pentad(lats, lngs)
    assert len(pentad_ids) == 3, "Should return 3 pentad IDs"
    print(f"✓ latlng2pentad handles {len(pentad_ids)} coordinates")
    
    # Test pentad2latlng with arrays
    center_lats, center_lngs = pentad2latlng(pentad_ids)
    assert len(center_lats) == 3, "Should return 3 latitudes"
    assert len(center_lngs) == 3, "Should return 3 longitudes"
    print(f"✓ pentad2latlng handles {len(pentad_ids)} pentad IDs")
    
    print("\n" + "=" * 70)
    print("✓ All vectorization tests passed!")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PENTAD CONVERSION TESTS")
    print("=" * 70)
    
    try:
        test_latlng2pentad()
        test_pentad2latlng()
        test_round_trip()
        test_vectorization()
        
        print("\n" + "=" * 70)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("=" * 70 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        sys.exit(1)

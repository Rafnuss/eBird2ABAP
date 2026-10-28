"""Rule-based pentad regressions independent of the website's legacy labels."""

import unittest

import numpy as np
from shapely.geometry import Point, box

from eBird2ABAP import generate_pentad_grid, latlng2pentad, latlng2polygon, pentad2latlng, pentad2polygon


class PentadConsistencyTests(unittest.TestCase):
    def test_published_northwest_corner_examples(self):
        # SABAP2 DMS manual section 2.2; BDI glossary's Cape Town, Dakar and Jos.
        for pentad, north, west in [
            ("2920_2935", -29 - 20/60, 29 + 35/60),
            ("3355_1825", -33 - 55/60, 18 + 25/60),
            ("1445b1730", 14 + 45/60, -17 - 30/60),
            ("0955c0850", 9 + 55/60, 8 + 50/60),
        ]:
            with self.subTest(pentad=pentad):
                np.testing.assert_allclose(pentad2polygon(pentad).bounds,
                                           [west, north - 1/12, west + 1/12, north], rtol=0, atol=1e-12)
                lat, lng = pentad2latlng(pentad)
                self.assertEqual(latlng2pentad(lat, lng), [pentad])

    def test_equator_and_prime_meridian_cells(self):
        for lat, lng, expected in [
            (-0.04, 0.04, "0000_0000"),
            (-0.04, -0.04, "0000a0005"),
            (0.04, -0.04, "0005b0005"),
            (0.04, 0.04, "0005c0000"),
            (0, 0, "0000_0000"),
            (0, -0.04, "0000a0005"),
            (0.04, 0, "0005c0000"),
            (0.04, 10.04, "0005c1000"),
            (4.375, -7.375, "0425b0725"),
        ]:
            with self.subTest(lat=lat, lng=lng):
                self.assertEqual(latlng2pentad(lat, lng), [expected])
                self.assertTrue(latlng2polygon(lat, lng).covers(Point(lng, lat)))

    def test_grid_edges_use_south_and_east_side(self):
        # The manual defines NW corners but not shared-edge assignment;
        # this deterministic half-open convention is a package decision.
        for lat, lng in [(1/12, 1/12), (-1/12, -1/12), (10, 20), (-10, -20)]:
            with self.subTest(lat=lat, lng=lng):
                np.testing.assert_allclose(latlng2polygon(lat, lng).bounds,
                                           [lng, lat - 1/12, lng + 1/12, lat], rtol=0, atol=1e-12)
                pentad = latlng2pentad(lat, lng)[0]
                np.testing.assert_allclose(pentad2polygon(pentad).bounds,
                                           latlng2polygon(lat, lng).bounds, rtol=0, atol=1e-12)
                self.assertNotEqual(latlng2pentad(lat + 1e-7, lng)[0], pentad)
                self.assertNotEqual(latlng2pentad(lat, lng - 1e-7)[0], pentad)

    def test_random_african_points_roundtrip_and_containment(self):
        rng = np.random.default_rng(42)
        lat = rng.uniform(-40, 40, 5000)
        lng = rng.uniform(-25, 60, 5000)
        ids = latlng2pentad(lat, lng)
        centre_lat, centre_lng = pentad2latlng(ids)
        self.assertEqual(latlng2pentad(centre_lat, centre_lng), ids)
        named = pentad2polygon(ids)
        coordinate = latlng2polygon(lat, lng)
        for y, x, first, second in zip(lat, lng, named, coordinate):
            self.assertTrue(first.covers(Point(x, y)))
            np.testing.assert_allclose(first.bounds, second.bounds, rtol=0, atol=1e-12)

    def test_generated_grids_have_consistent_ids_and_no_extra_border_cells(self):
        for region in [box(10, 0, 10 + 2/12, 2/12), box(-1/6, -1/6, 0, 0)]:
            grid = generate_pentad_grid(region, return_geojson=False)
            self.assertEqual(len(grid), 4)
            self.assertTrue(grid.pentad.is_unique)
            for pentad, geometry in zip(grid.pentad, grid.geometry):
                np.testing.assert_allclose(geometry.bounds, pentad2polygon(pentad).bounds,
                                           rtol=0, atol=1e-12)
                self.assertGreater(geometry.intersection(region).area, 0)

    def test_website_exceptions_are_not_naming_overrides(self):
        # Ghana KML: ID 0540c0005 at 5.625N, 0.041667W.
        self.assertEqual(latlng2pentad(5.625, -1/24), ["0540b0005"])
        # Nigeria KML: ID 0440c0530 at 4.541667N, 5.541667E.
        self.assertEqual(latlng2pentad(4 + 13/24, 5 + 13/24), ["0435c0530"])
        # Southern Atlantic KML: ID 1550_0540 west of Greenwich.
        self.assertEqual(latlng2pentad(-15.875, -5.625), ["1550a0540"])


if __name__ == "__main__":
    unittest.main()

"""Control-tab lightweight position map."""
from __future__ import annotations

import unittest

from ui.control_map import (
    latlon_bounds,
    position_fix_color_hex,
    project_latlon,
)


class TestControlMap(unittest.TestCase):
    def test_position_fix_color_matches_dashboard(self) -> None:
        self.assertEqual(
            position_fix_color_hex(stale=False, stream_idle=False, quality=4),
            "#4ade80",
        )
        self.assertEqual(
            position_fix_color_hex(stale=True, stream_idle=False, quality=4),
            "#f87171",
        )

    def test_project_latlon_center(self) -> None:
        bounds = latlon_bounds([(40.0, -74.0)])
        assert bounds is not None
        x, y = project_latlon(40.0, -74.0, bounds, 200, 100)
        self.assertAlmostEqual(x, 100.0, delta=2.0)
        self.assertAlmostEqual(y, 50.0, delta=2.0)

    def test_latlon_bounds_single_point_has_padding(self) -> None:
        bounds = latlon_bounds([(30.0, 10.0)])
        assert bounds is not None
        min_lon, max_lon, min_lat, max_lat = bounds
        self.assertLess(min_lat, 30.0)
        self.assertGreater(max_lat, 30.0)


if __name__ == "__main__":
    unittest.main()

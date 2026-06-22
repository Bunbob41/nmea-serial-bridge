"""Control-tab lightweight position map."""
from __future__ import annotations

import time
import unittest

from ui.control_map import (
    dynamic_grid_interval_meters,
    grid_cell_scale_label,
    latlon_bounds,
    position_fix_color_hex,
    project_latlon,
    prune_track_points,
    snap_grid_interval_meters,
    track_average_velocity_mps,
    track_points_in_window,
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

    def test_grid_cell_scale_label_rounds_nicely(self) -> None:
        bounds = latlon_bounds([(40.0, -74.0), (40.0001, -73.9999)])
        assert bounds is not None
        label = grid_cell_scale_label(bounds)
        self.assertTrue(label.startswith("Grid: "))
        self.assertIn(" m", label)
        interval = snap_grid_interval_meters(bounds)
        self.assertIn(interval, (1, 2, 5, 10, 25, 50, 100, 250, 500))
        self.assertEqual(label, f"Grid: {interval} m")

    def test_snap_grid_interval_prefers_standard_spacing(self) -> None:
        bounds = latlon_bounds([(40.0, -74.0), (40.0005, -73.9995)])
        assert bounds is not None
        interval = snap_grid_interval_meters(bounds)
        self.assertIn(interval, (1, 2, 5, 10, 25, 50, 100, 250, 500))
        self.assertNotEqual(interval, 37)

    def test_rolling_window_keeps_recent_points(self) -> None:
        now = 1000.0
        track = [
            (now - 6.0, 40.0, -74.0),
            (now - 3.0, 40.0001, -73.9999),
            (now - 0.5, 40.0002, -73.9998),
        ]
        windowed = track_points_in_window(track, now_mono=now)
        self.assertEqual(len(windowed), 2)
        self.assertEqual(windowed[0][1:], (40.0001, -73.9999))

    def test_prune_track_points_drops_stale_samples(self) -> None:
        now = 2000.0
        track = [
            (now - 10.0, 40.0, -74.0),
            (now - 7.0, 40.0001, -73.9999),
            (now - 4.0, 40.0002, -73.9998),
            (now - 1.0, 40.0003, -73.9997),
        ]
        prune_track_points(track, now_mono=now)
        self.assertEqual(len(track), 2)
        self.assertEqual(track[0][1:], (40.0002, -73.9998))
        self.assertEqual(track[1][1:], (40.0003, -73.9997))

    def test_rolling_window_never_returns_outside_window(self) -> None:
        now = 3000.0
        track = [(now - 20.0, 40.0, -74.0), (now - 0.2, 40.0001, -73.9999)]
        windowed = track_points_in_window(track, now_mono=now)
        self.assertEqual(len(windowed), 1)
        self.assertEqual(windowed[0][1:], (40.0001, -73.9999))

    def test_dynamic_grid_scales_with_velocity(self) -> None:
        now = time.monotonic()
        track = [
            (now - 4.0, 40.0, -74.0),
            (now - 2.0, 40.0003, -74.0),
            (now, 40.0006, -74.0),
        ]
        bounds = latlon_bounds([(lat, lon) for _t, lat, lon in track])
        assert bounds is not None
        velocity = track_average_velocity_mps(track, now_mono=now)
        self.assertGreater(velocity, 0.5)
        interval = dynamic_grid_interval_meters(track, bounds, now_mono=now)
        self.assertIn(interval, (1, 2, 5, 10, 25, 50, 100, 250, 500))
        label = grid_cell_scale_label(bounds, track, now_mono=now)
        self.assertEqual(label, f"Grid: {interval} m")
        self.assertNotIn("≈", label)


if __name__ == "__main__":
    unittest.main()

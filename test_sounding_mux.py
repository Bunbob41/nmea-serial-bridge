import time
import unittest

from depth_codec import DepthSample
from sounding_mux import (
    DISPLAY_CAP,
    DepthFixBinder,
    FixSnapshot,
    Sounding,
    SoundingBuffer,
    interpolate_position,
    mux_depth,
)


def _depth(mono: float, depth_m: float = 5.0) -> DepthSample:
    return DepthSample(depth_m=depth_m, source="sddpt", raw_line="x", received_mono=mono)


def _fix(lat: float, lon: float, mono: float) -> FixSnapshot:
    return FixSnapshot(lat, lon, 1, 1.2, "gga", mono)


class TestSoundingMux(unittest.TestCase):
    def test_stale(self) -> None:
        fix = FixSnapshot(44.0, -120.0, 1, 1.2, "gga", time.monotonic() - 4)
        d = DepthSample(5.0, "sddpt", "x", time.monotonic())
        self.assertTrue(mux_depth(d, fix, stale_ms=3000).stale)

    def test_cap(self) -> None:
        buf = SoundingBuffer(cap=DISPLAY_CAP)
        fix = FixSnapshot(44.0, -120.0, 1, 1.2, "gga", time.monotonic())
        d = DepthSample(5.0, "sddpt", "x", time.monotonic())
        for _ in range(DISPLAY_CAP + 5):
            buf.append(mux_depth(d, fix))
        self.assertEqual(len(buf), DISPLAY_CAP)

    def test_recent_for_map_skips_partial_coords_when_downsampled(self) -> None:
        buf = SoundingBuffer(cap=600)
        fix = FixSnapshot(44.0, -120.0, 1, 1.2, "gga", time.monotonic())
        d = DepthSample(5.0, "sddpt", "x", time.monotonic())
        bad = Sounding(
            depth_m=9.0,
            lat=45.0,
            lon=None,
            fix_age_ms=0,
            stale=True,
            depth_source="sddpt",
            wall_time=None,
            hdop=None,
            fix_type=None,
        )
        for _ in range(550):
            buf.append(mux_depth(d, fix))
        buf.append(bad)
        rows = buf.recent_for_map(max_points=100)
        self.assertTrue(rows)
        for row in rows:
            self.assertIsNotNone(row.get("lat"))
            self.assertIsNotNone(row.get("lon"))

    def test_interpolate_between_fixes(self) -> None:
        prev = _fix(44.0, -120.0, 100.0)
        cur = _fix(44.001, -120.001, 101.0)
        mid = interpolate_position(prev, cur, 100.5)
        self.assertIsNotNone(mid)
        lat, lon = mid
        self.assertAlmostEqual(lat, 44.0005, places=5)
        self.assertAlmostEqual(lon, -120.0005, places=5)

    def test_binder_spreads_high_rate_depths_on_subsequent_fix(self) -> None:
        binder = DepthFixBinder()
        t0 = 1000.0
        binder.on_fix(_fix(44.0, -120.0, t0))
        for i in range(48):
            binder.bind_depth(_depth(t0 + 0.02 * (i + 1), depth_m=float(i)))
        self.assertEqual(len(binder._pending), 48)
        released = binder.on_fix(_fix(44.01, -120.01, t0 + 1.0))
        self.assertEqual(len(released), 48)
        lats = [s.lat for s in released]
        lons = [s.lon for s in released]
        self.assertEqual(len(set(lats)), 48)
        self.assertEqual(len(set(lons)), 48)
        self.assertAlmostEqual(lats[0], 44.0 + (0.01 / 49), places=6)
        self.assertAlmostEqual(lats[-1], 44.0 + (48 * 0.01 / 49), places=6)

    def test_binder_interpolates_depths_before_current_fix(self) -> None:
        binder = DepthFixBinder()
        t0 = 2000.0
        binder.on_fix(_fix(44.0, -120.0, t0 - 1.0))
        binder.on_fix(_fix(44.01, -120.01, t0))
        out = binder.bind_depth(_depth(t0 - 0.5))
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(out[0].lat, 44.005, places=4)

    def test_binder_holds_depth_until_first_fix(self) -> None:
        binder = DepthFixBinder()
        t0 = 3000.0
        out = binder.bind_depth(_depth(t0, depth_m=7.5))
        self.assertEqual(out, [])
        self.assertEqual(len(binder._pending), 1)
        released = binder.on_fix(_fix(44.0, -120.0, t0 + 1.0))
        self.assertEqual(len(released), 1)
        self.assertAlmostEqual(released[0].lat, 44.0)
        self.assertAlmostEqual(released[0].lon, -120.0)
        self.assertAlmostEqual(released[0].depth_m, 7.5)

    def test_binder_flush_drops_pending_without_fix(self) -> None:
        binder = DepthFixBinder()
        binder.bind_depth(_depth(4000.0))
        flushed = binder.flush_pending()
        self.assertEqual(flushed, [])
        self.assertEqual(len(binder._pending), 0)

    def test_export_dict_uses_iso_timestamp(self) -> None:
        epoch = 1_700_000_000.5
        sounding = Sounding(
            depth_m=3.2,
            lat=44.0,
            lon=-120.0,
            fix_age_ms=0,
            stale=False,
            depth_source="sddpt",
            wall_time=epoch,
            hdop=1.0,
            fix_type=1,
        )
        row = sounding.to_export_dict()
        self.assertIsInstance(row["timestamp"], str)
        self.assertTrue(str(row["timestamp"]).endswith("Z"))
        self.assertNotIsInstance(row["timestamp"], float)


if __name__ == "__main__":
    unittest.main()

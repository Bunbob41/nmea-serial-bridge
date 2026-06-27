import time
import unittest

from depth_codec import DepthSample
from sounding_mux import FixSnapshot, mux_depth
from ui.mission_session import (
    MissionSessionRecord,
    apply_depth_metrics_to_record,
    compute_depth_session_metrics,
)


class TestMissionDepthSession(unittest.TestCase):
    def test_export_keeps_coords_when_stale(self) -> None:
        fix = FixSnapshot(44.0, -120.0, 1, 1.2, "gga", time.monotonic() - 4)
        depth = DepthSample(5.2, "sddpt", "$SDDPT,5.2,0.0", time.monotonic())
        row = mux_depth(depth, fix, stale_ms=3000).to_export_dict()
        self.assertTrue(row.get("fix_stale"))
        self.assertEqual(row.get("lat"), 44.0)
        self.assertEqual(row.get("lon"), -120.0)
        self.assertEqual(row.get("depth_m"), 5.2)

    def test_depth_metrics_from_soundings(self) -> None:
        soundings = [
            {"depth_m": 0.0, "depth_source": "sddpt"},
            {"depth_m": 4.5, "lat": 44.0, "lon": -120.0, "depth_source": "sddpt"},
            {"depth_m": 6.0, "lat": 44.1, "lon": -120.1, "depth_source": "sddbt"},
        ]
        metrics = compute_depth_session_metrics(
            soundings,
            depth_stats={
                "depth_enabled": True,
                "depth_port": "COM9",
                "depth_rate_hz": 2.5,
                "last_depth_m": 6.0,
                "last_depth_source": "sddbt",
                "sounding_count": 3,
            },
        )
        self.assertTrue(metrics["depth_enabled"])
        self.assertEqual(metrics["last_depth_m"], 6.0)
        self.assertAlmostEqual(metrics["avg_depth_m"], (0.0 + 4.5 + 6.0) / 3)
        self.assertEqual(metrics["sounding_count"], 3)

    def test_apply_depth_metrics_to_record(self) -> None:
        record = MissionSessionRecord(0, 1, 1, "", 0, 0, 1.0)
        apply_depth_metrics_to_record(
            record,
            [{"depth_m": 3.3, "depth_source": "sddpt"}],
            depth_stats={"depth_enabled": True, "depth_rate_hz": 1.0, "sounding_count": 1},
            avg_depth_rate_hz=1.0,
        )
        self.assertTrue(record.depth_enabled)
        self.assertEqual(record.last_depth_m, 3.3)
        self.assertEqual(record.avg_depth_rate_hz, 1.0)
        self.assertEqual(len(record.soundings), 1)


if __name__ == "__main__":
    unittest.main()

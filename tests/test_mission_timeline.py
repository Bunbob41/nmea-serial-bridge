"""Mission Review timeline scrub helpers."""
from __future__ import annotations

import unittest

from ui.mission_session import MissionSessionRecord
from ui.mission_timeline import (
    format_mission_duration_hms,
    mission_error_rate_pct,
    scrub_snapshot,
    timeline_bucket_count,
)


class TestMissionTimeline(unittest.TestCase):
    def _record(self) -> MissionSessionRecord:
        return MissionSessionRecord(
            started_mono=0.0,
            ended_mono=120.0,
            duration_s=120.0,
            backup_path=r"C:\logs\backup.nmea",
            total_bytes=10_000,
            total_dropped=0,
            avg_hz_up=5.0,
            throughput_buckets=[1000, 2000, 3000, 4000],
            health_ticks=["ok", "ok", "warn", "bad"],
        )

    def test_duration_hms(self) -> None:
        self.assertEqual(format_mission_duration_hms(30), "30s")
        self.assertEqual(format_mission_duration_hms(90), "01m 30s")
        self.assertEqual(format_mission_duration_hms(15150), "04h 12m 30s")

    def test_bucket_count(self) -> None:
        self.assertEqual(timeline_bucket_count(self._record()), 4)

    def test_error_rate(self) -> None:
        rec = self._record()
        self.assertEqual(mission_error_rate_pct(rec), 50.0)
        self.assertEqual(mission_error_rate_pct(rec, through_bucket=1), 0.0)

    def test_scrub_partial_bytes(self) -> None:
        snap = scrub_snapshot(self._record(), 1)
        self.assertEqual(snap.cumulative_bytes, 3000)
        self.assertEqual(snap.bucket_index, 1)


if __name__ == "__main__":
    unittest.main()
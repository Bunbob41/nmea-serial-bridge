"""Mission session recorder unit tests."""
from __future__ import annotations

import unittest

from ui.mission_session import BUCKET_INTERVAL_S, MissionSessionRecorder


class TestMissionSessionRecorder(unittest.TestCase):
    def test_buckets_throughput_and_health(self) -> None:
        rec = MissionSessionRecorder(bucket_s=5.0)
        rec.start(mono=0.0, com="COM7", baud=115200)
        t = 0.0
        for _ in range(6):
            rec.sample(
                {
                    "local_backup_bytes": 1000,
                    "local_backup_dropped": 0,
                    "hz_up": 5.0,
                    "local_backup_error": "",
                },
                mono=t,
            )
            t += 1.0
        rec.sample(
            {
                "local_backup_bytes": 5000,
                "local_backup_dropped": 2,
                "hz_up": 8.0,
                "local_backup_error": "",
            },
            mono=BUCKET_INTERVAL_S + 0.1,
        )
        out = rec.finalize(
            {"bytes": 5000, "dropped": 2, "path": r"C:\logs\backup.raw", "error": ""},
            mono=BUCKET_INTERVAL_S + 1.0,
        )
        self.assertGreaterEqual(len(out.throughput_buckets), 1)
        self.assertEqual(len(out.throughput_buckets), len(out.health_ticks))
        self.assertEqual(out.total_bytes, 5000)
        self.assertGreater(out.avg_hz_up, 0.0)


if __name__ == "__main__":
    unittest.main()

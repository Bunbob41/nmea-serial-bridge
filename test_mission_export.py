"""Mission Quick Export zip tests."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from ui.mission_export import build_mission_summary_text, quick_export_mission
from ui.mission_session import MissionSessionRecord


class TestMissionExport(unittest.TestCase):
    def test_summary_text_includes_duration_and_hz(self) -> None:
        text = build_mission_summary_text(
            MissionSessionRecord(
                started_mono=0.0,
                ended_mono=120.0,
                duration_s=120.0,
                backup_path=r"C:\logs\backup.raw",
                total_bytes=50_000,
                total_dropped=0,
                avg_hz_up=12.5,
                throughput_buckets=[1000, 2000],
                health_ticks=["ok", "ok"],
            )
        )
        self.assertIn("Duration:", text)
        self.assertIn("12.50", text)
        self.assertIn("50,000", text)

    def test_quick_export_creates_zip_with_raw_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "backup_20260614_1645.raw"
            raw.write_bytes(b"$GPGGA" * 200)
            record = MissionSessionRecord(
                started_mono=0.0,
                ended_mono=60.0,
                duration_s=60.0,
                backup_path=str(raw),
                total_bytes=raw.stat().st_size,
                total_dropped=0,
                avg_hz_up=10.0,
            )
            zip_path = quick_export_mission(record, dest_dir=Path(tmp) / "out")
            self.assertTrue(zip_path.is_file())
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                self.assertIn("mission_summary.txt", names)
                self.assertIn(raw.name, names)
                summary = zf.read("mission_summary.txt").decode("utf-8")
                self.assertIn("Mission Summary", summary)


if __name__ == "__main__":
    unittest.main()

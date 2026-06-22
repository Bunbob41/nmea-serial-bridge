"""Mission summary dialog formatting and verification."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ui.mission_summary import (
    format_mission_summary_line,
    verify_backup_on_disk,
)


class TestMissionSummary(unittest.TestCase):
    def test_format_line(self) -> None:
        line = format_mission_summary_line(
            {
                "bytes": 2_500_000,
                "dropped": 3,
                "path": r"C:\app\logs\backup_20260614_1645.raw",
            }
        )
        self.assertIn("Mission Data Safeguarded:", line)
        self.assertIn("2.4 MB", line)
        self.assertIn("3 Dropped", line)
        self.assertIn("backup_20260614_1645.raw", line)

    def test_zero_bytes_triggers_warning(self) -> None:
        _, warn, detail = verify_backup_on_disk(
            {"bytes": 0, "dropped": 0, "path": "", "error": ""}
        )
        self.assertTrue(warn)
        self.assertIn("0 bytes", detail)

    def test_empty_file_on_disk_triggers_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "backup_test.raw"
            path.touch()
            _, warn, detail = verify_backup_on_disk(
                {
                    "bytes": 1024,
                    "dropped": 0,
                    "path": str(path),
                    "error": "",
                }
            )
            self.assertTrue(warn)
            self.assertIn("empty", detail.lower())

    def test_valid_file_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "backup_test.raw"
            path.write_bytes(b"NMEA" * 100)
            on_disk, warn, _ = verify_backup_on_disk(
                {
                    "bytes": 400,
                    "dropped": 0,
                    "path": str(path),
                    "error": "",
                }
            )
            self.assertFalse(warn)
            self.assertEqual(on_disk, 400)


if __name__ == "__main__":
    unittest.main()

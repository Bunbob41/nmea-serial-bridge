"""Backup status bar formatting."""
from __future__ import annotations

import unittest

from ui.backup_status import format_backup_status


class TestBackupStatusFormat(unittest.TestCase):
    def test_active_compact_bar_full_tooltip(self) -> None:
        bar, tip = format_backup_status(
            enabled=True,
            running=False,
            active=True,
            error="",
            path=r"C:\logs\backup_20260614_1645.raw",
            nbytes=1_250_000,
            dropped=0,
            queue_depth=3,
            queue_max=8192,
        )
        self.assertEqual(bar, "Backup: 1.2 MB")
        self.assertIn("backup_20260614_1645.raw", tip)
        self.assertIn("1,250,000", tip)

    def test_drops_show_warn_glyph(self) -> None:
        bar, tip = format_backup_status(
            enabled=True,
            running=False,
            active=True,
            error="",
            path="/logs/x.raw",
            nbytes=500,
            dropped=12,
            queue_depth=8192,
            queue_max=8192,
        )
        self.assertIn("⚠", bar)
        self.assertIn("12", tip)

    def test_error_takes_priority(self) -> None:
        bar, tip = format_backup_status(
            enabled=True,
            running=True,
            active=False,
            error="Local backup write failed: [Errno 28] No space left on device",
            path="",
            nbytes=0,
            dropped=0,
        )
        self.assertEqual(bar, "Backup: error")
        self.assertIn("No space", tip)


if __name__ == "__main__":
    unittest.main()

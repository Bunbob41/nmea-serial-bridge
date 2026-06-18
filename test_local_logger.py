"""Local black-box serial backup writer."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest
from pathlib import Path

from core.local_logger import (
    LocalSerialBackup,
    _allocate_session_path,
    allocate_session_folder,
    default_local_backup_dir,
    format_session_folder_name,
)


class TestLocalSerialBackup(unittest.TestCase):
    def test_writes_and_fsync_raw_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            written: list[str] = []
            backup = LocalSerialBackup(base, on_error=written.append)
            path = backup.start_session()
            self.assertIsNotNone(path)
            assert path is not None
            backup.append(b"$GPGGA,1,2,3*00\r\n")
            backup.append(b"$GPRMC,1,2,3*11\r\n")
            snap = backup.close()
            self.assertEqual(path.read_bytes(), b"$GPGGA,1,2,3*00\r\n$GPRMC,1,2,3*11\r\n")
            self.assertEqual(int(snap["bytes"]), 34)
            self.assertFalse(written)

    def test_open_failure_returns_none_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "not_a_dir"
            blocker.write_text("x", encoding="utf-8")
            errors: list[str] = []
            backup = LocalSerialBackup(blocker / "logs", on_error=errors.append)
            self.assertIsNone(backup.start_session())
            backup.append(b"abc")  # no-op when inactive

    def test_append_after_write_error_is_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = LocalSerialBackup(base)
            path = backup.start_session()
            self.assertIsNotNone(path)
            backup._error = "simulated"
            backup.append(b"abc")  # must not raise
            backup.close()

    def test_queue_full_counts_drops_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            backup = LocalSerialBackup(base)
            path = backup.start_session()
            self.assertIsNotNone(path)
            backup._queue = __import__("queue").Queue(maxsize=1)  # type: ignore[attr-defined]
            backup.append(b"a")
            backup.append(b"b")
            backup.append(b"c")
            self.assertGreaterEqual(int(backup.snapshot()["dropped"]), 1)
            backup.close()

    def test_allocate_session_path_avoids_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = _allocate_session_path(base)
            first.write_bytes(b"x")
            second = _allocate_session_path(base)
            self.assertNotEqual(first, second)

    def test_default_dir_is_under_project_or_exe_parent(self) -> None:
        d = default_local_backup_dir()
        self.assertEqual(d.name, "logs")

    def test_session_folder_name_format(self) -> None:
        from datetime import datetime

        name = format_session_folder_name(now=datetime(2026, 6, 16, 19, 58, 0))
        self.assertEqual(name, "2026-06-16_19-58")

    def test_allocate_session_folder_creates_unique_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = allocate_session_folder(
                base, now=__import__("datetime").datetime(2026, 6, 16, 19, 58, 0)
            )
            second = allocate_session_folder(
                base, now=__import__("datetime").datetime(2026, 6, 16, 19, 58, 0)
            )
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())
            self.assertNotEqual(first, second)
            self.assertEqual(first.name, "2026-06-16_19-58")
            self.assertEqual(second.name, "2026-06-16_19-58_02")


if __name__ == "__main__":
    unittest.main()

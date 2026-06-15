"""Stress and resilience checks for LocalSerialBackup (no GUI)."""
from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from core.local_logger import LocalSerialBackup, _QUEUE_MAX


class TestLocalBackupStress(unittest.TestCase):
    def test_append_never_blocks_when_queue_saturates(self) -> None:
        """Producer must stay non-blocking even when writer falls behind."""
        chunk = b"X" * 4096
        bursts = _QUEUE_MAX + 512
        with tempfile.TemporaryDirectory() as tmp:
            backup = LocalSerialBackup(Path(tmp))
            self.assertIsNotNone(backup.start_session())

            t0 = time.perf_counter()
            for _ in range(bursts):
                backup.append(chunk)
            append_s = time.perf_counter() - t0
            self.assertLess(append_s, 1.5, "append() blocked the producer thread")

            snap = backup.snapshot()
            self.assertGreater(int(snap["dropped"]), 0)
            backup.close()

    def test_queue_saturation_drops_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            backup = LocalSerialBackup(Path(tmp))
            backup.start_session()
            backup._queue = __import__("queue").Queue(maxsize=4)  # type: ignore[attr-defined]
            for _ in range(20):
                backup.append(b"abc")
            snap = backup.snapshot()
            self.assertGreater(int(snap["dropped"]), 0)
            backup.close()

    def test_disk_full_isolates_backup_from_producer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            errors: list[str] = []
            backup = LocalSerialBackup(base, on_error=errors.append)
            backup.start_session()
            backup._error = "No space left on device"
            for _ in range(500):
                backup.append(b"Z" * 1024)
            snap = backup.close()
            self.assertEqual(int(snap["bytes"]), 0)


if __name__ == "__main__":
    unittest.main()

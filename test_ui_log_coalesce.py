"""Tests for ``log_serial_coalesce`` (GUI + bridge share the same rules)."""
from __future__ import annotations

import unittest
from typing import Optional

from log_serial_coalesce import serial_timeout_line_suppress


class TestSerialTimeoutCoalesce(unittest.TestCase):
    def test_first_shown_repeat_hidden_then_shown(self) -> None:
        t0 = 1_000_000.0
        last: Optional[str] = None
        mono = 0.0
        line = "Serial COM7: timed out (open/write)."
        sup, last, mono = serial_timeout_line_suppress(last, mono, line, now=t0)
        self.assertFalse(sup)
        sup, last, mono = serial_timeout_line_suppress(last, mono, line, now=t0 + 0.2)
        self.assertTrue(sup)
        sup, last, mono = serial_timeout_line_suppress(last, mono, line, now=t0 + 3.0)
        self.assertFalse(sup)

    def test_other_lines_never_suppressed(self) -> None:
        last, mono = None, 0.0
        sup, _, _ = serial_timeout_line_suppress(last, mono, "UDP←1:2 | gps=— | $GPGGA", now=100.0)
        self.assertFalse(sup)


if __name__ == "__main__":
    unittest.main()

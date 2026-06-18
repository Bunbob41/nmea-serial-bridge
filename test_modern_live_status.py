"""Tests for ui/modern_live_status.py."""
from __future__ import annotations

import unittest

from ui.modern_live_status import summary_kind_to_status_kind


class TestModernLiveStatus(unittest.TestCase):
    def test_summary_kind_to_status_kind(self) -> None:
        self.assertEqual(summary_kind_to_status_kind("ok"), "ok")
        self.assertEqual(summary_kind_to_status_kind("idle"), "idle")
        self.assertEqual(summary_kind_to_status_kind("warn"), "warn")
        self.assertEqual(summary_kind_to_status_kind("ready"), "ready")
        self.assertEqual(summary_kind_to_status_kind(""), "idle")
        self.assertEqual(summary_kind_to_status_kind("unknown"), "unknown")

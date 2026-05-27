"""bench_fanout_automation contracts."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from bench_fanout_automation import resolve_mode


class TestBenchFanoutAutomation(unittest.TestCase):
    def test_resolve_mode_auto_free_port(self) -> None:
        with patch("bench_fanout_automation.port_has_listener", return_value=False):
            self.assertEqual(resolve_mode("auto", 10110), "headless")

    def test_resolve_mode_auto_busy_port(self) -> None:
        with patch("bench_fanout_automation.port_has_listener", return_value=True):
            self.assertEqual(resolve_mode("auto", 10110), "live")

    def test_operator_guide_mentions_fanout_automation(self) -> None:
        text = (Path(__file__).resolve().parent / "docs" / "OPERATOR_GUIDE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("bench_fanout_automation.py", text)


if __name__ == "__main__":
    unittest.main()

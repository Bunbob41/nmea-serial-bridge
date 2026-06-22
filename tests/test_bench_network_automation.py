"""bench_network_automation mode selection and operator doc contract."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from bench_network_automation import resolve_mode


class TestBenchNetworkAutomation(unittest.TestCase):
    def test_resolve_mode_auto_free_port(self) -> None:
        with patch("bench_network_automation.port_has_listener", return_value=False):
            self.assertEqual(resolve_mode("auto", 10110), "headless")

    def test_resolve_mode_auto_busy_port(self) -> None:
        with patch("bench_network_automation.port_has_listener", return_value=True):
            self.assertEqual(resolve_mode("auto", 10110), "live")

    def test_resolve_mode_explicit(self) -> None:
        with patch("bench_network_automation.port_has_listener", return_value=True):
            self.assertEqual(resolve_mode("headless", 10110), "headless")
            self.assertEqual(resolve_mode("live", 10110), "live")


class TestOperatorGuideBenchNetwork(unittest.TestCase):
    def test_operator_guide_mentions_network_automation(self) -> None:
        from tests import REPO_ROOT

        text = (REPO_ROOT / "docs" / "OPERATOR_GUIDE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("bench_network_automation.py", text)


if __name__ == "__main__":
    unittest.main()

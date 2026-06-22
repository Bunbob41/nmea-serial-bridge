"""Tests for hub traffic quality mapping."""
from __future__ import annotations

import unittest

from ui.hub_quality import quality_from_bridge_stats


class TestHubQuality(unittest.TestCase):
    def test_idle_when_stopped(self) -> None:
        q = quality_from_bridge_stats({"running": False})
        self.assertEqual(q.state, "idle")

    def test_warn_on_drops(self) -> None:
        q = quality_from_bridge_stats(
            {"running": True, "hz_up": 1.0, "drops_s2n": 3, "rej_s2n": 0}
        )
        self.assertEqual(q.state, "warn")

    def test_ok_with_traffic(self) -> None:
        q = quality_from_bridge_stats({"running": True, "hz_up": 1.0, "drops_s2n": 0})
        self.assertEqual(q.state, "ok")


if __name__ == "__main__":
    unittest.main()

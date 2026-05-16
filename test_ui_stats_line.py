"""Tests for human-readable live stats formatting."""
from __future__ import annotations

import unittest

from ui.stats_line import format_live_stats_line


class TestFormatLiveStatsLine(unittest.TestCase):
    def test_healthy_idle_no_slash_pairs(self) -> None:
        s = format_live_stats_line(
            {
                "hz_down": 0.0,
                "hz_gui": 0.0,
                "hz_up": 0.0,
                "drops_n2s": 0,
                "drops_s2n": 0,
                "rej_n2s": 0,
                "rej_s2n": 0,
                "n2s_q": 0,
                "s2n_q": 0,
                "lines_down": 0,
                "lines_up": 0,
            }
        )
        self.assertIn("transport OK", s)
        self.assertIn("no sentences counted yet", s)
        self.assertNotIn("0/0", s)
        self.assertNotIn("dr ", s)

    def test_inject_rate_shown_when_active(self) -> None:
        s = format_live_stats_line(
            {
                "hz_down": 1.0,
                "hz_gui": 0.2,
                "hz_up": 0.0,
                "drops_n2s": 0,
                "drops_s2n": 0,
                "rej_n2s": 0,
                "rej_s2n": 0,
                "n2s_q": 0,
                "s2n_q": 0,
                "lines_down": 5,
                "lines_up": 0,
            }
        )
        self.assertIn("Send→COM", s)

    def test_drop_net_to_com_only(self) -> None:
        s = format_live_stats_line(
            {
                "hz_down": 0.0,
                "hz_gui": 0.0,
                "hz_up": 0.0,
                "drops_n2s": 3,
                "drops_s2n": 0,
                "rej_n2s": 0,
                "rej_s2n": 0,
                "n2s_q": 0,
                "s2n_q": 0,
                "lines_down": 0,
                "lines_up": 0,
            }
        )
        self.assertIn("drops 3", s)
        self.assertIn("net→COM", s)
        self.assertNotIn("transport OK", s)

    def test_session_totals_none_on_one_side(self) -> None:
        s = format_live_stats_line(
            {
                "hz_down": 0.0,
                "hz_gui": 0.0,
                "hz_up": 0.0,
                "drops_n2s": 0,
                "drops_s2n": 0,
                "rej_n2s": 0,
                "rej_s2n": 0,
                "n2s_q": 0,
                "s2n_q": 0,
                "lines_down": 100,
                "lines_up": 0,
            }
        )
        self.assertIn("100 →COM", s)
        self.assertIn("none →net", s)


if __name__ == "__main__":
    unittest.main()

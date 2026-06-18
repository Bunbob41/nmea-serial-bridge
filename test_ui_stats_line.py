"""Tests for human-readable live stats formatting."""
from __future__ import annotations

import unittest

from ui.stats_line import (
    backpressure_alert_kind,
    format_backpressure_chip,
    format_live_stats_line,
    format_running_hz_chip,
    stats_snapshot_from_merged,
    transport_alert_active,
)


class TestStatsSnapshot(unittest.TestCase):
    def test_snapshot_uses_bridge_keys(self) -> None:
        snap = stats_snapshot_from_merged(
            {
                "hz_down": 5.0,
                "hz_up": 1.0,
                "hz_gui": 0.2,
                "drops_n2s": 2,
                "drops_s2n": 0,
                "rej_n2s": 3,
                "rej_s2n": 1,
                "lines_down": 100,
                "lines_up": 4,
            }
        )
        self.assertEqual(snap["hz_down"], 5.0)
        self.assertEqual(snap["rej_n2s"], 3)
        self.assertEqual(snap["lines_down"], 100)


class TestFormatLiveStatsLine(unittest.TestCase):
    def test_transport_alert_active_true_for_backlog_or_drops(self) -> None:
        self.assertTrue(
            transport_alert_active(
                {"drops_n2s": 0, "drops_s2n": 0, "rej_n2s": 0, "rej_s2n": 0, "n2s_q": 12, "s2n_q": 0}
            )
        )
        self.assertTrue(
            transport_alert_active(
                {"drops_n2s": 1, "drops_s2n": 0, "rej_n2s": 0, "rej_s2n": 0, "n2s_q": 0, "s2n_q": 0}
            )
        )
        self.assertFalse(
            transport_alert_active(
                {"drops_n2s": 0, "drops_s2n": 0, "rej_n2s": 0, "rej_s2n": 0, "n2s_q": 3, "s2n_q": 2}
            )
        )

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
        self.assertIn("inject", s)

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
        self.assertIn("100 sentences→COM", s)
        self.assertIn("none →net", s)

    def test_shallow_queue_still_transport_ok(self) -> None:
        s = format_live_stats_line(
            {
                "hz_down": 5.0,
                "hz_gui": 0.0,
                "hz_up": 0.0,
                "drops_n2s": 0,
                "drops_s2n": 0,
                "rej_n2s": 0,
                "rej_s2n": 0,
                "n2s_q": 2,
                "s2n_q": 1,
                "lines_down": 100,
                "lines_up": 0,
            }
        )
        self.assertIn("transport OK", s)
        self.assertNotIn("queue ", s)

    def test_deep_queue_backlog_alert(self) -> None:
        s = format_live_stats_line(
            {
                "hz_down": 5.0,
                "hz_gui": 0.0,
                "hz_up": 0.0,
                "drops_n2s": 0,
                "drops_s2n": 0,
                "rej_n2s": 0,
                "rej_s2n": 0,
                "n2s_q": 14,
                "s2n_q": 0,
                "lines_down": 100,
                "lines_up": 0,
            }
        )
        self.assertIn("backlog", s)
        self.assertNotIn("transport OK", s)

    def test_gnss_segment_when_present(self) -> None:
        s = format_live_stats_line(
            {
                "hz_down": 5.0,
                "hz_gui": 0.0,
                "hz_up": 0.0,
                "drops_n2s": 0,
                "drops_s2n": 0,
                "rej_n2s": 0,
                "rej_s2n": 0,
                "n2s_q": 0,
                "s2n_q": 0,
                "lines_down": 10,
                "lines_up": 0,
                "summary": "RTK fixed · 12 sats · HDOP 0.9",
                "fix_label": "RTK fixed",
                "level": "good",
                "nav_stale": False,
            }
        )
        self.assertIn("GNSS:", s)
        self.assertIn("RTK", s)


class TestBackpressureChip(unittest.TestCase):
    def test_chip_hidden_when_healthy(self) -> None:
        self.assertFalse(
            transport_alert_active(
                {"drops_n2s": 0, "drops_s2n": 0, "rej_n2s": 0, "rej_s2n": 0, "n2s_q": 0, "s2n_q": 0}
            )
        )

    def test_chip_text_for_drops(self) -> None:
        text, kind = format_backpressure_chip(
            {"drops_n2s": 5, "drops_s2n": 0, "rej_n2s": 0, "rej_s2n": 0, "n2s_q": 0, "s2n_q": 0}
        )
        self.assertIn("5 drops", text)
        self.assertEqual(kind, "error")
        self.assertEqual(backpressure_alert_kind({"drops_n2s": 1}), "error")

    def test_chip_text_for_rejects_only(self) -> None:
        text, kind = format_backpressure_chip(
            {"drops_n2s": 0, "drops_s2n": 0, "rej_n2s": 2, "rej_s2n": 0, "n2s_q": 0, "s2n_q": 0}
        )
        self.assertIn("2 rej", text)
        self.assertEqual(kind, "warn")

    def test_backpressure_detail_rejects(self) -> None:
        from ui.stats_line import format_backpressure_detail

        detail = format_backpressure_detail(
            {"drops_n2s": 0, "drops_s2n": 0, "rej_n2s": 2, "rej_s2n": 0, "n2s_q": 0, "s2n_q": 0}
        )
        self.assertIn("Rejected 2 toward COM", detail)
        self.assertIn("strict NMEA", detail)


    def test_running_hz_chip_shows_gnss_fix_rate(self) -> None:
        text, tip = format_running_hz_chip(
            {
                "hz_fix_down": 1.0,
                "hz_fix_up": 0.0,
                "hz_down": 18.0,
                "hz_up": 0.0,
                "hz_gui": 0.0,
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
        self.assertIn("GNSS 1.0 Hz", text)
        self.assertIn("18 msg/s", text)
        self.assertNotIn("↓", text)
        self.assertNotIn("↑", text)
        self.assertIn("18.0", tip)
        self.assertIn("GGA", tip)

    def test_running_hz_chip_fallback_no_arrows(self) -> None:
        text, _tip = format_running_hz_chip(
            {
                "hz_fix_down": 0.0,
                "hz_fix_up": 0.0,
                "hz_down": 8.0,
                "hz_up": 0.0,
                "hz_gui": 0.0,
            }
        )
        self.assertEqual(text, "net 8.0/s")
        self.assertNotIn("↓", text)
        self.assertNotIn("↑", text)


if __name__ == "__main__":
    unittest.main()

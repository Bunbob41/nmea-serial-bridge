"""Session stats CSV / clipboard export."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from ui.session_stats_export import (
    format_stats_clipboard_text,
    format_stats_csv,
    stats_csv_rows,
)


class TestSessionStatsExport(unittest.TestCase):
    def test_csv_has_metric_header_and_counters(self) -> None:
        snap = {
            "exported_at": "2026-06-15T12:00:00Z",
            "state": "running",
            "preset": "Desk",
            "com": "COM7",
            "baud": "115200",
            "network_mode": "udp_listen",
            "network_target": "0.0.0.0:10110",
            "nmea_mode": "strict",
            "status_serial": "Serial: COM7 @ 115200 — open",
            "status_network": "Network: UDP listen 0.0.0.0:10110 — 1 peer",
            "status_nmea": "NMEA: strict · running",
            "status_gnss": "GNSS: RTK fixed",
            "hz_down": 5.0,
            "hz_up": 0.5,
            "hz_gui": 0.0,
            "drops_n2s": 2,
            "drops_s2n": 0,
            "rej_n2s": 1,
            "rej_s2n": 0,
            "n2s_q": 0,
            "s2n_q": 0,
            "lines_down": 100,
            "lines_up": 4,
            "gnss_summary": "RTK fixed · 12 sats",
            "gnss_fix": "RTK fixed",
            "stats_line": "↓5.0 ↑0.5 msg/s",
        }
        csv_text = format_stats_csv(snap)
        self.assertIn("metric,value", csv_text)
        self.assertIn("drops_n2s,2", csv_text)
        self.assertIn("hz_down,5.00", csv_text)
        rows = stats_csv_rows(snap)
        self.assertEqual(rows[0], ("metric", "value"))
        self.assertIn(("com", "COM7"), rows)

    def test_clipboard_includes_queue_counters(self) -> None:
        text = format_stats_clipboard_text(
            {
                "exported_at": "t",
                "state": "stopped",
                "preset": "",
                "com": "COM7",
                "baud": "115200",
                "network_mode": "udp_listen",
                "network_target": "0.0.0.0:10110",
                "nmea_mode": "passthrough",
                "status_serial": "",
                "status_network": "",
                "status_nmea": "",
                "status_gnss": "",
                "hz_down": 0.0,
                "hz_up": 0.0,
                "hz_gui": 0.0,
                "drops_n2s": 0,
                "drops_s2n": 0,
                "rej_n2s": 0,
                "rej_s2n": 0,
                "n2s_q": 3,
                "s2n_q": 1,
                "lines_down": 0,
                "lines_up": 0,
                "gnss_summary": "—",
                "stats_line": "",
            }
        )
        self.assertIn("queue_n2s: 3", text)
        self.assertIn("queue_s2n: 1", text)


if __name__ == "__main__":
    unittest.main()

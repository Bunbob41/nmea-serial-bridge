"""Tests for Modern connection health chip formatting."""
from __future__ import annotations

import unittest

from ui.connection_health import format_connection_health_chip


class TestConnectionHealthChip(unittest.TestCase):
    def test_idle_preview_from_fallbacks(self) -> None:
        text, kind, tip = format_connection_health_chip(
            serial_line="Serial: stopped",
            network_line="Network: stopped",
            nmea_mode="strict",
            running=False,
            fallback_com="COM7",
            fallback_udp_port="10110",
        )
        self.assertIn("COM7", text)
        self.assertIn("UDP:10110", text)
        self.assertIn("strict", text)
        self.assertIn("Stop", text)
        self.assertEqual(kind, "idle")
        self.assertIn("Serial", tip)

    def test_running_healthy(self) -> None:
        text, kind, _ = format_connection_health_chip(
            serial_line="Serial: COM7 @ 115200 — open",
            network_line="Network: UDP listen 0.0.0.0:10110 — 1 peer",
            nmea_mode="passthrough",
            running=True,
        )
        self.assertIn("COM7", text)
        self.assertIn("UDP:10110", text)
        self.assertIn("pass", text)
        self.assertIn("Run", text)
        self.assertEqual(kind, "ok")

    def test_serial_retry_warns(self) -> None:
        _, kind, _ = format_connection_health_chip(
            serial_line="Serial: disconnected — retry in 3s…",
            network_line="Network: UDP listen 0.0.0.0:10110 — 1 peer",
            nmea_mode="raw",
            running=True,
        )
        self.assertEqual(kind, "warn")

    def test_starting_session(self) -> None:
        text, kind, _ = format_connection_health_chip(
            serial_line="Serial: opening COM7 @ 115200…",
            network_line="Network: starting…",
            nmea_mode="strict",
            running=False,
            starting=True,
        )
        self.assertIn("Start…", text)
        self.assertEqual(kind, "warn")


if __name__ == "__main__":
    unittest.main()

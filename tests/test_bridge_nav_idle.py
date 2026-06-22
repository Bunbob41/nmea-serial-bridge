"""GNSS metrics clear when NMEA traffic stops (HUD / status bar retention fix)."""
from __future__ import annotations

import asyncio
import time
import unittest

from bridge_core import NetMode, SerialNetBridge
from nmea_codec import NmeaMode

_SAMPLE_RTK = (
    b"$GPGGA,123519,4807.038,N,01131.000,E,4,12,0.9,545.4,M,46.9,M,,*6A\r\n"
)


class TestBridgeNavIdle(unittest.TestCase):
    def _make_bridge(self) -> SerialNetBridge:
        loop = asyncio.new_event_loop()
        return SerialNetBridge(
            "COM99",
            115200,
            NetMode.UDP_LISTEN,
            loop=loop,
            udp_listen=("127.0.0.1", 10110),
            nmea_mode=NmeaMode.PASSTHROUGH,
        )

    def test_live_gga_then_clear_on_zero_hz(self) -> None:
        bridge = self._make_bridge()
        bridge.running = True
        bridge._ingest_net(_SAMPLE_RTK, "UDP←('127.0.0.1', 10110)")
        live = bridge.navigation_quality_stats()
        self.assertEqual(live.get("num_sats"), 12)
        self.assertEqual(live.get("quality"), 4)
        self.assertNotEqual(live.get("summary"), "No Data Stream")

        bridge._hz_remote_times.clear()
        bridge._hz_gui_times.clear()
        bridge._hz_serial_times.clear()
        bridge._hz_fix_n2s_times.clear()
        bridge._hz_fix_s2n_times.clear()
        idle = bridge.navigation_quality_stats()
        self.assertEqual(idle.get("summary"), "No Data Stream")
        self.assertEqual(idle.get("num_sats"), 0)
        self.assertEqual(idle.get("quality"), 0)
        self.assertTrue(idle.get("stream_idle"))

    def test_clear_within_two_seconds_when_gga_stale(self) -> None:
        bridge = self._make_bridge()
        bridge.running = True
        bridge._ingest_net(_SAMPLE_RTK, "UDP←('127.0.0.1', 10110)")
        nav = bridge._nav_quality_state[0]
        assert nav is not None
        nav["mono"] = time.monotonic() - 2.1
        bridge._hz_remote_times.append(time.monotonic())
        idle = bridge.navigation_quality_stats()
        self.assertEqual(idle.get("summary"), "No Data Stream")
        self.assertEqual(idle.get("num_sats"), 0)

    def test_navigation_quality_matches_stats_when_idle(self) -> None:
        bridge = self._make_bridge()
        bridge.running = True
        bridge._ingest_net(_SAMPLE_RTK, "UDP←('127.0.0.1', 10110)")
        bridge._hz_remote_times.clear()
        nav = bridge.navigation_quality()
        assert nav is not None
        self.assertEqual(nav.get("summary"), "No Data Stream")


if __name__ == "__main__":
    unittest.main()

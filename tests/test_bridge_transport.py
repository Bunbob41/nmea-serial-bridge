"""Tests for bridge transport truth (session timers, COM active, UDP peers)."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

import bridge_core
from bridge_core import COM_FLOW_GAP_S, SerialNetBridge, NetMode, UDP_PEER_STALE_S


_SHARED_LOOP = asyncio.new_event_loop()


def _make_bridge() -> SerialNetBridge:
    return SerialNetBridge(
        com="COM99",
        baud=115200,
        mode=NetMode.UDP_LISTEN,
        udp_listen=("0.0.0.0", 10110),
        loop=_SHARED_LOOP,
    )


class TestBridgeTransportStats(unittest.TestCase):
    def test_transport_stats_keys(self) -> None:
        b = _make_bridge()
        b.running = True
        b._serial_open = True
        b.serial_reader = MagicMock()
        b._session_started_mono = 100.0
        with patch.object(bridge_core.time, "monotonic", return_value=160.0):
            stats = b.transport_stats()
        self.assertIn("session_running_s", stats)
        self.assertIn("com_active_total_s", stats)
        self.assertIn("last_com_to_net_age_s", stats)
        self.assertIn("udp_peer_details", stats)
        self.assertEqual(stats["session_running_s"], 60.0)
        self.assertEqual(stats["serial_link_state"], "open")

    def test_com_active_accumulates_within_gap(self) -> None:
        b = _make_bridge()
        with patch.object(bridge_core.time, "monotonic", side_effect=[100.0, 101.0, 102.0]):
            b._note_com_to_net_activity()
            b._note_com_to_net_activity()
        self.assertAlmostEqual(b._com_active_total_s, 1.0)

    def test_com_active_skips_long_gap(self) -> None:
        b = _make_bridge()
        with patch.object(bridge_core.time, "monotonic", side_effect=[100.0, 100.0, 105.0, 105.0]):
            b._note_com_to_net_activity()
            b._note_com_to_net_activity()
        self.assertAlmostEqual(b._com_active_total_s, 0.0)

    def test_com_active_live_includes_open_flow(self) -> None:
        b = _make_bridge()
        b._com_active_total_s = 10.0
        b._com_flow_last_mono = 100.0
        with patch.object(bridge_core.time, "monotonic", return_value=100.0 + COM_FLOW_GAP_S - 0.5):
            live = b._com_active_total_s_live()
        self.assertAlmostEqual(live, 10.0 + COM_FLOW_GAP_S - 0.5)

    def test_last_com_to_net_age_s(self) -> None:
        b = _make_bridge()
        b._last_com_to_net_mono = 50.0
        with patch.object(bridge_core.time, "monotonic", return_value=58.0):
            self.assertAlmostEqual(b.last_com_to_net_age_s(), 8.0)

    def test_last_com_to_net_age_none_before_data(self) -> None:
        b = _make_bridge()
        self.assertIsNone(b.last_com_to_net_age_s())

    def test_serial_ingest_notes_com_activity(self) -> None:
        b = _make_bridge()
        b.running = True
        b.nmea_mode = bridge_core.NmeaMode.RAW
        b._enqueue_serial_to_net = MagicMock()
        with patch.object(b, "_note_com_to_net_activity") as note:
            b._ingest_serial(b"$GNGGA\r\n", "SER→NET")
            note.assert_called_once()

    def test_udp_peer_details_stale_flag(self) -> None:
        b = _make_bridge()
        peer = ("10.0.0.1", 10110)
        b._udp_peers.add(peer)
        now = 1000.0
        b._udp_peer_last_in[peer] = now - UDP_PEER_STALE_S - 1
        with patch.object(bridge_core.time, "monotonic", return_value=now):
            rows = b.udp_peer_details()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["stale"])
        self.assertIn("10.0.0.1:10110", rows[0]["addr"])

    def test_transport_session_summary_finalize_flushes_flow(self) -> None:
        b = _make_bridge()
        with patch.object(
            bridge_core.time,
            "monotonic",
            side_effect=[200.0, 201.5, 201.5, 201.5, 201.5],
        ):
            b._note_com_to_net_activity()
            summary = b.transport_session_summary(finalize=True)
        self.assertAlmostEqual(summary["com_active_total_s"], 1.5)
        self.assertEqual(b._com_flow_last_mono, 0.0)

    def test_session_counters_reset_on_start(self) -> None:
        b = _make_bridge()
        b._com_active_total_s = 99.0
        b._last_com_to_net_mono = 50.0
        with patch.object(bridge_core.time, "monotonic", return_value=1000.0):
            b.running = True
            b._session_started_mono = 1000.0
            b._last_com_to_net_mono = 0.0
            b._com_flow_last_mono = 0.0
            b._com_active_total_s = 0.0
        self.assertEqual(b._com_active_total_s, 0.0)
        self.assertEqual(b._last_com_to_net_mono, 0.0)


if __name__ == "__main__":
    unittest.main()

"""Tests for transport truth formatters (COM/UDP/session timing)."""
from __future__ import annotations

import unittest

from ui.transport_status import (
    COM_DATA_STALE_S,
    UDP_PEER_STALE_S,
    activity_transport_labels,
    connection_health_transport_suffix,
    format_age_s,
    format_duration_s,
    format_transport_stop_summary,
    web_transport_summary,
)


class TestFormatAgeDuration(unittest.TestCase):
    def test_format_age_s_none(self) -> None:
        self.assertEqual(format_age_s(None), "never")

    def test_format_age_s_subsecond(self) -> None:
        self.assertEqual(format_age_s(0.4), "<1s")

    def test_format_age_s_seconds(self) -> None:
        self.assertEqual(format_age_s(45.7), "45s")

    def test_format_age_s_minutes(self) -> None:
        self.assertEqual(format_age_s(125), "2m 5s")

    def test_format_age_s_hours(self) -> None:
        self.assertEqual(format_age_s(3661), "1h 1m")

    def test_format_duration_s_seconds_only(self) -> None:
        self.assertEqual(format_duration_s(8), "8s")

    def test_format_duration_s_minutes(self) -> None:
        self.assertEqual(format_duration_s(125), "2m 5s")

    def test_format_duration_s_hours(self) -> None:
        self.assertEqual(format_duration_s(3661), "1h 1m 1s")


class TestActivityTransportLabels(unittest.TestCase):
    def test_stopped_serial_udp(self) -> None:
        stats = {"running": False, "net_mode": "udp_listen"}
        serial_t, _, serial_k, udp_t, _, udp_k, sess_t, _ = activity_transport_labels(stats)
        self.assertIn("stopped", serial_t.lower())
        self.assertEqual(serial_k, "idle")
        self.assertIn("stopped", udp_t.lower())
        self.assertEqual(udp_k, "idle")
        self.assertIn("Session", sess_t)

    def test_running_no_com_data_warns(self) -> None:
        stats = {
            "running": True,
            "serial_link_state": "open",
            "last_com_to_net_age_s": None,
            "net_mode": "udp_listen",
            "udp_peer_details": [],
        }
        serial_t, _, serial_k, udp_t, _, udp_k, _, _ = activity_transport_labels(stats)
        self.assertIn("no COM data", serial_t)
        self.assertEqual(serial_k, "warn")
        self.assertIn("no peers", udp_t)
        self.assertEqual(udp_k, "warn")

    def test_running_com_and_peer_ok(self) -> None:
        stats = {
            "running": True,
            "serial_link_state": "open",
            "last_com_to_net_age_s": 5.0,
            "net_mode": "udp_listen",
            "udp_fanout": True,
            "session_running_s": 120.0,
            "com_active_total_s": 90.0,
            "udp_peer_details": [
                {
                    "addr": "192.168.1.10:5000",
                    "last_in_s": 3.0,
                    "stale": False,
                    "is_last_sender": True,
                }
            ],
        }
        serial_t, _, serial_k, udp_t, _, udp_k, sess_t, sess_tip = activity_transport_labels(stats)
        self.assertIn("5s", serial_t)
        self.assertEqual(serial_k, "ok")
        self.assertIn("192.168.1.10:5000", udp_t)
        self.assertEqual(udp_k, "ok")
        self.assertIn("2m", sess_t)
        self.assertIn("COM data active", sess_tip)

    def test_stale_com_data_warns(self) -> None:
        stats = {
            "running": True,
            "serial_link_state": "open",
            "last_com_to_net_age_s": COM_DATA_STALE_S + 10,
            "net_mode": "udp_listen",
            "udp_peer_details": [],
        }
        _, _, serial_k, _, _, _, _, _ = activity_transport_labels(stats)
        self.assertEqual(serial_k, "warn")

    def test_udp_remote_mode(self) -> None:
        stats = {
            "running": True,
            "net_mode": "udp_remote",
            "udp_remote_host": "10.0.0.5",
            "udp_remote_port": 4001,
            "serial_link_state": "open",
            "last_com_to_net_age_s": 2.0,
        }
        _, _, _, udp_t, udp_tip, udp_k, _, _ = activity_transport_labels(stats)
        self.assertIn("10.0.0.5:4001", udp_t)
        self.assertEqual(udp_k, "ok")
        self.assertIn("remote", udp_tip.lower())


class TestConnectionHealthTransportSuffix(unittest.TestCase):
    def test_idle_when_not_running(self) -> None:
        suffix, extra = connection_health_transport_suffix({"running": False})
        self.assertEqual(suffix, "")
        self.assertEqual(extra, "")

    def test_listen_with_fresh_peer(self) -> None:
        suffix, extra = connection_health_transport_suffix(
            {
                "running": True,
                "last_com_to_net_age_s": 12.0,
                "net_mode": "udp_listen",
                "udp_peer_details": [{"last_in_s": 8.0, "stale": False}],
            }
        )
        self.assertIn("COM 12s", suffix)
        self.assertIn("UDP 8s", suffix)
        self.assertIn("COM data age", extra)
        self.assertIn("newest inbound", extra)

    def test_stale_peers_warn_marker(self) -> None:
        suffix, _ = connection_health_transport_suffix(
            {
                "running": True,
                "last_com_to_net_age_s": 5.0,
                "net_mode": "udp_listen",
                "udp_peer_details": [
                    {"last_in_s": UDP_PEER_STALE_S + 5, "stale": True},
                ],
            }
        )
        self.assertIn("⚠", suffix)


class TestStopSummaryAndWeb(unittest.TestCase):
    def test_format_transport_stop_summary(self) -> None:
        block = format_transport_stop_summary(
            {
                "session_running_s": 300.0,
                "com_active_total_s": 240.0,
                "last_com_to_net_age_s": 4.0,
                "lines_up": 42,
                "net_mode": "udp_listen",
                "udp_peer_details": [
                    {"addr": "10.0.0.1:10110", "last_in_s": 30.0},
                ],
            }
        )
        self.assertIn("[Transport] Session summary", block)
        self.assertIn("Running: 5m", block)
        self.assertIn("COM data active: 4m", block)
        self.assertIn("Lines COM→net: 42", block)
        self.assertIn("10.0.0.1:10110", block)

    def test_web_transport_summary_fields(self) -> None:
        out = web_transport_summary(
            {
                "running": True,
                "session_running_s": 60.0,
                "com_active_total_s": 45.0,
                "last_com_to_net_age_s": 2.0,
                "serial_link_state": "open",
                "net_mode": "udp_listen",
                "udp_peer_details": [
                    {"last_in_s": 10.0, "stale": False},
                    {"last_in_s": 25.0, "stale": True},
                ],
            }
        )
        self.assertEqual(out["com_active_total_s"], 45.0)
        self.assertEqual(out["udp_peer_count"], 2)
        self.assertEqual(out["udp_peer_newest_in_s"], 10.0)
        self.assertFalse(out["udp_peer_stale"])

    def test_web_transport_summary_all_stale(self) -> None:
        out = web_transport_summary(
            {
                "running": True,
                "udp_peer_details": [
                    {"last_in_s": 90.0, "stale": True},
                ],
            }
        )
        self.assertTrue(out["udp_peer_stale"])


if __name__ == "__main__":
    unittest.main()

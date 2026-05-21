"""Unit tests for discovery_service (Connection Hub passive discovery)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from discovery_service import (
    DEFAULT_KEYWORDS,
    build_network_cards,
    build_snapshot,
    probe_udp_port_available,
    scan_serial_ports,
    serial_device_id,
)


def _make_port(device: str, description: str = "", manufacturer: str = "", hwid: str = ""):
    p = MagicMock()
    p.device = device
    p.description = description
    p.manufacturer = manufacturer
    p.hwid = hwid
    return p


class TestDiscoveryDefaults(unittest.TestCase):
    def test_keywords_match_auto_discovery(self) -> None:
        self.assertIn("Trimble", DEFAULT_KEYWORDS)
        self.assertNotIn("FTDI", DEFAULT_KEYWORDS)


class TestScanSerialPorts(unittest.TestCase):
    def test_stable_polls_required(self) -> None:
        port = _make_port("COM7", description="Trimble GPS")
        counts: dict[str, int] = {}
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            devs, counts = scan_serial_ports(stable_counts=counts, stable_polls_required=2)
        self.assertEqual(devs, [])
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            devs, counts = scan_serial_ports(stable_counts=counts, stable_polls_required=2)
        self.assertEqual(len(devs), 1)
        self.assertEqual(devs[0].port, "COM7")

    def test_ignores_non_gnss(self) -> None:
        port = _make_port("COM3", description="Arduino")
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[port]):
            devs, _ = scan_serial_ports(stable_polls_required=1)
        self.assertEqual(devs, [])


class TestNetworkCards(unittest.TestCase):
    def test_running_peer_count(self) -> None:
        cards = build_network_cards(
            bridge_stats={"running": True, "udp_peers": 2, "udp_listen_host": "0.0.0.0", "udp_listen_port": 10110},
            default_udp_port=10110,
        )
        self.assertEqual(cards[0].peer_count, 2)
        self.assertEqual(cards[0].status, "running")

    @patch("discovery_service.probe_udp_port_available", return_value=False)
    def test_port_busy(self, _probe: MagicMock) -> None:
        cards = build_network_cards(default_udp_port=10110)
        self.assertEqual(cards[0].status, "port_busy")


class TestBuildSnapshot(unittest.TestCase):
    def test_returns_counts(self) -> None:
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[]):
            snap, counts = build_snapshot()
        self.assertIsInstance(counts, dict)
        self.assertEqual(len(snap.network_cards), 1)


class TestProbeUdpPort(unittest.TestCase):
    def test_invalid_port(self) -> None:
        self.assertFalse(probe_udp_port_available("0.0.0.0", 99999))


class TestSerialDeviceId(unittest.TestCase):
    def test_hwid_preferred(self) -> None:
        p = _make_port("COM1", hwid="USB\\VID_1234")
        self.assertEqual(serial_device_id(p), "serial:USB\\VID_1234")


if __name__ == "__main__":
    unittest.main()

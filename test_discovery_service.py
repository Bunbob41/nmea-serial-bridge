"""Unit tests for discovery_service (Connection Hub passive discovery)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from discovery_service import (
    DEFAULT_KEYWORDS,
    build_network_cards,
    build_snapshot,
    merge_discovered_network_cards,
    probe_udp_port_available,
    scan_serial_ports,
    serial_device_id,
)
from network_scanner import NetworkScanResult


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


class TestHostInterfaces(unittest.TestCase):
    def test_parse_ipconfig(self) -> None:
        from network_scanner import list_host_ipv4_interfaces

        sample = """
Ethernet adapter Ethernet:

   IPv4 Address. . . . . . . . . . . : 192.168.1.42
Wireless LAN adapter Wi-Fi:

   IPv4 Address. . . . . . . . . . . : 10.0.0.8
"""
        ifaces = list_host_ipv4_interfaces(ipconfig_output=sample)
        addrs = {i.address for i in ifaces}
        self.assertIn("192.168.1.42", addrs)
        self.assertIn("10.0.0.8", addrs)

    def test_merge_host_interface_cards(self) -> None:
        from network_scanner import HostIpv4Interface

        from discovery_service import build_network_cards, merge_host_interface_cards

        base = build_network_cards(default_udp_port=10110)
        merged = merge_host_interface_cards(
            base,
            [HostIpv4Interface("Ethernet", "192.168.50.2")],
            default_udp_port=10110,
        )
        self.assertGreater(len(merged), len(base))
        self.assertTrue(any(c.host == "192.168.50.2" for c in merged))

    def test_resolve_iface_device_id(self) -> None:
        from discovery_service import resolve_network_bind_from_device_id

        bind = resolve_network_bind_from_device_id("net:iface:Ethernet:192.168.1.10")
        self.assertEqual(bind, ("192.168.1.10", 10110))

    def test_tailscale_unknown_adapter_ipconfig(self) -> None:
        from network_scanner import list_host_ipv4_interfaces

        sample = """
Unknown adapter Tailscale:

   IPv4 Address. . . . . . . . . . . : 100.64.0.1
"""
        ifaces = list_host_ipv4_interfaces(ipconfig_output=sample)
        addrs = {i.address for i in ifaces}
        self.assertIn("100.64.0.1", addrs)

    def test_resolve_tailscale_device_id(self) -> None:
        from discovery_service import resolve_network_bind_from_device_id

        bind = resolve_network_bind_from_device_id("net:tailscale:100.108.1.2")
        self.assertEqual(bind, ("100.108.1.2", 10110))


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
            with patch("network_scanner.list_host_ipv4_interfaces", return_value=[]):
                with patch("discovery_service.merge_tailscale_bind_cards", side_effect=lambda c, **_: c):
                    snap, counts = build_snapshot()
        self.assertIsInstance(counts, dict)
        self.assertEqual(len(snap.network_cards), 1)

    def test_merge_discovered_hosts(self) -> None:
        base = build_network_cards(default_udp_port=10110)
        scan = [
            NetworkScanResult(
                host="192.168.1.50",
                mac="",
                open_ports=(10110,),
                method="udp_probe",
                label="192.168.1.50 (UDP 10110)",
                stale=False,
                last_seen_mono=0.0,
            )
        ]
        merged = merge_discovered_network_cards(base, scan)
        self.assertGreater(len(merged), len(base))
        ids = [c.device_id for c in merged]
        self.assertTrue(any("discovered" in i for i in ids))

    def test_build_snapshot_with_scan_results(self) -> None:
        with patch("discovery_service.serial.tools.list_ports.comports", return_value=[]):
            snap, _ = build_snapshot(
                network_scan_results=[
                    NetworkScanResult(
                        "10.0.0.5",
                        "",
                        (10110,),
                        "udp_probe",
                        "10.0.0.5",
                        False,
                        0.0,
                    )
                ]
            )
        self.assertTrue(any("10.0.0.5" in c.host for c in snap.network_cards))


class TestProbeUdpPort(unittest.TestCase):
    def test_invalid_port(self) -> None:
        self.assertFalse(probe_udp_port_available("0.0.0.0", 99999))


class TestSerialDeviceId(unittest.TestCase):
    def test_hwid_preferred(self) -> None:
        p = _make_port("COM1", hwid="USB\\VID_1234")
        self.assertEqual(serial_device_id(p), "serial:USB\\VID_1234")


if __name__ == "__main__":
    unittest.main()

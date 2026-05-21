"""Tests for network_scanner LAN discovery."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from network_scanner import list_lan_hosts, probe_host_udp, scan_network

_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "arp_sample_windows.txt"


class TestListLanHosts(unittest.TestCase):
    def test_parses_arp_fixture(self) -> None:
        text = _FIXTURE.read_text(encoding="utf-8")
        hosts = list_lan_hosts(arp_output=text)
        self.assertIn("192.168.1.1", hosts)
        self.assertIn("192.168.1.50", hosts)

    def test_empty_arp_still_has_loopback(self) -> None:
        hosts = list_lan_hosts(arp_output="")
        self.assertIn("127.0.0.1", hosts)


class TestProbeHostUdp(unittest.TestCase):
    @patch("network_scanner.socket.socket")
    def test_returns_port_on_send_ok(self, mock_sock_cls) -> None:
        import socket as sock_mod

        inst = MagicMock()
        mock_sock_cls.return_value = inst
        inst.recvfrom.side_effect = sock_mod.timeout()
        ports = probe_host_udp("127.0.0.1", [10110], timeout_s=0.1)
        self.assertEqual(ports, (10110,))


class TestScanNetwork(unittest.TestCase):
    def test_respects_max_hosts(self) -> None:
        arp = "\n".join(f"  192.168.0.{i}          aa-bb-cc-dd-ee-{i:02d}     dynamic" for i in range(1, 40))
        results = scan_network(arp_output=arp, max_hosts=5, deadline_s=2.0)
        self.assertLessEqual(len(results), 5)


if __name__ == "__main__":
    unittest.main()

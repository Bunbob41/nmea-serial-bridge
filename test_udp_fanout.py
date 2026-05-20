"""Tests for UDP fan-out: one COM port → multiple UDP peers."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch, call

import bridge_core
from bridge_core import SerialNetBridge, NetMode


_SHARED_LOOP = asyncio.new_event_loop()


def _make_bridge() -> SerialNetBridge:
    return SerialNetBridge(
        com="COM99",
        baud=115200,
        mode=NetMode.UDP_LISTEN,
        udp_listen=("0.0.0.0", 10110),
        loop=_SHARED_LOOP,
    )


class TestUdpPeerRegistration(unittest.TestCase):
    def test_first_datagram_registers_peer(self) -> None:
        b = _make_bridge()
        b.running = True
        b._ingest_net = MagicMock()
        b._set_status = MagicMock()

        b.on_udp_datagram(b"$GNGGA,*00\r\n", ("192.168.1.10", 5000))
        self.assertIn(("192.168.1.10", 5000), b._udp_peers)
        self.assertEqual(b.udp_peer_count, 1)
        self.assertEqual(b.last_udp_addr, ("192.168.1.10", 5000))

    def test_second_peer_adds_to_set(self) -> None:
        b = _make_bridge()
        b.running = True
        b._ingest_net = MagicMock()
        b._set_status = MagicMock()

        b.on_udp_datagram(b"data", ("192.168.1.10", 5000))
        b.on_udp_datagram(b"data", ("192.168.1.20", 5001))
        self.assertEqual(b.udp_peer_count, 2)
        self.assertIn(("192.168.1.10", 5000), b._udp_peers)
        self.assertIn(("192.168.1.20", 5001), b._udp_peers)

    def test_same_peer_twice_stays_one(self) -> None:
        b = _make_bridge()
        b.running = True
        b._ingest_net = MagicMock()
        b._set_status = MagicMock()

        b.on_udp_datagram(b"data", ("10.0.0.1", 9000))
        b.on_udp_datagram(b"data", ("10.0.0.1", 9000))
        self.assertEqual(b.udp_peer_count, 1)

    def test_status_shows_multi_peer_label(self) -> None:
        b = _make_bridge()
        b.running = True
        b._ingest_net = MagicMock()
        b._set_status = MagicMock()

        b.on_udp_datagram(b"data", ("10.0.0.1", 1))
        b.on_udp_datagram(b"data", ("10.0.0.2", 2))

        # Second call should show "2 peers" in status
        last_net_status = b._set_status.call_args[0][1]
        self.assertIn("2 peers", last_net_status)

    def test_single_peer_status_shows_addr(self) -> None:
        b = _make_bridge()
        b.running = True
        b._ingest_net = MagicMock()
        b._set_status = MagicMock()

        b.on_udp_datagram(b"data", ("10.0.0.5", 4321))
        last_net_status = b._set_status.call_args[0][1]
        self.assertIn("10.0.0.5", last_net_status)
        self.assertNotIn("peers", last_net_status)

    def test_not_running_ignores_datagram(self) -> None:
        b = _make_bridge()
        b.running = False
        b._ingest_net = MagicMock()
        b.on_udp_datagram(b"data", ("1.2.3.4", 99))
        self.assertEqual(b.udp_peer_count, 0)
        b._ingest_net.assert_not_called()


class TestUdpFanOutSend(unittest.TestCase):
    def setUp(self) -> None:
        self._loop = asyncio.new_event_loop()

    def tearDown(self) -> None:
        self._loop.close()

    def _run(self, coro):  # type: ignore[no-untyped-def]
        return self._loop.run_until_complete(coro)

    def test_sends_to_all_peers(self) -> None:
        b = _make_bridge()
        b.running = True
        transport = MagicMock()
        b.udp_transport = transport
        b._udp_peers = {("10.0.0.1", 1), ("10.0.0.2", 2), ("10.0.0.3", 3)}

        self._run(b._send_net(b"hello"))

        self.assertEqual(transport.sendto.call_count, 3)
        sent_addrs = {c.args[1] for c in transport.sendto.call_args_list}
        self.assertEqual(sent_addrs, {("10.0.0.1", 1), ("10.0.0.2", 2), ("10.0.0.3", 3)})

    def test_dead_peer_removed_on_error(self) -> None:
        b = _make_bridge()
        b.running = True
        transport = MagicMock()
        b.udp_transport = transport
        b._ui_log = MagicMock()
        peer_good = ("10.0.0.1", 1)
        peer_dead = ("10.0.0.2", 2)
        b._udp_peers = {peer_good, peer_dead}
        b.last_udp_addr = peer_dead

        def _sendto_side(data, addr):
            if addr == peer_dead:
                raise OSError("Network unreachable")

        transport.sendto.side_effect = _sendto_side
        self._run(b._send_net(b"data"))

        self.assertNotIn(peer_dead, b._udp_peers)
        self.assertIn(peer_good, b._udp_peers)
        # last_udp_addr updated away from dead peer
        self.assertNotEqual(b.last_udp_addr, peer_dead)

    def test_no_peers_no_send(self) -> None:
        b = _make_bridge()
        b.running = True
        transport = MagicMock()
        b.udp_transport = transport
        b._udp_peers = set()

        self._run(b._send_net(b"data"))
        transport.sendto.assert_not_called()

    def test_single_link_mode_sends_only_to_last_peer(self) -> None:
        """udp_fanout=False must send only to last_udp_addr, ignoring other peers."""
        b = SerialNetBridge(
            com="COM99", baud=115200, mode=NetMode.UDP_LISTEN,
            udp_listen=("0.0.0.0", 10110), udp_fanout=False, loop=self._loop,
        )
        transport = MagicMock()
        b.udp_transport = transport
        b._ui_log = MagicMock()
        b._udp_peers = {("10.0.0.1", 1), ("10.0.0.2", 2)}
        b.last_udp_addr = ("10.0.0.2", 2)

        self._run(b._send_net(b"data"))

        transport.sendto.assert_called_once_with(b"data", ("10.0.0.2", 2))

    def test_single_link_no_send_when_no_last_addr(self) -> None:
        """udp_fanout=False with no last_udp_addr must not call sendto."""
        b = SerialNetBridge(
            com="COM99", baud=115200, mode=NetMode.UDP_LISTEN,
            udp_listen=("0.0.0.0", 10110), udp_fanout=False, loop=self._loop,
        )
        transport = MagicMock()
        b.udp_transport = transport
        b.last_udp_addr = None

        self._run(b._send_net(b"data"))
        transport.sendto.assert_not_called()

    def test_udp_fanout_default_is_true(self) -> None:
        """Default constructor must have fan-out enabled."""
        b = _make_bridge()
        self.assertTrue(b._udp_fanout)

    def test_udp_remote_mode_uses_single_sendto(self) -> None:
        """UDP_REMOTE (connected socket) must not fan-out — uses sendto() with no addr."""
        b = SerialNetBridge(
            com="COM99",
            baud=115200,
            mode=NetMode.UDP_REMOTE,
            udp_remote=("1.2.3.4", 9999),
            loop=self._loop,
        )
        transport = MagicMock()
        b.udp_transport = transport
        b._ui_log = MagicMock()
        b._udp_peers = {("5.5.5.5", 5555)}  # should be ignored in REMOTE mode

        self._run(b._send_net(b"data"))
        transport.sendto.assert_called_once_with(b"data")


class TestUdpPeerAbortCleanup(unittest.TestCase):
    def test_abort_clears_peers(self) -> None:
        b = _make_bridge()
        b._udp_peers = {("1.2.3.4", 1), ("5.6.7.8", 2)}
        b.last_udp_addr = ("1.2.3.4", 1)
        b.abort_now()
        self.assertEqual(b.udp_peer_count, 0)
        self.assertIsNone(b.last_udp_addr)

    def test_peer_count_in_stats(self) -> None:
        b = _make_bridge()
        stats_received: list[dict] = []
        b._stats_cb = stats_received.append
        b._udp_peers = {("10.0.0.1", 1), ("10.0.0.2", 2)}
        b._emit_stats()
        self.assertEqual(stats_received[-1]["udp_peers"], 2)


if __name__ == "__main__":
    unittest.main()

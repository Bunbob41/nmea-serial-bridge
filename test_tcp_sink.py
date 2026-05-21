"""Tests for optional TCP sink mirror alongside UDP fan-out."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from bridge_core import NetMode, SerialNetBridge, TcpSinkConfig


_SHARED_LOOP = asyncio.new_event_loop()


def _make_bridge(*, fanout: bool = True, sink: bool = True) -> SerialNetBridge:
    cfg = TcpSinkConfig(enabled=True, bind_port=10111) if sink else None
    return SerialNetBridge(
        com="COM99",
        baud=115200,
        mode=NetMode.UDP_LISTEN,
        udp_listen=("0.0.0.0", 10110),
        udp_fanout=fanout,
        tcp_sink=cfg,
        loop=_SHARED_LOOP,
    )


class TestTcpSinkMirror(unittest.TestCase):
    def test_mirror_writes_to_sink_clients(self) -> None:
        b = _make_bridge()
        b._tcp_sink = TcpSinkConfig(enabled=True, bind_port=10111)
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        b._tcp_sink_writers.add(writer)

        async def _run() -> None:
            await b._mirror_to_tcp_sink(b"$GNGGA,*00\r\n")

        _SHARED_LOOP.run_until_complete(_run())
        writer.write.assert_called_once_with(b"$GNGGA,*00\r\n")
        writer.drain.assert_awaited_once()

    def test_send_net_calls_mirror_when_sink_enabled(self) -> None:
        b = _make_bridge()
        b.udp_transport = MagicMock()
        b._tcp_sink = TcpSinkConfig(enabled=True)
        b._udp_fanout = True
        b._udp_peers.add(("127.0.0.1", 5000))
        b._mirror_to_tcp_sink = AsyncMock()

        async def _run() -> None:
            await b._send_net(b"test")

        _SHARED_LOOP.run_until_complete(_run())
        b.udp_transport.sendto.assert_called()
        b._mirror_to_tcp_sink.assert_awaited_once_with(b"test")


if __name__ == "__main__":
    unittest.main()

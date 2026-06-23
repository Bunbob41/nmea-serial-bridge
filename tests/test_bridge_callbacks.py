"""Bridge callback safety — stats/status must not abort ingest."""
from __future__ import annotations

import asyncio
import unittest
from typing import Optional

from bridge_core import NetMode, SerialNetBridge
from nmea_codec import NmeaMode

_GGA = (
    b"$GPGGA,032358.34,3600.42235,N,11846.36546,W,5,09,1.9,0.0,M,15.5,M,2.0,0000*51\r\n"
)


class TestBridgeCallbackSafety(unittest.TestCase):
    def setUp(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def tearDown(self) -> None:
        if self._loop is not None and not self._loop.is_closed():
            self._loop.close()
        self._loop = None

    def _bridge(self, **kwargs: object) -> SerialNetBridge:
        self._loop = asyncio.new_event_loop()
        return SerialNetBridge(
            "COM99",
            115200,
            NetMode.UDP_LISTEN,
            loop=self._loop,
            udp_listen=("127.0.0.1", 10110),
            nmea_mode=NmeaMode.PASSTHROUGH,
            **kwargs,
        )

    def test_emit_stats_survives_stats_cb_failure(self) -> None:
        logs: list[str] = []

        def bad_stats(_d: dict) -> None:
            raise TypeError("__init__() should return None, not 'NoneType'")

        bridge = self._bridge(ui_log=logs.append, stats_cb=bad_stats)
        bridge.running = True
        bridge._ingest_net(_GGA, "UDP←('127.0.0.1', 10110)")
        bridge._emit_stats()
        self.assertTrue(any("UI callback error" in line for line in logs))

    def test_on_udp_survives_ingest_failure(self) -> None:
        logs: list[str] = []
        bridge = self._bridge(ui_log=logs.append)
        bridge.running = True

        def boom(*_a: object, **_k: object) -> None:
            raise RuntimeError("ingest failed")

        bridge._ingest_net = boom  # type: ignore[method-assign]
        bridge.on_udp_datagram(_GGA, ("192.168.1.160", 60046))
        self.assertTrue(any("handler error" in line for line in logs))


if __name__ == "__main__":
    unittest.main()

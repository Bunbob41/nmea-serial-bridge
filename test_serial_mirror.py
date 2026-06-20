"""Serial mirror ports — parse helpers and bridge write fan-out."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from bridge_core import (
    NetMode,
    SerialMirrorConfig,
    SerialNetBridge,
    parse_serial_mirror_ports,
)


class TestParseSerialMirrorPorts(unittest.TestCase):
    def test_parses_and_dedupes(self) -> None:
        ports = parse_serial_mirror_ports("com12, COM13; COM12", primary="COM7")
        self.assertEqual(ports, ("COM12", "COM13"))

    def test_skips_primary_and_caps_at_two(self) -> None:
        ports = parse_serial_mirror_ports("COM7, COM8, COM9, COM10", primary="COM7")
        self.assertEqual(ports, ("COM8", "COM9"))


class TestSerialMirrorBridge(unittest.TestCase):
    def setUp(self) -> None:
        self._loop = asyncio.new_event_loop()

    def tearDown(self) -> None:
        self._loop.close()

    def _run(self, coro):
        return self._loop.run_until_complete(coro)

    def test_tx_mirror_broadcasts_to_extra_serial(self) -> None:
        bridge = SerialNetBridge(
            "COM7",
            115200,
            NetMode.UDP_LISTEN,
            udp_listen=("0.0.0.0", 10110),
            loop=self._loop,
            serial_mirror=SerialMirrorConfig(ports=("COM12",)),
        )
        bridge.running = True
        bridge.serial_writer = MagicMock()
        bridge.serial_writer.transport = MagicMock(serial=MagicMock())
        mirror_ser = MagicMock()
        bridge._mirror_serials = {"COM12": mirror_ser}
        with patch.object(bridge, "_write_chunk_to_writer", new_callable=AsyncMock) as primary_write:
            with patch.object(bridge, "_write_mirror_serial", new_callable=AsyncMock) as mirror_write:
                self._run(bridge._write_serial_bytes_locked(b"abc"))
        primary_write.assert_awaited_once()
        mirror_write.assert_awaited_once_with(mirror_ser, b"abc")

    def test_device_tx_schedules_mirror_from_serial_ingest(self) -> None:
        bridge = SerialNetBridge(
            "COM7",
            115200,
            NetMode.UDP_LISTEN,
            udp_listen=("0.0.0.0", 10110),
            loop=self._loop,
            serial_mirror=SerialMirrorConfig(ports=("COM12",), include_device_tx=True),
        )
        bridge.running = True
        bridge._mirror_serials = {"COM12": MagicMock()}
        with patch.object(bridge, "_schedule_mirror_broadcast") as sched:
            bridge._ingest_serial(b"$GGA\r\n", "SER->NET")
        sched.assert_called_once_with(b"$GGA\r\n")


if __name__ == "__main__":
    unittest.main()
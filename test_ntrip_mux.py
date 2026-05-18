"""NTRIP forwarder + COM mux path (mock caster, no live CORS account)."""
from __future__ import annotations

import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

from bridge_core import NetMode, NmeaMode, SerialNetBridge
from ntrip_client import NtripConfig, run_ntrip_forwarder


def _rtcm_like_chunks() -> list[bytes]:
    return [
        b"\xd3\x00\x08\x3e\xd0\x00\x03\x8a\x0e\xde",
        b"\xd3\x00\x13\x3e\xd7\x00\x03\x8a\x0e\xde\x00\x00\x00\x00\x00\x00\x00",
    ]


class _MockNtripCaster:
    """Minimal NTRIP v1 caster: 200 OK then RTCM-like bytes."""

    def __init__(self, chunks: list[bytes], *, require_auth: bool = False) -> None:
        self.chunks = list(chunks)
        self.require_auth = require_auth
        self._server: asyncio.AbstractServer | None = None
        self.requests: list[str] = []

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> tuple[str, int]:
        self._server = await asyncio.start_server(self._handle, host, port)
        sockets = self._server.sockets or []
        bound = sockets[0].getsockname()
        return str(bound[0]), int(bound[1])

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        buf = bytearray()
        while b"\r\n\r\n" not in buf and len(buf) < 8192:
            part = await reader.read(512)
            if not part:
                break
            buf.extend(part)
        req = buf.decode("latin-1", errors="replace")
        self.requests.append(req)
        if self.require_auth and "Authorization: Basic" not in req:
            writer.write(b"HTTP/1.0 401 Unauthorized\r\n\r\n")
        else:
            writer.write(
                b"HTTP/1.0 200 OK\r\n"
                b"Content-Type: application/octet-stream\r\n"
                b"\r\n"
            )
            for chunk in self.chunks:
                writer.write(chunk)
                await writer.drain()
            await asyncio.sleep(0.25)
        await writer.drain()
        writer.close()
        await writer.wait_closed()


class TestNtripMux(unittest.TestCase):
    def test_forwarder_receives_caster_chunks(self) -> None:
        async def _run() -> None:
            caster = _MockNtripCaster(_rtcm_like_chunks())
            host, port = await caster.start()
            received: list[bytes] = []
            running = True

            async def on_chunk(data: bytes) -> None:
                received.append(data)

            async def task() -> None:
                await run_ntrip_forwarder(
                    NtripConfig(host, port, "TEST"),
                    on_chunk,
                    lambda _m: None,
                    lambda: running,
                    reconnect_s=60.0,
                )

            fwd = asyncio.create_task(task())
            for _ in range(80):
                await asyncio.sleep(0.05)
                if len(received) >= 2:
                    break
            running = False
            try:
                await asyncio.wait_for(fwd, timeout=2.0)
            except asyncio.TimeoutError:
                fwd.cancel()
                try:
                    await fwd
                except asyncio.CancelledError:
                    pass
            await caster.stop()
            self.assertGreaterEqual(len(received), 1)
            self.assertTrue(any(c.startswith(b"\xd3") for c in received))

        asyncio.run(_run())

    def test_inject_correction_bypasses_nmea_line_counters(self) -> None:
        async def _run() -> None:
            loop = asyncio.new_event_loop()
            try:
                bridge = SerialNetBridge(
                    "COM_TEST",
                    115200,
                    NetMode.UDP_LISTEN,
                    udp_listen=("127.0.0.1", 0),
                    nmea_mode=NmeaMode.PASSTHROUGH,
                    loop=loop,
                )
                bridge.running = True
                bridge.serial_writer = MagicMock()
                bridge.serial_writer.write = MagicMock()
                bridge.serial_writer.drain = AsyncMock()
                written: list[bytes] = []

                async def capture(chunk: bytes) -> None:
                    written.append(chunk)

                bridge._write_serial_bytes_locked = capture  # type: ignore[method-assign]
                await bridge.inject_correction_bytes(_rtcm_like_chunks()[0])
                self.assertEqual(len(written), 1)
                self.assertEqual(bridge.lines_remote_to_serial, 0)
                self.assertEqual(bridge.lines_gui_to_serial, 0)
            finally:
                loop.close()

        asyncio.run(_run())

    def test_serial_writes_are_serialized(self) -> None:
        async def _run() -> None:
            loop = asyncio.new_event_loop()
            try:
                bridge = SerialNetBridge(
                    "COM_TEST",
                    115200,
                    NetMode.UDP_LISTEN,
                    udp_listen=("127.0.0.1", 0),
                    loop=loop,
                )
                bridge.running = True
                bridge.serial_writer = MagicMock()
                order: list[str] = []

                async def slow_write(chunk: bytes) -> None:
                    tag = chunk[:4].decode("latin-1", errors="replace")
                    order.append(f"start-{tag}")
                    await asyncio.sleep(0.02)
                    order.append(f"end-{tag}")

                bridge._write_serial_bytes_locked = slow_write  # type: ignore[method-assign]
                bridge._serial_write_lock = asyncio.Lock()
                await asyncio.gather(
                    bridge._write_serial_bytes(b"NET1"),
                    bridge.inject_correction_bytes(b"RTC1"),
                )
                self.assertEqual(order, ["start-NET1", "end-NET1", "start-RTC1", "end-RTC1"])
            finally:
                loop.close()

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()

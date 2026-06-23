"""Deterministic bridge state/mode invariants without hardware I/O."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from bridge_core import NetMode, SerialNetBridge
from nmea_codec import NmeaMode


class _DummyReader:
    async def read(self, _n: int) -> bytes:
        await asyncio.sleep(0.01)
        return b""


class _DummyWriter:
    def __init__(self, peer=None) -> None:
        self._peer = peer
        self.close_calls = 0
        self.wait_closed_calls = 0

    def close(self) -> None:
        self.close_calls += 1

    async def wait_closed(self) -> None:
        self.wait_closed_calls += 1

    def write(self, _data: bytes) -> None:
        return

    async def drain(self) -> None:
        return

    def get_extra_info(self, _name: str):
        return self._peer


class _DummyTransport:
    def close(self) -> None:
        return

    def sendto(self, _data: bytes, _addr=None) -> None:
        return


class _DummyServer:
    def close(self) -> None:
        return

    async def wait_closed(self) -> None:
        return

    async def serve_forever(self) -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            raise


class TestBridgeStateMachine(unittest.IsolatedAsyncioTestCase):
    async def _make_bridge(self, mode: NetMode) -> SerialNetBridge:
        loop = asyncio.get_running_loop()
        kwargs = {"loop": loop, "nmea_mode": NmeaMode.PASSTHROUGH}
        if mode == NetMode.UDP_LISTEN:
            kwargs["udp_listen"] = ("127.0.0.1", 10110)
        elif mode == NetMode.UDP_REMOTE:
            kwargs["udp_remote"] = ("127.0.0.1", 10110)
        elif mode == NetMode.TCP_SERVER:
            kwargs["tcp_bind_host"] = "127.0.0.1"
            kwargs["tcp_bind_port"] = 4040
        elif mode == NetMode.TCP_CLIENT:
            kwargs["tcp_client_host"] = "127.0.0.1"
            kwargs["tcp_client_port"] = 4041
        bridge = SerialNetBridge("COM99", 115200, mode, **kwargs)
        bridge._open_serial_stream = AsyncMock(return_value=(_DummyReader(), _DummyWriter()))  # type: ignore[method-assign]
        bridge._pump_net_to_serial = AsyncMock(return_value=None)  # type: ignore[method-assign]
        bridge._pump_serial_to_net_queue = AsyncMock(return_value=None)  # type: ignore[method-assign]
        bridge._serial_lifecycle_loop = AsyncMock(return_value=None)  # type: ignore[method-assign]
        bridge._tcp_client_runner = AsyncMock(return_value=None)  # type: ignore[method-assign]
        return bridge

    async def test_mode_start_stop_cycles(self) -> None:
        loop = asyncio.get_running_loop()
        udp_endpoint = AsyncMock(return_value=(_DummyTransport(), object()))
        with (
            patch.object(loop, "create_datagram_endpoint", udp_endpoint),
            patch("bridge_core.asyncio.start_server", AsyncMock(return_value=_DummyServer())),
        ):
            for mode in (
                NetMode.UDP_LISTEN,
                NetMode.UDP_REMOTE,
                NetMode.TCP_SERVER,
                NetMode.TCP_CLIENT,
            ):
                bridge = await self._make_bridge(mode)
                self.assertTrue(await bridge.start(), mode.value)
                self.assertTrue(bridge.running)
                await bridge.stop()
                self.assertFalse(bridge.running)
                self.assertTrue(await bridge.start(), f"{mode.value} second cycle")
                await bridge.stop()
                self.assertFalse(bridge.running)

    async def test_queue_pressure_counters_invariant(self) -> None:
        bridge = await self._make_bridge(NetMode.UDP_LISTEN)
        bridge.running = True
        bridge.net_to_serial = asyncio.Queue(maxsize=1)
        bridge.serial_to_net = asyncio.Queue(maxsize=1)
        bridge.net_to_serial.put_nowait(b"n2s")
        bridge.serial_to_net.put_nowait(b"s2n")

        bridge._enqueue_net_to_serial(b"overflow", "UDP←('127.0.0.1', 5555)")
        bridge._enqueue_serial_to_net(b"overflow", "SER→NET")

        self.assertEqual(bridge.drops_net_to_serial, 1)
        self.assertEqual(bridge.drops_serial_to_net, 1)

    async def test_udp_listen_peer_churn_no_counter_regression(self) -> None:
        bridge = await self._make_bridge(NetMode.UDP_LISTEN)
        bridge.running = True
        payload = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
        peers = [("127.0.0.1", 9900 + i) for i in range(30)]
        for addr in peers:
            bridge.on_udp_datagram(payload, addr)
            _ = bridge.net_to_serial.get_nowait()
        self.assertEqual(bridge.last_udp_addr, peers[-1])
        self.assertEqual(bridge.lines_remote_to_serial, len(peers))
        self.assertEqual(bridge.drops_net_to_serial, 0)
        self.assertEqual(bridge.rejected_net_to_serial, 0)

    async def test_udp_remote_peer_churn_no_counter_regression(self) -> None:
        bridge = await self._make_bridge(NetMode.UDP_REMOTE)
        bridge.running = True
        payload = b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n"
        peers = [("127.0.0.1", 12000 + i) for i in range(25)]
        for addr in peers:
            bridge.on_udp_datagram(payload, addr)
            _ = bridge.net_to_serial.get_nowait()
        self.assertEqual(bridge.last_udp_addr, peers[-1])
        self.assertEqual(bridge.lines_remote_to_serial, len(peers))
        self.assertEqual(bridge.drops_net_to_serial, 0)
        self.assertEqual(bridge.rejected_net_to_serial, 0)

    async def test_tcp_server_disconnect_reconnect_churn_replaces_writer(self) -> None:
        bridge = await self._make_bridge(NetMode.TCP_SERVER)
        bridge.running = True

        reader_a = _DummyReader()
        reader_b = _DummyReader()
        writer_a = _DummyWriter(peer=("10.0.0.10", 5001))
        writer_b = _DummyWriter(peer=("10.0.0.11", 5002))
        read_loop = AsyncMock(return_value=None)

        with patch.object(bridge, "_tcp_read_loop", read_loop):
            await bridge._on_tcp_client(reader_a, writer_a)
            await asyncio.sleep(0)
            await bridge._on_tcp_client(reader_b, writer_b)
            await asyncio.sleep(0)

        self.assertIs(bridge.tcp_reader, reader_b)
        self.assertIs(bridge.tcp_writer, writer_b)
        self.assertEqual(writer_a.close_calls, 1)
        self.assertEqual(writer_a.wait_closed_calls, 1)
        self.assertEqual(read_loop.await_count, 2)
        self.assertEqual(bridge.drops_net_to_serial, 0)
        self.assertEqual(bridge.rejected_net_to_serial, 0)
        self.assertEqual(bridge.drops_serial_to_net, 0)
        self.assertEqual(bridge.rejected_serial_to_net, 0)

    async def test_tcp_client_reconnect_storm_loop_no_counter_regression(self) -> None:
        loop = asyncio.get_running_loop()
        bridge = SerialNetBridge(
            "COM99",
            115200,
            NetMode.TCP_CLIENT,
            tcp_client_host="127.0.0.1",
            tcp_client_port=4041,
            tcp_reconnect_delay=0.5,
            loop=loop,
            nmea_mode=NmeaMode.PASSTHROUGH,
        )
        bridge.running = True
        bridge._network_ready = False

        connect_events = [
            ConnectionRefusedError("refused"),
            (_DummyReader(), _DummyWriter(peer=("127.0.0.1", 4041))),
            ConnectionResetError("reset"),
            (_DummyReader(), _DummyWriter(peer=("127.0.0.1", 4041))),
        ]
        connect_calls = {"n": 0}

        async def _open_connection(_host: str, _port: int):
            idx = connect_calls["n"]
            connect_calls["n"] += 1
            event = connect_events[idx]
            if isinstance(event, BaseException):
                raise event
            return event

        read_calls = {"n": 0}

        async def _read_once(_addr) -> None:
            read_calls["n"] += 1
            if read_calls["n"] >= 2:
                bridge.running = False

        with (
            patch("bridge_core.asyncio.open_connection", side_effect=_open_connection),
            patch("bridge_core.asyncio.sleep", AsyncMock(return_value=None)),
            patch.object(bridge, "_tcp_read_loop", side_effect=_read_once),
        ):
            await bridge._tcp_client_runner()

        self.assertGreaterEqual(connect_calls["n"], 4)
        self.assertEqual(read_calls["n"], 2)
        self.assertTrue(bridge._network_ready)
        self.assertEqual(bridge.drops_net_to_serial, 0)
        self.assertEqual(bridge.rejected_net_to_serial, 0)
        self.assertEqual(bridge.drops_serial_to_net, 0)
        self.assertEqual(bridge.rejected_serial_to_net, 0)

    async def test_raw_mode_preserves_binary_bytes(self) -> None:
        bridge = await self._make_bridge(NetMode.UDP_LISTEN)
        bridge.nmea_mode = NmeaMode.RAW
        bridge.running = True
        bridge.net_to_serial = asyncio.Queue()
        bridge.serial_to_net = asyncio.Queue()
        payload = bytes([0x00, 0xD3, 0x00, 0xFF, 0x81, 0x00, 0x13])
        bridge._ingest_net(payload, "UDP←('127.0.0.1', 10110)")
        self.assertEqual(bridge.net_to_serial.get_nowait(), payload)
        bridge._ingest_serial(payload, "SER→NET")
        self.assertEqual(bridge.serial_to_net.get_nowait(), payload)
        self.assertEqual(bridge._asm_n2s.pending_bytes, 0)
        self.assertEqual(bridge._asm_s2n.pending_bytes, 0)
        self.assertEqual(bridge.rejected_net_to_serial, 0)
        self.assertEqual(bridge.rejected_serial_to_net, 0)

    async def test_serial_reconnect_resets_assembler_buffers(self) -> None:
        bridge = await self._make_bridge(NetMode.UDP_LISTEN)
        bridge._asm_n2s._buf.extend(b"$GPGGA,partial")
        bridge._asm_s2n._buf.extend(b"$GPRMC,frag")
        bridge._serial_io_err_last_msg = "Serial: timed out"
        bridge._reset_serial_decode_state()
        self.assertEqual(bridge._asm_n2s.pending_bytes, 0)
        self.assertEqual(bridge._asm_s2n.pending_bytes, 0)
        self.assertIsNone(bridge._serial_io_err_last_msg)


if __name__ == "__main__":
    unittest.main()

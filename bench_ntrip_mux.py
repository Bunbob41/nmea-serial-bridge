#!/usr/bin/env python3
"""Bench NTRIP → COM mux locally (mock caster; optional com0com watch COM).

No CORS login required. Verifies HTTP handshake and RTCM chunks reach serial write path.

Examples:
  python bench_ntrip_mux.py
  python bench_ntrip_mux.py --com COM12 --seconds 5
  python bench_ntrip_mux.py --caster-host rtk2go.com --mount MP --user u --pass p
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge_core import NetMode, NmeaMode, SerialNetBridge
from ntrip_client import NtripConfig, run_ntrip_forwarder


class _BenchCaster:
    async def start(self, host: str, port: int) -> asyncio.AbstractServer:
        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            buf = bytearray()
            while b"\r\n\r\n" not in buf:
                part = await reader.read(400)
                if not part:
                    break
                buf.extend(part)
            print(f"[caster] request:\n{buf.decode('latin-1', errors='replace')[:400]}")
            writer.write(
                b"HTTP/1.0 200 OK\r\n"
                b"Content-Type: application/octet-stream\r\n"
                b"\r\n"
            )
            for i in range(20):
                # RTCM3 preamble 0xD3
                pkt = bytes([0xD3, 0x00, 0x08, i & 0xFF, 0, 0, 0, 0, 0, 0])
                writer.write(pkt)
                await writer.drain()
                await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

        return await asyncio.start_server(handle, host, port)

async def _bench_mock(*, com: str | None, seconds: float) -> int:
    host, port_s = "127.0.0.1", 0
    caster = _BenchCaster()
    server = await caster.start(host, port_s)
    bound = server.sockets[0].getsockname()
    port = int(bound[1])
    print(f"[bench] mock caster on {host}:{port}")

    loop = asyncio.get_running_loop()
    bridge: SerialNetBridge | None = None
    bytes_to_com = 0

    if com:
        bridge = SerialNetBridge(
            com,
            115200,
            NetMode.UDP_LISTEN,
            udp_listen=(host, 0),
            nmea_mode=NmeaMode.RAW,
            loop=loop,
            ui_log=lambda m: print(f"[bridge] {m}"),
        )
        if not await bridge.start():
            print(f"[bench] could not open {com} — use com0com pair or omit --com")
            server.close()
            await server.wait_closed()
            return 1
        print(f"[bench] bridge running on {com} (raw mode, NMEA+RTCM mux)")

    received: list[bytes] = []

    async def on_chunk(data: bytes) -> None:
        received.append(data)
        nonlocal bytes_to_com
        if bridge is not None:
            await bridge.inject_correction_bytes(data)
            bytes_to_com += len(data)

    running = True
    cfg = NtripConfig(host, port, "MOCK")
    fwd = asyncio.create_task(
        run_ntrip_forwarder(
            cfg,
            on_chunk,
            lambda m: print(m),
            lambda: running,
            reconnect_s=0.5,
        )
    )
    await asyncio.sleep(seconds)
    running = False
    fwd.cancel()
    try:
        await fwd
    except asyncio.CancelledError:
        pass
    if bridge is not None:
        await bridge.stop()
    server.close()
    await server.wait_closed()
    total = sum(len(c) for c in received)
    print(f"[bench] NTRIP chunks={len(received)} bytes={total} written_to_com={bytes_to_com}")
    if total < 10:
        print("[bench] FAIL — expected RTCM-like stream from mock caster")
        return 1
    print("[bench] OK — mux path delivered bytes (open watch COM in terminal to eyeball binary)")
    return 0


async def _bench_live(cfg: NtripConfig, *, com: str | None, seconds: float) -> int:
    print(f"[bench] live caster {cfg.host}:{cfg.port} mount {cfg.mountpoint}")
    loop = asyncio.get_running_loop()
    bridge: SerialNetBridge | None = None
    if com:
        bridge = SerialNetBridge(
            com,
            115200,
            NetMode.UDP_LISTEN,
            udp_listen=("127.0.0.1", 0),
            nmea_mode=NmeaMode.RAW,
            loop=loop,
        )
        if not await bridge.start():
            return 1
    received = 0
    running = True

    async def on_chunk(data: bytes) -> None:
        nonlocal received
        received += len(data)
        if bridge is not None:
            await bridge.inject_correction_bytes(data)

    fwd = asyncio.create_task(
        run_ntrip_forwarder(
            cfg,
            on_chunk,
            print,
            lambda: running,
        )
    )
    await asyncio.sleep(seconds)
    running = False
    fwd.cancel()
    try:
        await fwd
    except asyncio.CancelledError:
        pass
    if bridge is not None:
        await bridge.stop()
    print(f"[bench] live bytes={received}")
    return 0 if received else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Bench NTRIP correction mux (mock or live caster)")
    p.add_argument("--com", help="Optional COM to write muxed RTCM (e.g. com0com watch leg)")
    p.add_argument("--seconds", type=float, default=3.0)
    p.add_argument("--caster-host", help="Live caster host (omit for built-in mock)")
    p.add_argument("--port", type=int, default=2101)
    p.add_argument("--mount", default="")
    p.add_argument("--user", default="")
    p.add_argument("--pass", dest="password", default="")
    args = p.parse_args()
    if args.caster_host:
        cfg = NtripConfig(
            args.caster_host.strip(),
            int(args.port),
            args.mount.strip(),
            username=args.user,
            password=args.password,
        )
        if not cfg.enabled:
            print("Need --mount for live caster")
            return 2
        return asyncio.run(_bench_live(cfg, com=args.com, seconds=args.seconds))
    return asyncio.run(_bench_mock(com=args.com, seconds=args.seconds))


if __name__ == "__main__":
    raise SystemExit(main())

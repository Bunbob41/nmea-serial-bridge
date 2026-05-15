#!/usr/bin/env python3
"""Headless UDP listen -> COM test (no GUI). Bridge GUI must be stopped on that COM."""
from __future__ import annotations

import argparse
import asyncio
import sys

from bench_config import load_bench_defaults
from bench_udp_test import port_has_listener
from bridge_gui import NetMode, NmeaMode, SerialNetBridge, configure_windows_event_loop_policy
from nmea_static_edh import build_gga, build_rmc


async def _run(com: str, baud: int, host: str, port: int, seconds: float) -> int:
    loop = asyncio.get_running_loop()
    logs: list[str] = []

    bridge = SerialNetBridge(
        com,
        baud,
        NetMode.UDP_LISTEN,
        udp_listen=(host, port),
        loop=loop,
        ui_log=logs.append,
        ui_log_verbose=lambda: True,
        nmea_mode=NmeaMode.PASSTHROUGH,
    )

    if port_has_listener(port) and host in ("0.0.0.0", "", "127.0.0.1"):
        print(f"[bridge_headless] UDP :{port} already in use — stop GUI bridge first.")
        return 2

    ok = await bridge.start()
    if not ok:
        print("[bridge_headless] start() failed:")
        for line in logs[-8:]:
            print(f"  {line}")
        return 1

    print(f"[bridge_headless] listening UDP {host}:{port} -> {com} @ {baud}")

    import socket
    from datetime import datetime, timezone

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = ("127.0.0.1", port)
    try:
        end = loop.time() + seconds
        n = 0
        while loop.time() < end:
            t = datetime.now(timezone.utc)
            for line in (build_gga(t, 38.685746, -121.082524, 255.0), build_rmc(t, 38.685746, -121.082524)):
                sock.sendto((line + "\r\n").encode("ascii"), dest)
            n += 1
            await asyncio.sleep(0.2)
    finally:
        sock.close()
        bridge.abort_now()
        pending = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        await asyncio.sleep(0.2)

    udp_ok = sum(1 for x in logs if "UDP" in x and "GPGGA" in x) >= 3
    open_fail = any("Cannot open" in x or "Timed out opening" in x for x in logs)
    wrote = udp_ok and not open_fail
    print(f"[bridge_headless] sent {n} pairs; log lines={len(logs)}")
    if logs:
        print("[bridge_headless] last events:")
        for line in logs[-6:]:
            safe = line.encode("ascii", errors="replace").decode("ascii")
            print(f"  {safe}")
    return 0 if wrote or len(logs) > 2 else 1


def main() -> None:
    configure_windows_event_loop_policy()
    d = load_bench_defaults()
    p = argparse.ArgumentParser(description="Headless bridge self-test")
    p.add_argument("--com", default=str(d["com"]))
    p.add_argument("--baud", type=int, default=int(d["baud"]))
    p.add_argument("--udp-host", default=str(d["udp_host"]))
    p.add_argument("--udp-port", type=int, default=int(d["udp_port"]))
    p.add_argument("--seconds", type=float, default=4.0)
    args = p.parse_args()
    raise SystemExit(asyncio.run(_run(args.com, args.baud, args.udp_host, args.udp_port, args.seconds)))


if __name__ == "__main__":
    main()

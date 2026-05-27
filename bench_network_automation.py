#!/usr/bin/env python3
"""Automated P0 network bench (no GUI).

Modes:
  auto (default) — headless UDP+TCP checks when the bench UDP port is free;
                   otherwise live listener + UDP burst (bridge GUI may be Running).
  headless       — requires free bench UDP port + COM (com0com); asserts zero net→serial drops.
  live           — requires bridge listening on bench UDP; sends a short burst (no drop counters).

See docs/OPERATOR_GUIDE.md §6.4 and verify_all.py (always runs this step).
"""
from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import time
from datetime import datetime, timezone
from typing import Literal

from bench_config import desk_udp_send_host, load_bench_defaults
from bench_tcp_test import port_has_tcp_listener
from bench_udp_test import port_has_listener
from bridge_core import NetMode, SerialNetBridge, configure_windows_event_loop_policy
from nmea_codec import NmeaMode
from nmea_static_sample import SAMPLE_ALT_M, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, build_gga, build_rmc

# Ephemeral TCP server port for headless reconnect check (not the Connect default 4001).
_HEADLESS_TCP_PORT = 41099


def resolve_mode(
    requested: str,
    udp_port: int,
) -> Literal["headless", "live"]:
    """Pick headless vs live when mode is auto."""
    if requested in ("headless", "live"):
        return requested  # type: ignore[return-value]
    return "live" if port_has_listener(udp_port) else "headless"


def _udp_burst(
    dest_host: str,
    dest_port: int,
    *,
    seconds: float,
    hz: float,
) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interval = 1.0 / hz if hz > 0 else 0.2
    end = time.monotonic() + max(0.05, seconds)
    n = 0
    try:
        while time.monotonic() < end:
            t = datetime.now(timezone.utc)
            for line in (
                build_gga(t, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, SAMPLE_ALT_M),
                build_rmc(t, SAMPLE_LAT_DEG, SAMPLE_LON_DEG),
            ):
                sock.sendto((line + "\r\n").encode("ascii"), (dest_host, dest_port))
            n += 1
            time.sleep(max(0, interval - 0.01))
    finally:
        sock.close()
    return n


def _tcp_send_once(host: str, port: int) -> None:
    t = datetime.now(timezone.utc)
    payload = (build_gga(t, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, SAMPLE_ALT_M) + "\r\n").encode("ascii")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3.0)
    try:
        s.connect((host, port))
        s.sendall(payload)
    finally:
        try:
            s.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        s.close()


async def _teardown_bridge(bridge: SerialNetBridge) -> None:
    bridge.abort_now()
    loop = asyncio.get_running_loop()
    pending = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    for t in pending:
        t.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    await asyncio.sleep(0.15)


async def _headless_udp_ingest(
    com: str,
    baud: int,
    udp_host: str,
    udp_port: int,
    *,
    seconds: float,
    hz: float,
    min_lines: int,
) -> tuple[bool, str]:
    if port_has_listener(udp_port) and udp_host in ("0.0.0.0", "", "127.0.0.1"):
        return False, f"UDP :{udp_port} already in use — stop GUI bridge or use --mode live"

    loop = asyncio.get_running_loop()
    logs: list[str] = []
    bridge = SerialNetBridge(
        com,
        baud,
        NetMode.UDP_LISTEN,
        udp_listen=(udp_host, udp_port),
        loop=loop,
        ui_log=logs.append,
        ui_log_verbose=lambda: False,
        nmea_mode=NmeaMode.PASSTHROUGH,
    )
    ok = await bridge.start()
    if not ok:
        tail = "; ".join(logs[-4:]) if logs else "start() returned False"
        return False, f"bridge start failed ({tail})"

    dest_host = desk_udp_send_host({"udp_host": udp_host, "udp_port": udp_port})
    drops0 = bridge.drops_net_to_serial
    lines0 = bridge.lines_remote_to_serial
    try:
        pairs = _udp_burst(dest_host, udp_port, seconds=seconds, hz=hz)
        await asyncio.sleep(0.35)
    finally:
        await _teardown_bridge(bridge)

    drops = bridge.drops_net_to_serial - drops0
    lines = bridge.lines_remote_to_serial - lines0
    if drops > 0:
        return False, f"net→serial drops={drops} (sent {pairs} tick pairs)"
    if lines < min_lines:
        return False, f"only {lines} lines accepted (need >={min_lines}); check COM {com}"
    return True, f"zero drops; {lines} lines from {pairs} tick pairs"


async def _headless_tcp_reconnect(
    com: str,
    baud: int,
    tcp_port: int,
) -> tuple[bool, str]:
    host = "127.0.0.1"
    if port_has_tcp_listener(host, tcp_port):
        return False, f"TCP :{tcp_port} already in use"

    loop = asyncio.get_running_loop()
    logs: list[str] = []
    bridge = SerialNetBridge(
        com,
        baud,
        NetMode.TCP_SERVER,
        tcp_bind_host="0.0.0.0",
        tcp_bind_port=tcp_port,
        loop=loop,
        ui_log=logs.append,
        ui_log_verbose=lambda: False,
        nmea_mode=NmeaMode.PASSTHROUGH,
    )
    ok = await bridge.start()
    if not ok:
        tail = "; ".join(logs[-4:]) if logs else "start() returned False"
        return False, f"TCP server start failed ({tail})"

    try:
        await asyncio.sleep(0.25)
        await asyncio.to_thread(_tcp_send_once, host, tcp_port)
        await asyncio.sleep(0.45)
        await asyncio.to_thread(_tcp_send_once, host, tcp_port)
        await asyncio.sleep(0.2)
    except OSError as exc:
        return False, f"TCP client failed: {exc}"
    finally:
        await _teardown_bridge(bridge)

    return True, "two TCP client sessions completed"


def _live_udp_burst(udp_port: int, dest_host: str, *, seconds: float, hz: float) -> tuple[bool, str]:
    if not port_has_listener(udp_port):
        return (
            False,
            f"nothing listening on UDP :{udp_port} — Start bridge (UDP listen) then retry",
        )
    pairs = _udp_burst(dest_host, udp_port, seconds=seconds, hz=hz)
    return (
        True,
        f"listener OK; sent {pairs} tick pairs to {dest_host}:{udp_port} "
        "(watch status bar / live log for drops)",
    )


async def _run_headless(
    com: str,
    baud: int,
    udp_host: str,
    udp_port: int,
    *,
    udp_seconds: float,
    udp_hz: float,
    tcp_port: int,
    skip_tcp: bool,
) -> int:
    steps: list[tuple[str, tuple[bool, str]]] = []
    ok_udp, msg_udp = await _headless_udp_ingest(
        com,
        baud,
        udp_host,
        udp_port,
        seconds=udp_seconds,
        hz=udp_hz,
        min_lines=4,
    )
    steps.append(("UDP ingest (zero drops)", (ok_udp, msg_udp)))

    if not skip_tcp:
        ok_tcp, msg_tcp = await _headless_tcp_reconnect(com, baud, tcp_port)
        steps.append((f"TCP server reconnect (:{tcp_port})", (ok_tcp, msg_tcp)))

    fails = 0
    for i, (title, (ok, detail)) in enumerate(steps, 1):
        tag = "PASS" if ok else "FAIL"
        print(f"[bench_network] {i}/{len(steps)} {title}: {tag} — {detail}")
        if not ok:
            fails += 1

    if fails:
        print(f"[bench_network] FAILED ({fails} step(s))")
        return 1
    print("[bench_network] OK (headless)")
    return 0


def _run_live(udp_port: int, dest_host: str, *, seconds: float, hz: float) -> int:
    ok, detail = _live_udp_burst(udp_port, dest_host, seconds=seconds, hz=hz)
    tag = "PASS" if ok else "FAIL"
    print(f"[bench_network] live UDP burst: {tag} — {detail}")
    if not ok:
        print("[bench_network] FAILED (live)")
        return 1
    print("[bench_network] OK (live — drop counters require running bridge UI/API)")
    return 0


def main(argv: list[str] | None = None) -> int:
    d = load_bench_defaults()
    p = argparse.ArgumentParser(description="P0 network automation (UDP + optional TCP)")
    p.add_argument(
        "--mode",
        choices=("auto", "headless", "live"),
        default="auto",
        help="auto: headless when UDP port free, else live burst",
    )
    p.add_argument("--com", default=str(d["com"]))
    p.add_argument("--baud", type=int, default=int(d["baud"]))
    p.add_argument("--udp-host", default=str(d["udp_host"]))
    p.add_argument("--udp-port", type=int, default=int(d["udp_port"]))
    p.add_argument("--udp-seconds", type=float, default=1.5, help="Burst duration (headless/live)")
    p.add_argument("--udp-hz", type=float, default=8.0, help="Burst rate")
    p.add_argument("--tcp-port", type=int, default=_HEADLESS_TCP_PORT, help="Headless TCP server port")
    p.add_argument("--skip-tcp", action="store_true", help="Headless: skip TCP reconnect step")
    args = p.parse_args(argv)

    mode = resolve_mode(args.mode, args.udp_port)
    dest_host = desk_udp_send_host(d)
    print(
        f"[bench_network] mode={mode} (requested={args.mode}) "
        f"UDP {args.udp_host}:{args.udp_port} dest={dest_host}:{args.udp_port}"
    )
    if mode == "headless":
        print(f"[bench_network] COM {args.com} @ {args.baud}")
        configure_windows_event_loop_policy()
        return asyncio.run(
            _run_headless(
                args.com,
                args.baud,
                args.udp_host,
                args.udp_port,
                udp_seconds=args.udp_seconds,
                udp_hz=args.udp_hz,
                tcp_port=args.tcp_port,
                skip_tcp=args.skip_tcp,
            )
        )
    return _run_live(args.udp_port, dest_host, seconds=args.udp_seconds, hz=args.udp_hz)


if __name__ == "__main__":
    raise SystemExit(main())

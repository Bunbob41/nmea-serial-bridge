#!/usr/bin/env python3
"""Automated UDP fan-out bench (no GUI, no HUD).

Headless (bench UDP port free):
  1. Fan-out ON — two registered peers both receive COM→net inject.
  2. Fan-out OFF — only the last registered peer receives.

Live (bridge already listening):
  Registers two peers and listens briefly; PASS if both receive serial→net traffic
  (com0com echo / field serial) or with --live-min-recv 0 when only registration is checked.

See docs/OPERATOR_GUIDE.md §5.5 and verify_all.py.
"""
from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import time
from typing import Literal

from bench_config import desk_udp_send_host, load_bench_defaults
from bench_udp_test import port_has_listener
from bridge_core import NetMode, SerialNetBridge, configure_windows_event_loop_policy
from nmea_codec import NmeaMode

_REGISTER_PING = b"$GPRMC,000000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,010100,,,A*67\r\n"
_INJECT_LINE = b"$GPGGA,3841.1448,N,12104.9514,W,1,08,1.0,10.0,M,0.0,M,,*6D\r\n"


def resolve_mode(requested: str, udp_port: int) -> Literal["headless", "live"]:
    if requested in ("headless", "live"):
        return requested  # type: ignore[return-value]
    return "live" if port_has_listener(udp_port) else "headless"


class _FanoutPeer:
    """One bound UDP socket — register and receive on the same local port."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.sock.settimeout(0.2)
        self.addr = self.sock.getsockname()

    def register(self, bridge_host: str, bridge_port: int) -> None:
        self.sock.sendto(_REGISTER_PING, (bridge_host, bridge_port))

    def drain(self, seconds: float) -> int:
        deadline = time.monotonic() + max(0.05, seconds)
        count = 0
        while time.monotonic() < deadline:
            try:
                self.sock.recvfrom(4096)
                count += 1
            except TimeoutError:
                continue
        return count

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


async def _teardown_bridge(bridge: SerialNetBridge) -> None:
    bridge.abort_now()
    loop = asyncio.get_running_loop()
    pending = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    for t in pending:
        t.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    await asyncio.sleep(0.15)


async def _headless_fanout_case(
    com: str,
    baud: int,
    udp_host: str,
    udp_port: int,
    *,
    udp_fanout: bool,
    dest_host: str,
) -> tuple[bool, str]:
    if port_has_listener(udp_port) and udp_host in ("0.0.0.0", "", "127.0.0.1"):
        return False, f"UDP :{udp_port} in use — stop GUI bridge or use --mode live"

    loop = asyncio.get_running_loop()
    logs: list[str] = []
    bridge = SerialNetBridge(
        com,
        baud,
        NetMode.UDP_LISTEN,
        udp_listen=(udp_host, udp_port),
        udp_fanout=udp_fanout,
        loop=loop,
        ui_log=logs.append,
        ui_log_verbose=lambda: False,
        nmea_mode=NmeaMode.PASSTHROUGH,
    )
    peer_a = _FanoutPeer("A")
    peer_b = _FanoutPeer("B")
    try:
        ok = await bridge.start()
        if not ok:
            tail = "; ".join(logs[-4:]) if logs else "start() returned False"
            return False, f"bridge start failed ({tail})"

        await asyncio.sleep(0.2)
        peer_a.register(dest_host, udp_port)
        await asyncio.sleep(0.05)
        peer_b.register(dest_host, udp_port)
        await asyncio.sleep(0.15)

        if bridge.udp_peer_count < 2:
            return False, f"expected 2 peers, got {bridge.udp_peer_count}"

        bridge.schedule_serial_to_net(_INJECT_LINE, tag="BENCH→NET")
        await asyncio.sleep(0.55)

        recv_a = await asyncio.to_thread(peer_a.drain, 0.8)
        recv_b = await asyncio.to_thread(peer_b.drain, 0.8)

        if udp_fanout:
            if recv_a >= 1 and recv_b >= 1:
                return True, f"both peers received (A={recv_a}, B={recv_b})"
            return False, f"fan-out ON but A={recv_a} B={recv_b} datagrams (need >=1 each)"

        if recv_b >= 1 and recv_a == 0:
            return True, f"last peer only (A=0, B={recv_b})"
        return False, f"fan-out OFF expected B>=1 and A=0; got A={recv_a} B={recv_b}"
    finally:
        peer_a.close()
        peer_b.close()
        await _teardown_bridge(bridge)


async def _run_headless(
    com: str,
    baud: int,
    udp_host: str,
    udp_port: int,
    *,
    dest_host: str,
    skip_single_link: bool,
) -> int:
    steps: list[tuple[str, tuple[bool, str]]] = []
    ok_on, msg_on = await _headless_fanout_case(
        com, baud, udp_host, udp_port, udp_fanout=True, dest_host=dest_host
    )
    steps.append(("Fan-out ON (2 peers receive)", (ok_on, msg_on)))

    if not skip_single_link:
        ok_off, msg_off = await _headless_fanout_case(
            com, baud, udp_host, udp_port, udp_fanout=False, dest_host=dest_host
        )
        steps.append(("Fan-out OFF (last peer only)", (ok_off, msg_off)))

    fails = 0
    for i, (title, (ok, detail)) in enumerate(steps, 1):
        tag = "PASS" if ok else "FAIL"
        print(f"[bench_fanout] {i}/{len(steps)} {title}: {tag} — {detail}")
        if not ok:
            fails += 1

    if fails:
        print(f"[bench_fanout] FAILED ({fails} step(s))")
        return 1
    print("[bench_fanout] OK (headless)")
    return 0


def _run_live(
    udp_port: int,
    dest_host: str,
    *,
    listen_seconds: float,
    min_recv: int,
) -> int:
    if not port_has_listener(udp_port):
        print(
            f"[bench_fanout] FAIL — nothing listening on UDP :{udp_port}\n"
            "  Start bridge with Fan-out checked, then retry.",
            file=sys.stderr,
        )
        return 1

    peer_a = _FanoutPeer("A")
    peer_b = _FanoutPeer("B")
    try:
        peer_a.register(dest_host, udp_port)
        time.sleep(0.05)
        peer_b.register(dest_host, udp_port)
        print(
            f"[bench_fanout] live: registered peers "
            f"A={peer_a.addr[1]} B={peer_b.addr[1]} -> {dest_host}:{udp_port}"
        )
        if min_recv <= 0:
            print("[bench_fanout] OK (live - peers registered; COM->net not required)")
            return 0

        print(
            f"[bench_fanout] listening {listen_seconds:.0f}s - "
            "generate COM->net (paired com0com echo or serial into bridge COM)..."
        )
        recv_a = peer_a.drain(listen_seconds)
        recv_b = peer_b.drain(listen_seconds)
    finally:
        peer_a.close()
        peer_b.close()

    if recv_a >= min_recv and recv_b >= min_recv:
        print(f"[bench_fanout] OK (live - A={recv_a} B={recv_b} datagrams)")
        return 0

    print(
        f"[bench_fanout] FAIL (live) - A={recv_a} B={recv_b} "
        f"(need >={min_recv} each). Enable Fan-out and pulse COM->net.",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    d = load_bench_defaults()
    p = argparse.ArgumentParser(description="UDP fan-out automation (two peers)")
    p.add_argument(
        "--mode",
        choices=("auto", "headless", "live"),
        default="auto",
        help="auto: headless when UDP port free, else live",
    )
    p.add_argument("--com", default=str(d["com"]))
    p.add_argument("--baud", type=int, default=int(d["baud"]))
    p.add_argument("--udp-host", default=str(d["udp_host"]))
    p.add_argument("--udp-port", type=int, default=int(d["udp_port"]))
    p.add_argument(
        "--skip-single-link",
        action="store_true",
        help="Headless: skip fan-out OFF (last-peer-only) check",
    )
    p.add_argument(
        "--live-listen",
        type=float,
        default=6.0,
        help="Live: seconds to listen per peer after registration",
    )
    p.add_argument(
        "--live-min-recv",
        type=int,
        default=1,
        help="Live: min datagrams per peer (0 = registration only)",
    )
    args = p.parse_args(argv)

    mode = resolve_mode(args.mode, args.udp_port)
    dest_host = desk_udp_send_host(d)
    print(
        f"[bench_fanout] mode={mode} (requested={args.mode}) "
        f"dest={dest_host}:{args.udp_port}"
    )

    if mode == "headless":
        print(f"[bench_fanout] COM {args.com} @ {args.baud}")
        configure_windows_event_loop_policy()
        return asyncio.run(
            _run_headless(
                args.com,
                args.baud,
                args.udp_host,
                args.udp_port,
                dest_host=dest_host,
                skip_single_link=args.skip_single_link,
            )
        )

    return _run_live(
        args.udp_port,
        dest_host,
        listen_seconds=args.live_listen,
        min_recv=args.live_min_recv,
    )


if __name__ == "__main__":
    raise SystemExit(main())

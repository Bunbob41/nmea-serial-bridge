#!/usr/bin/env python3
"""UDP fan-out bench helper: register as a peer and listen for serial→net replies.

Use with ONE bridge instance (UDP listen). Run a second copy or bench_udp_test.py in
another terminal to register another peer. Generate COM→net traffic via com0com echo
or live serial input.

Example:
  python bench_fanout_probe.py --seconds 15
  python bench_fanout_probe.py --register-only
"""
from __future__ import annotations

import argparse
import socket
import sys
import time

from bench_config import desk_udp_send_host, load_bench_defaults

_d = load_bench_defaults()
DEFAULT_HOST = desk_udp_send_host(_d)
DEFAULT_PORT = int(_d["udp_port"])


def main() -> None:
    p = argparse.ArgumentParser(description="Register UDP peer and listen for fan-out replies.")
    p.add_argument("--host", default=DEFAULT_HOST, help="Bridge listen address to send to")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bridge UDP listen port")
    p.add_argument("--seconds", type=float, default=15.0, help="Listen duration (0 = register only)")
    p.add_argument("--register-only", action="store_true", help="Send one datagram and exit")
    args = p.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 0))
    local = sock.getsockname()
    sock.settimeout(0.5)

    ping = b"$GPRMC,000000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,010100,,,A*67\r\n"
    sock.sendto(ping, (args.host, args.port))
    print(f"Registered peer via sendto {args.host}:{args.port} (local {local[0]}:{local[1]})")

    if args.register_only or args.seconds <= 0:
        return

    deadline = time.monotonic() + args.seconds
    count = 0
    print(f"Listening {args.seconds:.0f}s for serial->net fan-out datagrams…")
    while time.monotonic() < deadline:
        try:
            data, src = sock.recvfrom(4096)
        except TimeoutError:
            continue
        count += 1
        if count <= 3 or count % 50 == 0:
            print(f"  recv #{count} {len(data)} B from {src}")
    print(f"Done: {count} datagram(s) received on {local[1]}")
    if count == 0:
        print(
            "No replies — ensure bridge is Running, fan-out enabled, and COM→net traffic exists.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

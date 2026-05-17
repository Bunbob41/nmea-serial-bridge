#!/usr/bin/env python3
"""Send test NMEA to the bridge on UDP 10110. Run AFTER bridge is Started."""
from __future__ import annotations

import argparse
import socket
import sys
import time
from datetime import datetime, timezone

from bench_config import desk_udp_send_host, load_bench_defaults
from nmea_static_sample import SAMPLE_ALT_M, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, build_gga, build_rmc

_d = load_bench_defaults()
DEFAULT_HOST = desk_udp_send_host(_d)
DEFAULT_PORT = int(_d["udp_port"])


def port_has_listener(port: int) -> bool:
    """If we cannot bind, something is already listening (usually the bridge)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(("0.0.0.0", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def main() -> None:
    p = argparse.ArgumentParser(
        description=f"UDP bench test: needs bridge listening on UDP :{DEFAULT_PORT} first."
    )
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--seconds", type=float, default=10.0, help="How long to send (0 = one burst)")
    p.add_argument("--hz", type=float, default=5.0)
    args = p.parse_args()

    dest = (args.host, args.port)
    print(f"[bench_udp_test] Target: {args.host}:{args.port}")

    if not port_has_listener(args.port):
        print(
            f"[bench_udp_test] ERROR: Nothing is LISTENING on UDP port {args.port}.\n"
            "  The bridge must be running first:\n"
            "    1) Open NMEA Serial Bridge (desktop shortcut)\n"
            "    2) Apply bench preset -> Start bridge\n"
            f"    3) Log must say: UDP listen on ('0.0.0.0', {args.port})\n"
            "    4) Run this script again\n"
            "  Or run:  python check_setup.py"
        )
        sys.exit(1)

    print(f"[bench_udp_test] OK: port {args.port} is in use (bridge should be listening).")
    print(
        f"[bench_udp_test] Watch the paired com0com port (bridge uses {load_bench_defaults()['com']}) "
        "and the bridge live log."
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interval = 1.0 / args.hz if args.hz > 0 else 0
    end = time.time() + args.seconds if args.seconds > 0 else time.time()
    n = 0
    try:
        while True:
            t = datetime.now(timezone.utc)
            for line in (
                build_gga(t, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, SAMPLE_ALT_M),
                build_rmc(t, SAMPLE_LAT_DEG, SAMPLE_LON_DEG),
            ):
                sock.sendto((line + "\r\n").encode("ascii"), dest)
            n += 1
            if args.seconds <= 0:
                break
            if time.time() >= end:
                break
            time.sleep(max(0, interval - 0.01))
    except KeyboardInterrupt:
        print("\n[bench_udp_test] Stopped.")
    finally:
        sock.close()
    print(f"[bench_udp_test] Sent {n} GGA+RMC pairs to {args.host}:{args.port}.")


if __name__ == "__main__":
    main()

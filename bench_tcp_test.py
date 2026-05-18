#!/usr/bin/env python3
"""Send test NMEA to a bridge running in TCP server mode. Run AFTER bridge is Started."""
from __future__ import annotations

import argparse
import socket
import sys
import time
from datetime import datetime, timezone

from nmea_static_sample import SAMPLE_ALT_M, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, build_gga, build_rmc

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4001


def port_has_tcp_listener(host: str, port: int) -> bool:
    """Return True if something accepts TCP connections on host:port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.4)
    try:
        s.connect((host, port))
        s.close()
        return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


def main() -> int:
    p = argparse.ArgumentParser(
        description="TCP bench test: bridge must be Started in TCP server mode first."
    )
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--seconds", type=float, default=5.0, help="How long to send (0 = one burst)")
    p.add_argument("--hz", type=float, default=2.0)
    args = p.parse_args()

    print(f"[bench_tcp_test] Target: {args.host}:{args.port}")

    if not port_has_tcp_listener(args.host, args.port):
        print(
            f"[bench_tcp_test] ERROR: Nothing accepted TCP on {args.host}:{args.port}.\n"
            "  1) Open NMEA Serial Bridge\n"
            "  2) Tools/Net → Advanced → TCP server (e.g. 0.0.0.0:4001)\n"
            "  3) Desk test or Boat, then Start bridge\n"
            "  4) Log should say: TCP server listening …\n"
            "  5) Run this script again"
        )
        return 1

    print(f"[bench_tcp_test] OK: TCP connect to {args.host}:{args.port} succeeded.")
    print("[bench_tcp_test] Watch bridge log for TCP← lines and COM traffic.")

    interval = 1.0 / args.hz if args.hz > 0 else 0
    end = time.time() + args.seconds if args.seconds > 0 else time.time()
    n = 0
    try:
        sock = socket.create_connection((args.host, args.port), timeout=5.0)
        sock.settimeout(2.0)
        while True:
            t = datetime.now(timezone.utc)
            for line in (
                build_gga(t, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, SAMPLE_ALT_M),
                build_rmc(t, SAMPLE_LAT_DEG, SAMPLE_LON_DEG),
            ):
                sock.sendall((line + "\r\n").encode("ascii"))
            n += 1
            if args.seconds <= 0:
                break
            if time.time() >= end:
                break
            time.sleep(max(0, interval - 0.01))
    except KeyboardInterrupt:
        print("\n[bench_tcp_test] Stopped.")
    except OSError as e:
        print(f"[bench_tcp_test] ERROR: {e}")
        return 1
    finally:
        try:
            sock.close()
        except Exception:
            pass
    print(f"[bench_tcp_test] Sent {n} GGA+RMC pairs over TCP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

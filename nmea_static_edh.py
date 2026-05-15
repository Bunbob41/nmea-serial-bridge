#!/usr/bin/env python3
"""Static El Dorado Hills, CA fix — GGA + RMC at 5 Hz over UDP to the bridge."""
from __future__ import annotations

import argparse
import socket
import time
from datetime import datetime, timezone

from nmea_codec import nmea_checksum_ok

# Town Center area, El Dorado Hills, CA (WGS84)
EDH_LAT_DEG = 38.685746
EDH_LON_DEG = -121.082524
EDH_ALT_M = 255.0  # ~837 ft, typical bench elevation


def nmea_checksum(body: str) -> str:
    """body: talker + fields, no leading $ or *checksum."""
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"${body}*{cs:02X}"


def deg_to_nmea_lat(deg: float) -> tuple[str, str]:
    hemi = "N" if deg >= 0 else "S"
    x = abs(deg)
    d = int(x)
    m = (x - d) * 60.0
    return f"{d:02d}{m:07.4f}", hemi


def deg_to_nmea_lon(deg: float) -> tuple[str, str]:
    hemi = "E" if deg >= 0 else "W"
    x = abs(deg)
    d = int(x)
    m = (x - d) * 60.0
    return f"{d:03d}{m:07.4f}", hemi


def build_gga(when: datetime, lat: float, lon: float, alt_m: float) -> str:
    t = when.strftime("%H%M%S.") + f"{when.microsecond // 10000:02d}"
    lat_f, lat_h = deg_to_nmea_lat(lat)
    lon_f, lon_h = deg_to_nmea_lon(lon)
    body = (
        f"GPGGA,{t},{lat_f},{lat_h},{lon_f},{lon_h},"
        f"1,10,0.9,{alt_m:.1f},M,-25.0,M,,"
    )
    return nmea_checksum(body)


def build_rmc(when: datetime, lat: float, lon: float) -> str:
    t = when.strftime("%H%M%S.") + f"{when.microsecond // 10000:02d}"
    d = when.strftime("%d%m%y")
    lat_f, lat_h = deg_to_nmea_lat(lat)
    lon_f, lon_h = deg_to_nmea_lon(lon)
    # Static: valid fix, zero speed, arbitrary north-heading course
    body = (
        f"GPRMC,{t},A,{lat_f},{lat_h},{lon_f},{lon_h},"
        f"0.0,0.0,{d},2.5,W"
    )
    return nmea_checksum(body)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Send static El Dorado Hills GGA+RMC at 5 Hz to the bridge (UDP)."
    )
    p.add_argument("--dest-host", default="127.0.0.1", help="Bridge UDP host")
    p.add_argument("--dest-port", type=int, default=10110, help="Bridge UDP port")
    p.add_argument("--rate-hz", type=float, default=5.0, help="Updates per second (GGA+RMC each tick)")
    p.add_argument("--duration", type=float, default=0.0, help="Seconds (0 = run until Ctrl+C)")
    p.add_argument("--lat", type=float, default=EDH_LAT_DEG, help="WGS84 latitude (degrees)")
    p.add_argument("--lon", type=float, default=EDH_LON_DEG, help="WGS84 longitude (degrees)")
    p.add_argument("--alt-m", type=float, default=EDH_ALT_M, help="Altitude meters")
    p.add_argument("--listen-port", type=int, default=0, help="Local UDP bind (0 = random)")
    p.add_argument("--quiet", action="store_true", help="Do not print each sentence")
    args = p.parse_args()

    gga = build_gga(datetime.now(timezone.utc), args.lat, args.lon, args.alt_m)
    rmc = build_rmc(datetime.now(timezone.utc), args.lat, args.lon)
    if not nmea_checksum_ok(gga) or not nmea_checksum_ok(rmc):
        raise SystemExit("internal error: built invalid NMEA checksum")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.listen_port))
    dest = (args.dest_host, args.dest_port)
    interval = 1.0 / args.rate_hz if args.rate_hz > 0 else 0.2
    end = time.time() + args.duration if args.duration > 0 else None

    print(
        f"[nmea_static_edh] {args.lat:.6f}, {args.lon:.6f} @ {args.alt_m:.1f} m "
        f"-> UDP {args.dest_host}:{args.dest_port} @ {args.rate_hz} Hz (GGA+RMC)"
    )
    print(f"[nmea_static_edh] Example GGA: {gga}")
    print(f"[nmea_static_edh] Example RMC: {rmc}")

    n = 0
    try:
        while end is None or time.time() < end:
            tick_start = time.perf_counter()
            when = datetime.now(timezone.utc)
            for line in (build_gga(when, args.lat, args.lon, args.alt_m), build_rmc(when, args.lat, args.lon)):
                sock.sendto((line + "\r\n").encode("ascii"), dest)
                if not args.quiet:
                    print(f"[nmea_static_edh] TX: {line}")
            n += 1
            elapsed = time.perf_counter() - tick_start
            sleep_s = interval - elapsed
            if sleep_s > 0:
                time.sleep(sleep_s)
    except KeyboardInterrupt:
        print("[nmea_static_edh] Stopped (Ctrl+C).")
    finally:
        sock.close()
        print(f"[nmea_static_edh] Done. Sent {n} update pairs ({n * 2} sentences).")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""TCP stress client: 5 NMEA sentences @ 5 Hz, LA → Sacramento @ 5 m/s, auto-reconnect.

Connect to a bridge running in **TCP server** mode. On disconnect, waits and reconnects;
each new session restarts the route at Los Angeles.
"""
from __future__ import annotations

import argparse
import math
import socket
import sys
import threading
import time
from datetime import datetime, timezone

from nmea_static_sample import build_gga, nmea_checksum

# WGS84 anchors (approx city centers)
LA_LAT, LA_LON = 34.0522, -118.2437
SAC_LAT, SAC_LON = 38.5816, -121.4944
DEFAULT_ALT_M = 25.0

MPS_TO_KNOTS = 1.943844


def _initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _advance(lat: float, lon: float, bearing_deg: float, distance_m: float) -> tuple[float, float]:
    r = 6_371_000.0
    brng = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(distance_m / r)
        + math.cos(lat1) * math.sin(distance_m / r) * math.cos(brng)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(distance_m / r) * math.cos(lat1),
        math.cos(distance_m / r) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def _time_fields(when: datetime) -> tuple[str, str]:
    t = when.strftime("%H%M%S.") + f"{when.microsecond // 10000:02d}"
    d = when.strftime("%d%m%y")
    return t, d


def _deg_lat(lat: float) -> tuple[str, str]:
    hemi = "N" if lat >= 0 else "S"
    x = abs(lat)
    d = int(x)
    m = (x - d) * 60.0
    return f"{d:02d}{m:07.4f}", hemi


def _deg_lon(lon: float) -> tuple[str, str]:
    hemi = "E" if lon >= 0 else "W"
    x = abs(lon)
    d = int(x)
    m = (x - d) * 60.0
    return f"{d:03d}{m:07.4f}", hemi


def build_vtg(when: datetime, course_deg: float, speed_mps: float) -> str:
    t = _time_fields(when)[0]
    kn = speed_mps * MPS_TO_KNOTS
    kmh = speed_mps * 3.6
    body = f"GPVTG,{course_deg:.1f},T,,M,{kn:.2f},N,{kmh:.2f},K"
    return nmea_checksum(body)


def build_gll(when: datetime, lat: float, lon: float) -> str:
    t = _time_fields(when)[0]
    lat_f, lat_h = _deg_lat(lat)
    lon_f, lon_h = _deg_lon(lon)
    body = f"GPGLL,{lat_f},{lat_h},{lon_f},{lon_h},{t},A,A"
    return nmea_checksum(body)


def build_zda(when: datetime) -> str:
    t = when.strftime("%H%M%S.") + f"{when.microsecond // 10000:02d}"
    body = (
        f"GPZDA,{t},{when.day:02d},{when.month:02d},{when.year},00,00"
    )
    return nmea_checksum(body)


def build_rmc_motion(
    when: datetime, lat: float, lon: float, *, course_deg: float, speed_mps: float
) -> str:
    t, d = _time_fields(when)
    lat_f, lat_h = _deg_lat(lat)
    lon_f, lon_h = _deg_lon(lon)
    kn = speed_mps * MPS_TO_KNOTS
    body = (
        f"GPRMC,{t},A,{lat_f},{lat_h},{lon_f},{lon_h},"
        f"{kn:.2f},{course_deg:.1f},{d},2.5,W"
    )
    return nmea_checksum(body)


def five_sentence_bundle(
    when: datetime, lat: float, lon: float, *, course_deg: float, speed_mps: float, alt_m: float
) -> list[str]:
    return [
        build_gga(when, lat, lon, alt_m),
        build_rmc_motion(when, lat, lon, course_deg=course_deg, speed_mps=speed_mps),
        build_vtg(when, course_deg, speed_mps),
        build_gll(when, lat, lon),
        build_zda(when),
    ]


# Product demo: visible chart motion in a few minutes (full Sac leg is ~32 h @ 5 m/s).
DEMO_SPEED_MPS = 100.0
DEMO_LEG_KM = 18.0
DEMO_DURATION_S = 240.0


class RouteRunner:
    """Dead-reckoning LA → Sacramento; reset to LA on session start or leg limit."""

    def __init__(self, *, speed_mps: float, arrive_m: float, leg_reset_m: float | None = None) -> None:
        self.speed_mps = speed_mps
        self.bearing = _initial_bearing_deg(LA_LAT, LA_LON, SAC_LAT, SAC_LON)
        self.arrive_m = arrive_m
        self.leg_reset_m = leg_reset_m if leg_reset_m is not None else arrive_m
        self.reset()

    def reset(self) -> None:
        self.lat = LA_LAT
        self.lon = LA_LON
        self.travel_m = 0.0

    def step(self, dt_s: float) -> tuple[float, float, float]:
        dist = self.speed_mps * dt_s
        if dist <= 0:
            return self.lat, self.lon, self.bearing
        remaining = max(0.0, self.arrive_m - self.travel_m)
        step_m = min(dist, remaining) if remaining > 0 else dist
        self.lat, self.lon = _advance(self.lat, self.lon, self.bearing, step_m)
        self.travel_m += step_m
        if self.travel_m >= self.leg_reset_m - 0.5:
            self.reset()
        return self.lat, self.lon, self.bearing


def port_has_tcp_listener(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


def _tcp_recv_drain(sock: socket.socket, stop: threading.Event, *, quiet: bool) -> None:
    """Read and discard bridge egress so tcp_writer.drain() does not back up the COM->net queue."""
    sock.settimeout(0.5)
    total = 0
    while not stop.is_set():
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            continue
        except OSError:
            break
        if not chunk:
            break
        total += len(chunk)
    if not quiet and total:
        print(f"[bench_tcp_stress] Drained {total} bytes from bridge on disconnect", flush=True)


def run_session(
    sock: socket.socket,
    route: RouteRunner,
    *,
    hz: float,
    alt_m: float,
    quiet: bool,
) -> int:
    interval = 1.0 / hz if hz > 0 else 0.2
    sent_ticks = 0
    while True:
        t0 = time.perf_counter()
        when = datetime.now(timezone.utc)
        lat, lon, cog = route.step(interval)
        lines = five_sentence_bundle(when, lat, lon, course_deg=cog, speed_mps=route.speed_mps, alt_m=alt_m)
        payload = "".join(line + "\r\n" for line in lines).encode("ascii", errors="replace")
        sock.sendall(payload)
        sent_ticks += 1
        if not quiet and sent_ticks % int(max(hz, 1)) == 0:
            print(
                f"[tcp_stress] tick={sent_ticks} {lat:.5f},{lon:.5f} "
                f"cog={cog:.1f} deg travel={route.travel_m/1000:.2f} km",
                flush=True,
            )
        elapsed = time.perf_counter() - t0
        time.sleep(max(0.0, interval - elapsed))


def main() -> int:
    p = argparse.ArgumentParser(description="TCP NMEA stress: LA→Sacramento, auto-reconnect.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=4001)
    p.add_argument("--hz", type=float, default=5.0, help="Updates per second (5 sentences each)")
    p.add_argument("--speed-mps", type=float, default=5.0, help="Ground speed along route (m/s)")
    p.add_argument("--alt-m", type=float, default=DEFAULT_ALT_M)
    p.add_argument("--reconnect-delay", type=float, default=1.0)
    p.add_argument("--connect-timeout", type=float, default=8.0)
    p.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Stop after N seconds (0 = run until Ctrl+C or parent kills process)",
    )
    p.add_argument("--quiet", action="store_true")
    p.add_argument(
        "--demo",
        action="store_true",
        help="Presenter mode: ~100 m/s, 18 km legs, 4 min auto-stop (visible map motion)",
    )
    args = p.parse_args()

    if args.demo:
        args.speed_mps = DEMO_SPEED_MPS
        if args.duration <= 0:
            args.duration = DEMO_DURATION_S

    arrive_m = _haversine_m(LA_LAT, LA_LON, SAC_LAT, SAC_LON)
    leg_reset_m = DEMO_LEG_KM * 1000.0 if args.demo else arrive_m
    route = RouteRunner(
        speed_mps=args.speed_mps,
        arrive_m=arrive_m,
        leg_reset_m=leg_reset_m,
    )
    end = time.time() + args.duration if args.duration > 0 else None

    mode = (
        f"demo {DEMO_LEG_KM:g} km legs @ {args.speed_mps:g} m/s, {args.duration:g}s"
        if args.demo
        else f"route LA->Sac ~{arrive_m/1000:.1f} km (restarts at LA each connect)"
    )
    print(
        f"[bench_tcp_stress] Target {args.host}:{args.port} | "
        f"{args.hz:g} Hz x 5 sentences | {args.speed_mps:g} m/s | {mode}",
        flush=True,
    )

    session = 0
    try:
        while end is None or time.time() < end:
            if not port_has_tcp_listener(args.host, args.port):
                print(
                    f"[bench_tcp_stress] Waiting for TCP server on {args.host}:{args.port}...",
                    flush=True,
                )
                time.sleep(args.reconnect_delay)
                continue
            try:
                sock = socket.create_connection((args.host, args.port), timeout=args.connect_timeout)
            except OSError as exc:
                print(f"[bench_tcp_stress] Connect failed: {exc}", flush=True)
                time.sleep(args.reconnect_delay)
                continue

            session += 1
            route.reset()
            print(
                f"[bench_tcp_stress] Session {session} connected — route reset to LA "
                "(RX drain on — reads COM->TCP echo so bridge queues stay healthy)",
                flush=True,
            )
            drain_stop = threading.Event()
            drain = threading.Thread(
                target=_tcp_recv_drain,
                args=(sock, drain_stop),
                kwargs={"quiet": args.quiet},
                daemon=True,
            )
            try:
                drain.start()
                run_session(sock, route, hz=args.hz, alt_m=args.alt_m, quiet=args.quiet)
            except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                print(f"[bench_tcp_stress] Disconnected: {exc}", flush=True)
            finally:
                drain_stop.set()
                drain.join(timeout=2.0)
                try:
                    sock.close()
                except OSError:
                    pass
            if end is not None and time.time() >= end:
                break
            print(f"[bench_tcp_stress] Reconnecting in {args.reconnect_delay:g}s...", flush=True)
            time.sleep(args.reconnect_delay)
    except KeyboardInterrupt:
        print("\n[bench_tcp_stress] Stopped.", flush=True)
    print(f"[bench_tcp_stress] Done ({session} session(s)).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

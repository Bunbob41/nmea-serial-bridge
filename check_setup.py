#!/usr/bin/env python3
"""Quick checks before a bridge test — COM ports, UDP port, subnet hints."""
from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys

import serial.tools.list_ports

from py_interpreter import subprocess_no_console_kwargs

_SUBPROC_KW = subprocess_no_console_kwargs()


def list_com(expected_com: str = "") -> None:
    print("COM ports visible to Python:")
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("  (none)")
        return
    want = expected_com.strip().upper()
    for p in ports:
        desc = f" - {p.description}" if p.description else ""
        mark = "  <-- saved bridge COM" if want and p.device.upper() == want else ""
        print(f"  {p.device}{desc}{mark}")


def _windows_pid_for_udp_port(port: int) -> list[int]:
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"], text=True, errors="replace", **_SUBPROC_KW
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    pids: list[int] = []
    pat = re.compile(rf"UDP\s+\S+:{port}\s+\S+\s+(\d+)\s*$")
    for line in out.splitlines():
        m = pat.search(line.strip())
        if m:
            pids.append(int(m.group(1)))
    return sorted(set(pids))


def _windows_process_name(pid: int) -> str:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            text=True,
            errors="replace",
            **_SUBPROC_KW,
        )
    except (OSError, subprocess.CalledProcessError):
        return "?"
    line = out.strip().splitlines()
    if not line or "No tasks" in line[0]:
        return "?"
    # "Image Name","PID",...
    parts = line[0].split(",")
    if parts:
        return parts[0].strip('"')
    return "?"


def check_udp_bind(port: int) -> None:
    print(f"\nUDP port {port} on this PC:")
    if sys.platform == "win32":
        owners = _windows_pid_for_udp_port(port)
        if owners:
            print(f"  IN USE — listener(s) already bound to UDP :{port}:")
            for pid in owners:
                name = _windows_process_name(pid)
                print(f"    PID {pid}: {name}")
            names = {_windows_process_name(p) for p in owners}
            if any("NMEA" in n.upper() for n in names):
                print(
                    f"\n  >>> NMEA Simulator is LISTENING on this port — that blocks the bridge.\n"
                    f"  Fix: Quit NMEA Simulator (or change it to SEND to 127.0.0.1:{port},\n"
                    f"  not Listen/Bind on {port}). Start the bridge FIRST so it owns :{port}.\n"
                    f"  Correct flow: Bridge listens :{port}  <--  NMEA Sim sends TO 127.0.0.1:{port}"
                )
            elif any("python" in n.lower() for n in names):
                print("  (Likely the bridge — OK if you already clicked Start.)")
            return

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(("0.0.0.0", port))
        print(f"  OK: port {port} is free (nothing else bound here right now).")
    except OSError as e:
        print(f"  IN USE or blocked: {e}")
        print("  Stop the other app using this port, then start the bridge.")
    finally:
        s.close()


def check_udp_send(host: str, port: int) -> None:
    print(f"\nUDP send test -> {host}:{port}:")
    msg = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)
    try:
        s.sendto(msg, (host, port))
        print("  Sent one NMEA sentence (no reply unless bridge+echo loop is up).")
    except OSError as e:
        print(f"  Send failed: {e}")
    finally:
        s.close()


def print_production_hints(pc_ip: str, port: int, ins_ip: str, com: str) -> None:
    print(
        f"""
Production / boat path (boat-style named preset or bench_defaults.json):
  1) Set survey Ethernet on this PC (static recommended): {pc_ip}/24
  2) Configure INS / sonar to SEND NMEA UDP to {pc_ip}:{port} (not "listen" on {port})
  3) Bridge: load boat preset in app -> Start -> {com} @ 115200 to target serial device
  4) Do NOT open any other serial app on {com} while the bridge is running
  5) Verify downstream position/data on the connected device/app, not laptop COM GPS
  6) INS reference IP (typical): {ins_ip}

Pre-flight on the boat PC:
  python com_free.py --com {com}
  python check_setup.py --port {port} --host {pc_ip}
"""
    )


def print_network_hints(port: int, com: str = "", send_host: str = "127.0.0.1") -> None:
    com_line = f"  - Bridge COM (bench preset): {com}" if com else "  - Pick bridge COM in the app; echo on the paired com0com port."
    print(
        f"""
Bench path (bench-style preset or bench_defaults.json):
  - UDP listen port: {port}
  - UDP send test target: {send_host}:{port}
{com_line}

Subnet / network (read this once):
  - com0com + 127.0.0.1 = SAME PC. Subnet does NOT matter.
  - Use host {send_host} and port {port} in the UDP test script (nmea_static_sample.py).
  - Remote host 192.168.x.x only matters for ANOTHER machine on your LAN.
  - In com0com Setup: confirm which two COM ports are PAIRED (not every com0com port talks to every other).

UDP + NMEA Simulator (common mistake):
  - The BRIDGE must LISTEN on UDP port {port} (bind).
  - NMEA Simulator must SEND to {send_host}:{port} — it must NOT "listen" on {port}.
  - If NMEA Simulator owns port {port}, the bridge cannot receive anything.
  - Order: (1) quit NMEA Sim  (2) bridge Start  (3) NMEA Sim UDP output -> {send_host}:{port}
"""
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Pre-flight checks for nmea-serial-bridge")
    p.add_argument("--port", type=int, default=0, help="UDP listen port (0 = load from saved preset)")
    p.add_argument("--host", default="", help="UDP target for send test (empty = preset default)")
    p.add_argument("--com", default="", help="Expected bridge COM (highlights in port list)")
    p.add_argument(
        "--production",
        action="store_true",
        help="Show boat/INS production checklist (boat-style preset or bench_defaults.json)",
    )
    args = p.parse_args()

    com = str(args.com or "").strip()
    send_host = "127.0.0.1"
    port = 10110
    if args.production:
        try:
            from bench_config import load_production_defaults

            d = load_production_defaults()
            port = int(args.port) if args.port > 0 else int(d.get("udp_port", 10110))
            send_host = str(args.host or d.get("pc_ip", "192.168.1.10")).strip() or "192.168.1.10"
            com = com or str(d.get("com", "COM3"))
            print_production_hints(
                str(d.get("pc_ip", "192.168.1.10")),
                port,
                str(d.get("ins_ip", "192.168.1.20")),
                com,
            )
        except ImportError:
            port = int(args.port) if args.port > 0 else 10110
            send_host = str(args.host or "192.168.1.10")
            com = com or "COM3"
            print_production_hints(send_host, port, "192.168.1.20", com)
    else:
        try:
            from bench_config import desk_udp_send_host, load_bench_defaults

            d = load_bench_defaults()
            port = int(args.port) if args.port > 0 else int(d.get("udp_port", 10110))
            send_host = str(args.host or "").strip() or desk_udp_send_host(d)
            com = com or str(d.get("com", ""))
            print_network_hints(port, com, send_host)
        except ImportError:
            port = int(args.port) if args.port > 0 else 10110
            send_host = str(args.host or "127.0.0.1")
            print_network_hints(port, com, send_host)

    list_com(com)
    check_udp_bind(port)
    check_udp_send(send_host, port)
    print("\nIf COM open fails in the bridge: close Tera Term / PuTTY on that port.")
    print(
        f"Bench: Presets -> load bench preset -> Start -> Tera Term on paired COM (not {com or 'bridge COM'}) -> "
        f"python nmea_static_sample.py --dest-port {port}\n"
        "Boat:  Checklists -> Boat checklist (or Diagnostics -> Boat checklist)\n"
    )


if __name__ == "__main__":
    main()

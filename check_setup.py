#!/usr/bin/env python3
"""Quick checks before a bridge test — COM ports, UDP port, subnet hints."""
from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys

import serial.tools.list_ports


def list_com() -> None:
    print("COM ports visible to Python:")
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("  (none)")
        return
    for p in ports:
        desc = f" - {p.description}" if p.description else ""
        print(f"  {p.device}{desc}")


def _windows_pid_for_udp_port(port: int) -> list[int]:
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, errors="replace")
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


def print_network_hints() -> None:
    print(
        """
Subnet / network (read this once):
  - com0com + 127.0.0.1 = SAME PC. Subnet does NOT matter.
  - Use host 127.0.0.1 or localhost and port 10110 in the UDP test script.
  - Remote host 192.168.x.x only matters for ANOTHER machine on your LAN.
  - In com0com Setup: confirm which two COM ports are PAIRED (not every com0com port talks to every other).
  - Bridge: COM7  |  Echo (serial_echo / Tera Term): COM12  - not both on COM7.

UDP + NMEA Simulator (common mistake):
  - The BRIDGE must LISTEN on UDP port 10110 (bind).
  - NMEA Simulator must SEND to 127.0.0.1:10110 — it must NOT "listen" on 10110.
  - If NMEA Simulator owns port 10110, the bridge cannot receive anything.
  - Order: (1) quit NMEA Sim  (2) bridge Start  (3) NMEA Sim UDP output -> 127.0.0.1:10110
"""
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Pre-flight checks for nmea-serial-bridge")
    p.add_argument("--port", type=int, default=10110)
    p.add_argument("--host", default="127.0.0.1", help="UDP target for send test")
    args = p.parse_args()

    print_network_hints()
    list_com()
    check_udp_bind(args.port)
    check_udp_send(args.host, args.port)
    print("\nIf COM7 open fails in the bridge: close Tera Term / PuTTY on COM7.")
    print(
        "Recommended: bridge_gui -> bench preset -> Start -> Tera Term on COM12 -> "
        "NMEA Sim UDP send to 127.0.0.1:10110 (or: python nmea_static_edh.py).\n"
    )


if __name__ == "__main__":
    main()

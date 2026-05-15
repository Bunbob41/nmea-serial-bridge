#!/usr/bin/env python3
"""Check whether a COM port can be opened and list likely Python holders."""
from __future__ import annotations

import argparse
import sys

import serial

from bench_config import load_bench_defaults


def main() -> int:
    p = argparse.ArgumentParser(description="Test COM port availability")
    p.add_argument("--com", default=None, help="Port name (default: bench_defaults.json)")
    p.add_argument("--baud", type=int, default=None)
    args = p.parse_args()
    d = load_bench_defaults()
    com = args.com or str(d["com"])
    baud = args.baud if args.baud is not None else int(d["baud"])

    print(f"[com_free] Testing {com} @ {baud} ...")
    try:
        ser = serial.Serial(com, baudrate=baud, timeout=0)
        ser.close()
        print(f"[com_free] OK: {com} is available.")
    except Exception as e:
        print(f"[com_free] BLOCKED: {com} — {e}")
        print("[com_free] Common causes:")
        print("  - Bridge GUI still running (Stop bridge, or close app)")
        print("  - Stuck python bridge_headless.py (end task in Task Manager)")
        print("  - Tera Term / PuTTY / NMEA Simulator on the same COM")
        print("  - Mission Planner or other app using the port")
        print()
        print("[com_free] Python processes:")
        try:
            import subprocess

            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" "
                    "| Select-Object ProcessId,CommandLine | Format-Table -AutoSize",
                ],
                text=True,
                errors="replace",
            )
            print(out if out.strip() else "  (none)")
        except Exception as ex:
            print(f"  (could not list: {ex})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

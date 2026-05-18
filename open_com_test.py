#!/usr/bin/env python3
"""Test opening a COM port (bridge must be stopped)."""
import argparse
import sys

import serial

from bench_config import load_bench_defaults


def main() -> None:
    d = load_bench_defaults()
    p = argparse.ArgumentParser()
    p.add_argument("--com", default=str(d["com"]))
    p.add_argument("--baud", type=int, default=int(d["baud"]))
    args = p.parse_args()
    try:
        ser = serial.Serial(args.com, baudrate=args.baud, timeout=0)
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)
    print(f"OK: opened {args.com} @ {args.baud}")
    ser.close()


if __name__ == "__main__":
    main()

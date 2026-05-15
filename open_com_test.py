#!/usr/bin/env python3
"""Test opening a COM port (bridge must be stopped)."""
import argparse
import sys

import serial


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--com", default="COM7")
    p.add_argument("--baud", type=int, default=115200)
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

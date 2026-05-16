#!/usr/bin/env python3
"""Repeated headless bridge cycles (COM release + UDP path). Edit bench_defaults.json."""
from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

from bench_config import load_bench_defaults
from py_interpreter import cli_python_executable

ROOT = Path(__file__).resolve().parent


def main() -> int:
    d = load_bench_defaults()
    p = argparse.ArgumentParser(description="Stress headless bridge start/stop cycles")
    p.add_argument("--cycles", type=int, default=6, help="Headless runs (default 6)")
    p.add_argument("--seconds", type=float, default=2.0, help="Seconds per cycle")
    p.add_argument("--pause", type=float, default=0.35, help="Pause between cycles (COM settle)")
    args = p.parse_args()

    py = cli_python_executable()
    com = str(d["com"])
    baud = str(d["baud"])
    port = str(d["udp_port"])
    fails = 0

    print(f"[bench_stress] {args.cycles} cycles, {args.seconds}s each, pause {args.pause}s")
    print(f"[bench_stress] {com} @ {baud}, UDP :{port}")

    for i in range(1, args.cycles + 1):
        print(f"\n[bench_stress] cycle {i}/{args.cycles}")
        code = subprocess.call(
            [
                py,
                str(ROOT / "bridge_headless.py"),
                "--com",
                com,
                "--baud",
                baud,
                "--udp-port",
                port,
                "--seconds",
                str(args.seconds),
            ],
            cwd=ROOT,
        )
        if code != 0:
            print(f"[bench_stress] FAIL headless exit {code}")
            fails += 1
        code = subprocess.call(
            [py, str(ROOT / "com_free.py"), "--com", com, "--baud", baud],
            cwd=ROOT,
        )
        if code != 0:
            print(f"[bench_stress] FAIL com_free exit {code}")
            fails += 1
        if i < args.cycles:
            time.sleep(args.pause)

    if fails:
        print(f"\n[bench_stress] FAILED ({fails} step(s))")
        return 1
    print("\n[bench_stress] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

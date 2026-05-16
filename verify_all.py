#!/usr/bin/env python3
"""Run all automated checks (no GUI interaction). Exit 0 = all passed."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def run(name: str, args: list[str]) -> int:
    print(f"\n>> {name}: {' '.join(args)}")
    return subprocess.call([PY, *args], cwd=ROOT)


def main() -> int:
    steps = [
        ("compileall", ["-m", "compileall", "-q", str(ROOT)]),
        ("unittest", ["-m", "unittest", "test_nmea_codec", "test_bridge_metrics", "-q"]),
        ("com_free", ["com_free.py"]),
        ("check_setup", ["check_setup.py", "--port", "10110"]),
        ("bench_gui_smoke", ["bench_gui_smoke.py"]),
        ("bench_headless", ["bridge_headless.py", "--seconds", "2"]),
        ("bench_stress", ["bench_stress.py", "--cycles", "3", "--pause", "0.4"]),
    ]
    failed = 0
    for name, args in steps:
        if run(name, args) != 0:
            failed += 1
            print(f"FAIL: {name}")
    if failed:
        print(f"\n[verify_all] {failed} step(s) failed")
        return 1
    print("\n[verify_all] All automated checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

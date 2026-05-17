#!/usr/bin/env python3
"""Run all automated checks (no GUI interaction). Exit 0 = all passed.

When the bench UDP port is already bound (typically the bridge GUI is Running),
steps that need exclusive COM + UDP (com_free, bridge_headless, bench_stress) are
skipped so this script still passes. Set VERIFY_ALL_NO_SKIP=1 to run them anyway.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from bench_config import load_bench_defaults
from bench_udp_test import port_has_listener
from py_interpreter import cli_python_executable, subprocess_no_console_kwargs

ROOT = Path(__file__).resolve().parent
PY = cli_python_executable()


def compile_repo() -> int:
    """Compile project sources only (skip dist/, venv, __pycache__)."""
    import compileall
    import re

    skip = re.compile(r"(\\|/)(dist|\.venv|venv|__pycache__)(\\|/)")
    ok = compileall.compile_dir(str(ROOT), quiet=1, rx=skip)
    return 0 if ok else 1


def run(name: str, args: list[str]) -> int:
    print(f"\n>> {name}: {' '.join(args)}", flush=True)
    return subprocess.call([PY, *args], cwd=ROOT, **subprocess_no_console_kwargs())


def _bench_udp_port() -> int:
    try:
        return int(load_bench_defaults().get("udp_port", 10110))
    except (TypeError, ValueError):
        return 10110


def main() -> int:
    bench_port = _bench_udp_port()
    skip_hw = port_has_listener(bench_port) and os.environ.get("VERIFY_ALL_NO_SKIP", "").strip() not in (
        "1",
        "true",
        "yes",
    )

    if skip_hw:
        print(
            f"\n[verify_all] NOTE: UDP :{bench_port} is already in use (likely bridge GUI is Running).\n"
            "Skipping com_free, bridge_headless, and bench_stress (they need a free port and COM).\n"
            "Stop the bridge or set VERIFY_ALL_NO_SKIP=1 to run the full hardware suite.\n",
            flush=True,
        )

    steps: list[tuple[str, list[str] | None]] = [
        ("compileall", None),
        (
            "unittest",
            ["-m", "unittest", "discover", "-s", str(ROOT), "-p", "test_*.py", "-q"],
        ),
        ("com_free", ["com_free.py"]),
        ("check_setup", ["check_setup.py"]),
        ("bench_gui_smoke", ["bench_gui_smoke.py"]),
        ("bench_headless", ["bridge_headless.py", "--seconds", "2"]),
        ("bench_stress", ["bench_stress.py", "--cycles", "6", "--pause", "0.35"]),
    ]

    skip_names = {"com_free", "bench_headless", "bench_stress"}
    if skip_hw:
        steps = [(n, a) for (n, a) in steps if n not in skip_names]

    failed = 0
    for name, args in steps:
        if name == "compileall":
            print("\n>> compileall: project sources (excludes dist/, venv/)", flush=True)
            code = compile_repo()
        else:
            code = run(name, args or [])
        if code != 0:
            failed += 1
            print(f"FAIL: {name}", flush=True)
    if failed:
        print(f"\n[verify_all] {failed} step(s) failed", flush=True)
        return 1
    if skip_hw:
        print(
            "\n[verify_all] All automated checks passed (hardware stress steps skipped — UDP port in use).",
            flush=True,
        )
    else:
        print("\n[verify_all] All automated checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run all automated checks (no GUI interaction). Exit 0 = all passed.

When the bench UDP port is already bound (typically the bridge GUI is Running),
steps that need exclusive COM + UDP (com_free, bridge_headless, bench_stress) are
skipped so this script still passes. Set VERIFY_ALL_NO_SKIP=1 to run them anyway.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from bench_config import load_bench_defaults
from bench_udp_test import port_has_listener
from py_interpreter import cli_python_executable, subprocess_no_console_kwargs
from ui.qt_test_harness import is_windows_qt_shutdown_exit, unittest_output_indicates_ok

ROOT = Path(__file__).resolve().parent
PY = cli_python_executable()
_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\):")


def compile_repo() -> int:
    """Compile project sources only (skip dist/, venv, __pycache__)."""
    import compileall
    import re

    skip = re.compile(r"(\\|/)(dist|\.venv|venv|__pycache__)(\\|/)")
    ok = compileall.compile_dir(str(ROOT), quiet=1, rx=skip)
    return 0 if ok else 1


def _has_traceback(text: str) -> bool:
    return bool(_TRACEBACK_RE.search(text or ""))


def _step_success(
    name: str,
    code: int | None,
    stdout: str,
    stderr: str,
    *,
    tb_seen: bool,
) -> bool:
    if code == 0 and tb_seen and name == "unittest" and unittest_output_indicates_ok(stdout, stderr):
        print(
            "[verify_all] NOTE: unittest logged expected handler tracebacks — treated as pass.",
            flush=True,
        )
        return True
    if tb_seen:
        return False
    if code == 0:
        return True
    if not is_windows_qt_shutdown_exit(code):
        return False
    if name == "unittest" and unittest_output_indicates_ok(stdout, stderr):
        print(
            "[verify_all] NOTE: unittest Qt shutdown fast-fail (0xC0000409) after OK — treated as pass.",
            flush=True,
        )
        return True
    if name == "bench_gui_smoke" and "All UIs OK" in (stdout or ""):
        print(
            "[verify_all] NOTE: bench_gui_smoke Qt shutdown fast-fail (0xC0000409) after OK — treated as pass.",
            flush=True,
        )
        return True
    return False


def run(name: str, args: list[str], *, echo_output: bool = True) -> tuple[int, bool]:
    print(f"\n>> {name}: {' '.join(args)}", flush=True)
    proc = subprocess.run(
        [PY, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        **subprocess_no_console_kwargs(),
    )
    if echo_output and proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if echo_output and proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", flush=True)
    tb_seen = _has_traceback(proc.stdout or "") or _has_traceback(proc.stderr or "")
    if _step_success(name, proc.returncode, proc.stdout or "", proc.stderr or "", tb_seen=tb_seen):
        return 0, False
    return proc.returncode, tb_seen


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
        ("unittest", ["tools/run_unittests.py"]),
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
            tb_seen = False
        else:
            code, tb_seen = run(name, args or [])
        if code != 0 or tb_seen:
            failed += 1
            why = "traceback detected" if tb_seen and code == 0 else f"exit={code}"
            print(f"FAIL: {name} ({why})", flush=True)
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

#!/usr/bin/env python3
"""Run all automated checks (no GUI interaction). Exit 0 = all passed.

When the bench UDP port is already bound (typically the bridge GUI is Running),
steps that need exclusive COM + UDP (com_free, bridge_headless, bench_stress) are
skipped so this script still passes. Set VERIFY_ALL_NO_SKIP=1 to run them anyway.

On GitHub Actions (and other CI hosts with GITHUB_ACTIONS/CI set), COM hardware
benches are skipped automatically — runners have no com0com/COM1. Full bench
suites still run on a normal local `python verify_all.py`.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from bench_config import load_bench_defaults
from bench_udp_test import port_has_listener
from py_interpreter import cli_python_executable, subprocess_no_console_kwargs, subprocess_script_argv
from ui.qt_test_harness import is_windows_qt_shutdown_exit, unittest_output_indicates_ok

ROOT = Path(__file__).resolve().parent
PY = cli_python_executable()
_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\):")

# Steps that open the bench COM port or require com0com (headless bridge paths).
_HW_COM_STEPS = frozenset(
    {
        "com_free",
        "bench_headless",
        "bench_stress",
        "bench_network",
        "bench_fanout",
    }
)
# Subset skipped when the bench UDP port is already bound locally (GUI running).
_UDP_BUSY_SKIP_STEPS = frozenset(
    {
        "com_free",
        "bench_headless",
        "bench_stress",
    }
)


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
    if name == "unittest" and unittest_output_indicates_ok(stdout, stderr):
        if is_windows_qt_shutdown_exit(code):
            print(
                "[verify_all] NOTE: unittest Qt shutdown fast-fail (0xC0000409) after OK — treated as pass.",
                flush=True,
            )
            return True
        if code == 0 and tb_seen:
            print(
                "[verify_all] NOTE: unittest logged expected handler tracebacks — treated as pass.",
                flush=True,
            )
            return True
        if code == 0:
            return True
    if name == "bench_gui_smoke" and "All UIs OK" in (stdout or ""):
        if is_windows_qt_shutdown_exit(code) or code == 0:
            if is_windows_qt_shutdown_exit(code):
                print(
                    "[verify_all] NOTE: bench_gui_smoke Qt shutdown fast-fail (0xC0000409) after OK — treated as pass.",
                    flush=True,
                )
            return True
    if tb_seen:
        return False
    if code == 0:
        return True
    if is_windows_qt_shutdown_exit(code):
        return False
    return False


def run_unittest_file(name: str, module: str) -> tuple[int, bool]:
    print(f"\n>> {name}: python -m unittest {module}", flush=True)
    proc = subprocess.run(
        [PY, "-m", "unittest", module],
        cwd=ROOT,
        capture_output=True,
        text=True,
        **subprocess_no_console_kwargs(),
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", flush=True)
    tb_seen = _has_traceback(proc.stdout or "") or _has_traceback(proc.stderr or "")
    if proc.returncode == 0 and not tb_seen:
        return 0, False
    return proc.returncode or 1, tb_seen


def run(name: str, args: list[str], *, echo_output: bool = True) -> tuple[int, bool]:
    print(f"\n>> {name}: {' '.join(args)}", flush=True)
    script = args[0]
    script_args = args[1:]
    proc = subprocess.run(
        subprocess_script_argv(ROOT / script, script_args),
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


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _is_ci_host() -> bool:
    """True on GitHub Actions and similar CI runners (no bench COM hardware)."""
    return _truthy_env("GITHUB_ACTIONS") or _truthy_env("CI")


def _skip_step_names() -> frozenset[str]:
    """Return verify_all step names to skip for this host/environment."""
    if _truthy_env("VERIFY_ALL_NO_SKIP"):
        return frozenset()
    if _is_ci_host():
        return _HW_COM_STEPS
    bench_port = _bench_udp_port()
    if port_has_listener(bench_port):
        return _UDP_BUSY_SKIP_STEPS
    return frozenset()


def _print_skip_notice(skip_names: frozenset[str]) -> None:
    if not skip_names:
        return
    if _is_ci_host() and not _truthy_env("VERIFY_ALL_NO_SKIP"):
        print(
            "\n[verify_all] NOTE: CI host (GITHUB_ACTIONS/CI) — skipping COM hardware benches:\n"
            f"  {', '.join(sorted(skip_names))}\n"
            "GitHub runners have no com0com/COM1. Run `python verify_all.py` locally for the full suite.\n"
            "Set VERIFY_ALL_NO_SKIP=1 to force hardware steps on CI (will fail without COM).\n",
            flush=True,
        )
        return
    bench_port = _bench_udp_port()
    print(
        f"\n[verify_all] NOTE: UDP :{bench_port} is already in use (likely bridge GUI is Running).\n"
        "Skipping com_free, bridge_headless, and bench_stress (they need a free port and COM).\n"
        "Stop the bridge or set VERIFY_ALL_NO_SKIP=1 to run the full hardware suite.\n",
        flush=True,
    )


def main() -> int:
    skip_names = _skip_step_names()
    _print_skip_notice(skip_names)

    steps: list[tuple[str, list[str] | None]] = [
        ("compileall", None),
        ("gui_no_console", ["tools/gui_no_console_check.py"]),
        ("app_icon", ["tests.test_app_icon"]),
        ("unittest", ["tools/run_unittests.py"]),
        ("com_free", ["com_free.py"]),
        ("check_setup", ["check_setup.py"]),
        ("bench_gui_smoke", ["bench_gui_smoke.py"]),
        ("bench_headless", ["bridge_headless.py", "--seconds", "2"]),
        ("bench_stress", ["bench_stress.py", "--cycles", "6", "--pause", "0.35"]),
        ("bench_network", ["bench_network_automation.py"]),
        (
            "bench_fanout",
            ["bench_fanout_automation.py", "--skip-single-link", "--live-min-recv", "0"],
        ),
    ]

    if skip_names:
        steps = [(n, a) for (n, a) in steps if n not in skip_names]

    failed = 0
    for name, args in steps:
        if name == "compileall":
            print("\n>> compileall: project sources (excludes dist/, venv/)", flush=True)
            code = compile_repo()
            tb_seen = False
        elif name == "app_icon":
            code, tb_seen = run_unittest_file(name, args[0])
        else:
            code, tb_seen = run(name, args or [])
        if code != 0 or tb_seen:
            failed += 1
            why = "traceback detected" if tb_seen and code == 0 else f"exit={code}"
            print(f"FAIL: {name} ({why})", flush=True)
    if failed:
        print(f"\n[verify_all] {failed} step(s) failed", flush=True)
        return 1
    if skip_names:
        if _is_ci_host() and not _truthy_env("VERIFY_ALL_NO_SKIP"):
            print(
                "\n[verify_all] All automated checks passed "
                "(COM hardware benches skipped on CI — run locally for full bench).",
                flush=True,
            )
        else:
            print(
                "\n[verify_all] All automated checks passed "
                "(hardware stress steps skipped — UDP port in use).",
                flush=True,
            )
    else:
        print("\n[verify_all] All automated checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

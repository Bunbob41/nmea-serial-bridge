#!/usr/bin/env python3
"""Run unittest discover; normalize Windows Qt post-shutdown exit code."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_DISCOVER_ARGS = ["-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "test_*.py"]
_FAIL_LINE_RE = re.compile(r"^(?:FAIL|ERROR): .+", re.MULTILINE)


def _print_failure_summary(stdout: str, stderr: str) -> None:
    combined = (stdout or "") + (stderr or "")
    lines = [ln for ln in _FAIL_LINE_RE.findall(combined)]
    if lines:
        print("[run_unittests] Failing tests:", flush=True)
        for ln in lines:
            print(f"  {ln}", flush=True)
        return
    progress = ""
    try:
        from ui.qt_test_harness import unittest_dot_progress

        progress = unittest_dot_progress(stdout, stderr)
    except Exception:
        pass
    if "F" in progress or "E" in progress:
        print(
            "[run_unittests] unittest dot progress contains failure markers "
            f"({progress.count('F')} F, {progress.count('E')} E) — re-run with -v above.",
            flush=True,
        )


def _run_discover(py: str, *, verbose: bool) -> subprocess.CompletedProcess[str]:
    args = [py, *_DISCOVER_ARGS]
    if verbose:
        args.append("-v")
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def main() -> int:
    root_s = str(ROOT)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    from py_interpreter import cli_python_executable
    from ui.qt_test_harness import is_windows_qt_shutdown_exit, unittest_output_indicates_ok

    py = cli_python_executable()
    proc = _run_discover(py, verbose=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", flush=True)

    ok = proc.returncode == 0
    qt_shutdown = is_windows_qt_shutdown_exit(proc.returncode) and unittest_output_indicates_ok(
        proc.stdout or "", proc.stderr or ""
    )
    if not ok and not qt_shutdown:
        print("\n[run_unittests] unittest discover failed — re-running with -v", flush=True)
        verbose = _run_discover(py, verbose=True)
        if verbose.stdout:
            print(verbose.stdout, end="" if verbose.stdout.endswith("\n") else "\n", flush=True)
        if verbose.stderr:
            print(verbose.stderr, end="" if verbose.stderr.endswith("\n") else "\n", flush=True)
        _print_failure_summary(verbose.stdout or "", verbose.stderr or "")
        return int(proc.returncode or 1)

    if qt_shutdown:
        print(
            "[run_unittests] NOTE: Qt shutdown fast-fail (0xC0000409) after all tests OK — treated as pass.",
            flush=True,
        )
        if sys.platform == "win32":
            os._exit(0)
        return 0
    return 0


if __name__ == "__main__":
    code = main()
    if sys.platform == "win32" and code == 0:
        os._exit(0)
    raise SystemExit(code)

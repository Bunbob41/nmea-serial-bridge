#!/usr/bin/env python3
"""Run unittest discover; normalize Windows Qt post-shutdown exit code."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    root_s = str(ROOT)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    from py_interpreter import cli_python_executable
    from ui.qt_test_harness import is_windows_qt_shutdown_exit, unittest_output_indicates_ok

    py = cli_python_executable()
    proc = subprocess.run(
        [py, "-m", "unittest", "discover", "-s", str(ROOT), "-p", "test_*.py", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", flush=True)
    if proc.returncode == 0:
        return 0
    if is_windows_qt_shutdown_exit(proc.returncode) and unittest_output_indicates_ok(
        proc.stdout or "", proc.stderr or ""
    ):
        print(
            "[run_unittests] NOTE: Qt shutdown fast-fail (0xC0000409) after all tests OK — treated as pass.",
            flush=True,
        )
        if sys.platform == "win32":
            os._exit(0)
        return 0
    return int(proc.returncode or 1)


if __name__ == "__main__":
    code = main()
    if sys.platform == "win32" and code == 0:
        os._exit(0)
    raise SystemExit(code)

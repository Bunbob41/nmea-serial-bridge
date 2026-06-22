#!/usr/bin/env python3
"""QC: PyInstaller console=False sets stdio to None — entry points must not crash."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge_gui import _should_minimize_launch_console
from py_interpreter import stream_isatty


def main() -> int:
    saved = sys.stderr, sys.stdin, sys.stdout
    try:
        sys.stderr = None
        sys.stdin = None
        sys.stdout = None
        if stream_isatty(sys.stderr) or stream_isatty(sys.stdin):
            print("[gui_no_console_check] FAIL: null streams reported as TTY")
            return 1
        if _should_minimize_launch_console(foreground=False):
            print("[gui_no_console_check] FAIL: would call isatty on null stderr")
            return 1
    finally:
        sys.stderr, sys.stdin, sys.stdout = saved
    print("[gui_no_console_check] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

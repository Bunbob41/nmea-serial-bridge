#!/usr/bin/env python3
"""Post-build QC: frozen serial-link.exe must survive startup (console=False / stderr=None)."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCH_LOG = Path.home() / ".cursor-udp-com-bridge" / "launch.log"


def _log_marker() -> str:
    if LAUNCH_LOG.is_file():
        return LAUNCH_LOG.read_text(encoding="utf-8", errors="replace")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test frozen serial-link.exe startup")
    parser.add_argument(
        "exe",
        nargs="?",
        default=str(ROOT / "dist" / "serial-link" / "serial-link.exe"),
        help="Path to serial-link.exe",
    )
    parser.add_argument("--wait", type=float, default=5.0, help="Seconds to wait after launch")
    args = parser.parse_args()

    exe = Path(args.exe).resolve()
    if not exe.is_file():
        print(f"[frozen_gui_smoke] FAIL: missing {exe}", file=sys.stderr)
        return 1

    before = _log_marker()
    try:
        proc = subprocess.Popen(
            [str(exe), "--ui", "modern"],
            cwd=str(exe.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except OSError as exc:
        print(f"[frozen_gui_smoke] FAIL: could not start exe: {exc}", file=sys.stderr)
        return 1

    time.sleep(max(1.0, float(args.wait)))
    code = proc.poll()
    if code is not None:
        print(f"[frozen_gui_smoke] FAIL: exe exited early with code {code}", file=sys.stderr)
        return 1

    after = _log_marker()
    new_lines = [ln for ln in after[len(before) :].splitlines() if ln.strip()]
    if any("CRASH" in ln for ln in new_lines):
        print("[frozen_gui_smoke] FAIL: launch.log reports CRASH", file=sys.stderr)
        for ln in new_lines[-5:]:
            print(f"  {ln}", file=sys.stderr)
        proc.terminate()
        return 1
    if not any("OPEN ui=" in ln for ln in new_lines):
        print("[frozen_gui_smoke] FAIL: launch.log missing OPEN ui= line", file=sys.stderr)
        proc.terminate()
        return 1

    print(f"[frozen_gui_smoke] OK pid={proc.pid} exe={exe.name}")
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

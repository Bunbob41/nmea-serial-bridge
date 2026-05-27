#!/usr/bin/env python3
"""One-shot bench checks (no GUI). Edit bench_defaults.json for COM / UDP port."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from bench_config import load_bench_defaults

ROOT = Path(__file__).resolve().parent


def _run(cmd: list[str]) -> int:
    print(f"\n>> {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    d = load_bench_defaults()
    com = str(d["com"])
    port = int(d["udp_port"])
    py = sys.executable

    def script(name: str) -> str:
        return str(ROOT / name)

    print(f"[bench_all] defaults: {com} @ {d['baud']}, UDP :{port}")

    code = _run([py, script("check_setup.py")])
    if code != 0:
        return code

    code = _run([py, script("com_free.py"), "--com", com, "--baud", str(d["baud"])])
    if code != 0:
        print("[bench_all] COM open failed — close other apps on that port.")
        return code

    code = _run(
        [
            py,
            script("bridge_headless.py"),
            "--com",
            com,
            "--baud",
            str(d["baud"]),
            "--udp-port",
            str(port),
            "--seconds",
            "1.5",
        ]
    )
    if code != 0:
        print("[bench_all] headless bridge test failed.")
        return code

    code = _run([py, script("bench_gui_smoke.py")])
    if code != 0:
        return code

    code = _run([py, script("bench_network_automation.py")])
    if code != 0:
        print("[bench_all] network automation failed (see output above).")
        return code

    code = _run([py, script("bench_fanout_automation.py")])
    if code != 0:
        print("[bench_all] fan-out automation failed (see output above).")
        return code

    print("\n[bench_all] OK — for GUI: shortcut -> bench preset -> Start -> watch paired COM.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

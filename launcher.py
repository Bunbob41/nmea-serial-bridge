#!/usr/bin/env python3
"""Start the bridge GUI. Default: no console — saved UI or Qt layout picker."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ui.registry import UI_DEFAULT, UI_LABELS, UI_ORDER

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_choice.json"
ROOT = Path(__file__).resolve().parent
PY = sys.executable


def _pythonw_next_to(sys_exe: Path) -> Path | None:
    p = sys_exe.resolve()
    if p.name.lower() == "pythonw.exe":
        return p
    cand = p.parent / "pythonw.exe"
    return cand if cand.is_file() else None


def _resolve_pythonw_for_spawn() -> Path:
    """Prefer pythonw beside the interpreter that ran launcher; avoid stale hard-coded paths."""
    cur = Path(sys.executable)
    n = _pythonw_next_to(cur)
    if n is not None:
        return n
    legacy = Path(r"C:\Program Files\Python314\pythonw.exe")
    if legacy.is_file():
        return legacy
    return cur


def _load_choice() -> str | None:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        ui = data.get("ui")
        if ui in UI_ORDER:
            return ui
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return None


def _save_choice(ui: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"ui": ui}, indent=2), encoding="utf-8")


def _menu() -> str:
    print("\n  NMEA Serial Bridge — choose UI\n")
    for i, uid in enumerate(UI_ORDER, 1):
        print(f"  {i}. {UI_LABELS[uid]}")
    print(f"  {len(UI_ORDER) + 1}. Remember last & launch")
    print("  0. Exit\n")
    last = _load_choice()
    if last:
        print(f"  (last: {UI_LABELS.get(last, last)})\n")
    while True:
        raw = input("Choice [1]: ").strip() or "1"
        if raw == "0":
            raise SystemExit(0)
        if raw == str(len(UI_ORDER) + 1) and last:
            return last
        try:
            n = int(raw)
            if 1 <= n <= len(UI_ORDER):
                return UI_ORDER[n - 1]
        except ValueError:
            pass
        print("  Invalid — try again.")


def _spawn_gui(ui_arg: list[str]) -> None:
    exe = _resolve_pythonw_for_spawn()
    script = ROOT / "bridge_gui.py"
    subprocess.Popen([str(exe), str(script), *ui_arg], cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch NMEA bridge GUI")
    parser.add_argument(
        "--console-menu",
        action="store_true",
        help="Interactive 1–4 menu in this terminal (for debugging)",
    )
    args = parser.parse_args()

    if args.console_menu:
        ui = _menu()
        remember = input("Remember this UI for next time? [Y/n]: ").strip().lower()
        if remember in ("", "y", "yes"):
            _save_choice(ui)
        _spawn_gui(["--ui", ui])
        print(f"\nLaunched: {UI_LABELS[ui]}\n")
        return 0

    saved = _load_choice()
    if saved:
        _spawn_gui(["--ui", saved])
    else:
        _spawn_gui(["--pick-ui"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

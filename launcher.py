#!/usr/bin/env python3
"""Choose UI layout, optionally remember choice, then start the bridge GUI."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ui.registry import UI_DEFAULT, UI_LABELS, UI_ORDER

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_choice.json"
ROOT = Path(__file__).resolve().parent
PY = sys.executable
PYTHONW = Path(r"C:\Program Files\Python314\pythonw.exe")
if not PYTHONW.is_file():
    PYTHONW = Path(sys.executable.replace("python.exe", "pythonw.exe"))


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


def main() -> int:
    ui = _menu()
    remember = input("Remember this UI for next time? [Y/n]: ").strip().lower()
    if remember in ("", "y", "yes"):
        _save_choice(ui)
    exe = PYTHONW if PYTHONW.is_file() else Path(PY)
    script = ROOT / "bridge_gui.py"
    subprocess.Popen([str(exe), str(script), "--ui", ui], cwd=ROOT)
    print(f"\nLaunched: {UI_LABELS[ui]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

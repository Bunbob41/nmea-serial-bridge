#!/usr/bin/env python3
"""Start the bridge GUI. Default: no console — saved UI or Qt layout picker."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ui.registry import (
    UI_DEFAULT,
    UI_DESCRIPTIONS,
    UI_FIELD,
    UI_LABELS,
    UI_LEGACY_ALIASES,
    UI_ORDER,
    normalize_ui_id,
)
from version import __version__

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_choice.json"
ROOT = Path(__file__).resolve().parent


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


def _load_choice(*, migrate_legacy: bool = True) -> str | None:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        raw = str(data.get("ui") or "")
        ui = normalize_ui_id(raw)
        if ui not in UI_ORDER:
            return None
        if migrate_legacy and raw in UI_LEGACY_ALIASES:
            _save_choice(ui)
        return ui
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def _save_choice(ui: str) -> None:
    ui = normalize_ui_id(ui)
    if ui not in UI_ORDER:
        ui = UI_DEFAULT
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"ui": ui}, indent=2), encoding="utf-8")


def _menu() -> str:
    print(f"\n  Serial Link v{__version__} — Ethernet ↔ serial — choose layout\n")
    for i, uid in enumerate(UI_ORDER, 1):
        print(f"  {i}. {UI_LABELS[uid]}")
        for line in UI_DESCRIPTIONS[uid].split(". "):
            line = line.strip()
            if line:
                print(f"       {line}.")
    remember_n = len(UI_ORDER) + 1
    print(f"\n  {remember_n}. Remember last saved layout and launch")
    print("  0. Exit\n")
    last = _load_choice()
    if last:
        print(f"  (last saved: {UI_LABELS.get(last, last)})\n")
    default = "2" if UI_FIELD in UI_ORDER and UI_ORDER.index(UI_FIELD) == 1 else "1"
    while True:
        raw = input(f"Choice [{default}]: ").strip() or default
        if raw == "0":
            raise SystemExit(0)
        if raw == str(remember_n) and last:
            return last
        try:
            n = int(raw)
            if 1 <= n <= len(UI_ORDER):
                return UI_ORDER[n - 1]
        except ValueError:
            pass
        print("  Invalid — enter a number from the menu.")


def _spawn_gui(ui_arg: list[str], *, foreground: bool = False) -> None:
    """Launch bridge_gui. Use foreground+python.exe when run from a terminal (errors visible)."""
    script = ROOT / "bridge_gui.py"
    if foreground:
        exe = Path(sys.executable)
        raise SystemExit(subprocess.call([str(exe), str(script), *ui_arg], cwd=str(ROOT)))
    exe = _resolve_pythonw_for_spawn()
    subprocess.Popen([str(exe), str(script), *ui_arg], cwd=str(ROOT))
    if sys.stdin.isatty():
        print(
            f"Started GUI in background ({exe.name}). "
            "If no window appears, run:\n"
            f"  python \"{script}\"\n"
            "or:\n"
            f"  python launcher.py --foreground\n"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"Launch Serial Link GUI (v{__version__})",
    )
    parser.add_argument(
        "--ui",
        choices=list(UI_ORDER),
        help="Layout: standard (full Connect tab) or field (survey log-first)",
    )
    parser.add_argument(
        "--pick-ui",
        action="store_true",
        help="Always show the layout picker (ignore saved choice)",
    )
    parser.add_argument(
        "--console-menu",
        action="store_true",
        help="Interactive numbered menu in this terminal",
    )
    parser.add_argument(
        "--foreground",
        "-f",
        action="store_true",
        help="Run GUI in this terminal (shows errors; blocks until you close the app)",
    )
    args = parser.parse_args()
    foreground = bool(args.foreground)

    if args.console_menu:
        ui = _menu()
        remember = input("Remember this layout for next time? [y/N]: ").strip().lower()
        if remember in ("y", "yes"):
            _save_choice(ui)
        else:
            from ui.picker import clear_saved_ui_choice

            clear_saved_ui_choice()
        _spawn_gui(["--ui", ui], foreground=foreground)
        if not foreground:
            print(f"\nLaunched: {UI_LABELS[ui]}\n")
        return 0

    if args.ui:
        ui = normalize_ui_id(args.ui)
        if ui in UI_ORDER:
            _spawn_gui(["--ui", ui], foreground=foreground)
            return 0

    if args.pick_ui:
        _spawn_gui(["--pick-ui"], foreground=foreground or sys.stdin.isatty())
        return 0

    saved = _load_choice()
    if saved:
        _spawn_gui(["--ui", saved], foreground=foreground)
    else:
        _spawn_gui(["--pick-ui"], foreground=foreground)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Dev helper: wipe saved UI/layout prefs so the next launch feels like first run.

Removes %USERPROFILE%\\.cursor-udp-com-bridge\\ (layout choice, ui_prefs, theme,
HUD layout, named path presets on this PC).

Close the bridge GUI before running. Safe to delete this file when you are done testing.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".cursor-udp-com-bridge"

KNOWN_FILES = (
    "ui_choice.json",
    "ui_prefs.json",
    "ui_theme.json",
    "path_presets.json",
    "survey_hud_layout.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset NMEA bridge saved prefs (first-launch style)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be removed without deleting.",
    )
    parser.add_argument(
        "--keep-presets",
        action="store_true",
        help="Keep path_presets.json (only reset UI/layout/HUD/theme).",
    )
    args = parser.parse_args()

    if not CONFIG_DIR.exists():
        print(f"Nothing to reset — folder does not exist:\n  {CONFIG_DIR}")
        return 0

    # Guard against accidental wrong path
    resolved = CONFIG_DIR.resolve()
    home = Path.home().resolve()
    if resolved.parent != home or resolved.name != ".cursor-udp-com-bridge":
        print(f"Refusing to touch unexpected path:\n  {resolved}", file=sys.stderr)
        return 1

    targets: list[Path] = []
    if args.keep_presets:
        for name in KNOWN_FILES:
            if name == "path_presets.json":
                continue
            p = CONFIG_DIR / name
            if p.exists():
                targets.append(p)
        for p in sorted(CONFIG_DIR.iterdir()):
            if p.name not in KNOWN_FILES and p.is_file():
                targets.append(p)
    else:
        targets = [CONFIG_DIR]

    print("NMEA bridge — reset saved prefs")
    print(f"  Folder: {CONFIG_DIR}\n")
    if args.dry_run:
        print("[dry-run] Would remove:")
        for t in targets:
            if t.is_dir():
                for child in sorted(t.rglob("*")):
                    print(f"  - {child}")
            else:
                print(f"  - {t}")
        print("\nRe-run without --dry-run to apply.")
        return 0

    for t in targets:
        if t.is_dir():
            shutil.rmtree(t)
            print(f"Removed folder: {t}")
        elif t.is_file():
            t.unlink()
            print(f"Removed file:   {t}")

    print("\nDone. Next launch should show the layout picker (if using launcher)")
    print("and default UI prefs — as if first run on this PC.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# bridge_gui.py — entry point for Network ↔ COM bridge GUI
from __future__ import annotations

import argparse
import multiprocessing
import os
import sys

from py_interpreter import run_frozen_helper_if_requested

# Frozen one-folder build: run bundled Diagnostics helpers without spawning system python.exe.
_helper_code = run_frozen_helper_if_requested()
if _helper_code is not None:
    raise SystemExit(_helper_code)

from PySide6 import QtWidgets

from bridge_core import (  # noqa: F401 — re-export for older scripts
    NetMode,
    SerialNetBridge,
    configure_windows_event_loop_policy,
)
from ui.app_icon import apply_app_icon
from ui.fonts import app_ui_font, ensure_bundled_fonts
from ui.registry import create_window
from ui.standard import BridgeWindowStandard

BridgeWindow = BridgeWindowStandard


def main() -> None:
    parser = argparse.ArgumentParser(description="NMEA UDP/TCP ↔ serial bridge")
    parser.add_argument(
        "--ui",
        choices=["standard", "field", "modern", "minimal", "logfirst"],
        default=None,
        help="UI layout (default: saved choice, picker on first .exe run, else standard)",
    )
    parser.add_argument(
        "--pick-ui",
        action="store_true",
        help="Show layout picker dialog before opening the window",
    )
    args = parser.parse_args()

    # Qt6-native high-DPI scaling — must be set before QApplication is constructed.
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    ensure_bundled_fonts()
    app.setFont(app_ui_font())
    apply_app_icon(app)

    from PySide6.QtCore import QLockFile, QStandardPaths

    lock_path = os.path.join(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation),
        "nmea-serial-bridge.lock",
    )
    instance_lock = QLockFile(lock_path)
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock(400):
        if instance_lock.error() == QLockFile.LockError.LockFailedError:
            instance_lock.removeStaleLockFile()
            instance_lock.tryLock(400)
        if not instance_lock.isLocked():
            QtWidgets.QMessageBox.warning(
                None,
                "Already running",
                "Serial Link is already open.\n\n"
                "Check the taskbar or system tray for the window. "
                "If you switched layouts earlier, end the old python.exe in "
                "Task Manager only if no window is visible.",
            )
            return
    app._instance_lock = instance_lock  # type: ignore[attr-defined]

    from ui.layout_switch_hook import install_three_way_layout_cycle
    from ui.picker import load_saved_ui, resolve_ui_id

    install_three_way_layout_cycle()

    # Only show the picker when explicitly requested via --pick-ui.
    # Field is the default layout; users swap to Standard via the Layout chip.
    show_picker = args.pick_ui
    ui_id = resolve_ui_id(args.ui, show_picker=show_picker)
    w = create_window(ui_id)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        multiprocessing.freeze_support()
    main()

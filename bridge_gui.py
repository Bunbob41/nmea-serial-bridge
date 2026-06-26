# bridge_gui.py — entry point for Network ↔ COM bridge GUI
from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from pathlib import Path

from py_interpreter import run_frozen_helper_if_requested, stream_isatty

# Frozen one-folder build: run bundled Diagnostics helpers without spawning system python.exe.
_helper_code = run_frozen_helper_if_requested()
if _helper_code is not None:
    raise SystemExit(_helper_code)

from PySide6 import QtWidgets

from ui.window_present import schedule_launch_focus

from bridge_core import (  # noqa: F401 — re-export for older scripts
    NetMode,
    SerialNetBridge,
    configure_windows_event_loop_policy,
)
from ui.app_icon import apply_app_icon
from ui.fonts import app_ui_font, configure_qt_font_environment, ensure_bundled_fonts
from ui.registry import UI_FIELD, create_window

BridgeWindow = None  # resolved via create_window(ui_id)


def _launch_log(msg: str) -> None:
    try:
        log_dir = Path.home() / ".cursor-udp-com-bridge"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "launch.log").open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
    except OSError:
        pass


def _schedule_present_main_window(win: QtWidgets.QWidget) -> None:
    schedule_launch_focus(win)


def _minimize_launch_console() -> None:
    """Hide the launcher console after the GUI is up (python.exe dev runs)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
    except Exception:
        pass


def _should_minimize_launch_console(*, foreground: bool) -> bool:
    """Hide dev launcher console after GUI show; skip when stderr is missing (frozen exe)."""
    return not foreground and sys.platform == "win32" and stream_isatty(sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="NMEA UDP/TCP ↔ serial bridge")
    parser.add_argument(
        "--foreground",
        "-f",
        action="store_true",
        help="Keep this console open (debug)",
    )
    parser.add_argument(
        "--ui",
        choices=["field", "modern", "minimal", "logfirst", "standard"],
        default=None,
        help="UI layout (default: saved choice, picker on first .exe run, else field)",
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
    configure_qt_font_environment()

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
        instance_lock.removeStaleLockFile()
        instance_lock.tryLock(400)
    if not instance_lock.isLocked():
        msg = (
            "Serial Link is already open.\n\n"
            "Check the taskbar or system tray (^ by the clock) for a hidden window. "
            "If the bridge was running when you closed the window, it may still be "
            "in the tray — right-click the icon and choose Exit.\n\n"
            "If nothing is visible, end stray python.exe / serial-link.exe in Task Manager, "
            "delete this lock file, then try again:\n"
            f"{lock_path}"
        )
        if stream_isatty(sys.stderr):
            print(msg, file=sys.stderr)
        _launch_log(f"LOCKED: {msg}")
        QtWidgets.QMessageBox.warning(None, "Already running", msg)
        return
    app._instance_lock = instance_lock  # type: ignore[attr-defined]

    def _release_instance_lock() -> None:
        lock = getattr(app, "_instance_lock", None)
        if lock is not None and lock.isLocked():
            try:
                lock.unlock()
            except Exception:
                pass

    app.aboutToQuit.connect(_release_instance_lock)

    from ui.layout_switch_hook import install_three_way_layout_cycle
    from ui.picker import load_saved_ui, resolve_ui_id

    install_three_way_layout_cycle()

    # Only show the picker when explicitly requested via --pick-ui.
    # Field is the default layout; users swap to Standard via the Layout chip.
    show_picker = args.pick_ui
    ui_id = resolve_ui_id(args.ui, show_picker=show_picker)
    try:
        w = create_window(ui_id)
        w.show()
        _schedule_present_main_window(w)
        if _should_minimize_launch_console(foreground=bool(args.foreground)):
            _minimize_launch_console()
        _launch_log(
            f"OPEN ui={ui_id} title={w.windowTitle()} geo={w.frameGeometry().getRect()}"
        )
    except Exception:
        _release_instance_lock()
        _launch_log("CRASH during create/show")
        raise
    # os._exit: lingering QThreads can block a normal sys.exit after app.quit().
    code = app.exec()
    try:
        from PySide6 import QtCore

        QtCore.QThreadPool.globalInstance().waitForDone(1500)
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
    except Exception:
        pass
    os._exit(int(code) if isinstance(code, int) else 0)


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        multiprocessing.freeze_support()
    main()

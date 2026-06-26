"""Bring the main bridge window on-screen and to the foreground."""
from __future__ import annotations

import sys

from PySide6 import QtCore, QtWidgets

_LAUNCH_FOCUS_ATTR = "_serial_link_launch_focus_done"


def clamp_main_window_to_screen(win: QtWidgets.QWidget) -> None:
    """Keep the window on a visible monitor without restoring minimize or stealing focus."""
    if win.windowState() & QtCore.Qt.WindowState.WindowMinimized:
        return
    if not win.isVisible():
        return

    app = QtWidgets.QApplication.instance()
    screen = win.screen() or (app.primaryScreen() if app is not None else None)
    if screen is None:
        return
    available = screen.availableGeometry()
    if win.width() > available.width() or win.height() > available.height():
        win.resize(
            min(win.width(), available.width()),
            min(win.height(), available.height()),
        )
    frame = win.frameGeometry()
    x = max(available.left(), min(frame.x(), available.right() - frame.width() + 1))
    y = max(available.top(), min(frame.y(), available.bottom() - frame.height() + 1))
    if x != frame.x() or y != frame.y():
        win.move(x, y)
        frame = win.frameGeometry()
    if not available.intersects(frame):
        frame.moveCenter(available.center())
        win.move(frame.topLeft())


def focus_main_window_at_launch(win: QtWidgets.QWidget) -> None:
    """One-time startup focus — never call while the user has minimized the window."""
    if getattr(win, _LAUNCH_FOCUS_ATTR, False):
        return
    setattr(win, _LAUNCH_FOCUS_ATTR, True)

    win.showNormal()
    if sys.platform == "win32":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            hwnd = int(win.winId())
            user32.AllowSetForegroundWindow(0xFFFFFFFF)  # ASFW_ANY
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
    else:
        try:
            win.raise_()
        except Exception:
            pass
        win.activateWindow()
    clamp_main_window_to_screen(win)


def schedule_launch_focus(win: QtWidgets.QWidget) -> None:
    """Startup only: one immediate focus plus a layout-settle screen clamp."""
    focus_main_window_at_launch(win)
    QtCore.QTimer.singleShot(200, lambda w=win: clamp_main_window_to_screen(w))

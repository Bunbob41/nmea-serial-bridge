"""Bring the main bridge window on-screen and to the foreground."""
from __future__ import annotations

import sys

from PySide6 import QtCore, QtGui, QtWidgets

_LAUNCH_FOCUS_ATTR = "_serial_link_launch_focus_done"
_CLAMP_TIMER_ATTR = "_serial_link_clamp_timer"


def _work_area_for_window(win: QtWidgets.QWidget) -> QtCore.QRect | None:
    """Pick the monitor work area that best overlaps the window frame."""
    frame = win.frameGeometry()
    app = QtWidgets.QApplication.instance()
    if app is None:
        return None

    best: QtCore.QRect | None = None
    best_area = 0
    for screen in app.screens():
        avail = screen.availableGeometry()
        inter = avail.intersected(frame)
        area = max(0, inter.width()) * max(0, inter.height())
        if area > best_area:
            best_area = area
            best = avail

    if best is not None:
        return best

    screen = win.screen() or app.primaryScreen()
    return screen.availableGeometry() if screen is not None else None


def clamp_main_window_to_screen(win: QtWidgets.QWidget) -> None:
    """Keep the window on a visible monitor without restoring minimize or stealing focus."""
    state = win.windowState()
    if state & (
        QtCore.Qt.WindowState.WindowMinimized
        | QtCore.Qt.WindowState.WindowMaximized
        | QtCore.Qt.WindowState.WindowFullScreen
    ):
        return
    if not win.isVisible():
        return

    available = _work_area_for_window(win)
    if available is None:
        return

    if win.width() > available.width() or win.height() > available.height():
        win.resize(
            min(win.width(), available.width()),
            min(win.height(), available.height()),
        )

    frame = win.frameGeometry()
    x = frame.x()
    y = frame.y()

    if frame.width() > available.width():
        x = available.left()
    else:
        if frame.right() > available.right():
            x = available.right() - frame.width() + 1
        if frame.left() < available.left():
            x = available.left()

    if frame.height() > available.height():
        y = available.top()
    else:
        if frame.bottom() > available.bottom():
            y = available.bottom() - frame.height() + 1
        if frame.top() < available.top():
            y = available.top()

    if x != frame.x() or y != frame.y():
        win.move(x, y)
        frame = win.frameGeometry()

    if not available.intersects(frame):
        frame.moveCenter(available.center())
        win.move(frame.topLeft())


def schedule_clamp_to_screen(win: QtWidgets.QWidget) -> None:
    """Debounce clamp so layout/state settle before we nudge the frame."""
    timer = getattr(win, _CLAMP_TIMER_ATTR, None)
    if timer is None:
        timer = QtCore.QTimer(win)
        timer.setSingleShot(True)
        timer.setInterval(50)
        timer.timeout.connect(lambda w=win: clamp_main_window_to_screen(w))
        setattr(win, _CLAMP_TIMER_ATTR, timer)
    timer.start()


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


def present_main_window(win: QtWidgets.QWidget) -> None:
    """Show from tray or after layout switch — restore and keep title bar on-screen."""
    win.showNormal()
    try:
        win.raise_()
    except Exception:
        pass
    try:
        win.activateWindow()
    except Exception:
        pass
    schedule_clamp_to_screen(win)
    QtCore.QTimer.singleShot(200, lambda w=win: clamp_main_window_to_screen(w))

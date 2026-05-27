"""System tray — keep bridge running when the window is closed (field monitoring)."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.app_icon import app_icon


def tray_available() -> bool:
    return QtWidgets.QSystemTrayIcon.isSystemTrayAvailable()


def install_tray_icon(win: QtWidgets.QWidget) -> Optional[QtWidgets.QSystemTrayIcon]:
    """Attach tray icon + menu; returns None if the OS has no tray."""
    if not tray_available():
        return None
    tray = QtWidgets.QSystemTrayIcon(win)
    icon = app_icon()
    if not icon.isNull():
        tray.setIcon(icon)
    tray.setToolTip("Serial Link — stopped")

    menu = QtWidgets.QMenu(win)
    act_show = menu.addAction("Show window")
    act_show.triggered.connect(lambda: show_main_window(win))
    menu.addSeparator()
    act_stop = menu.addAction("Stop bridge")
    act_stop.triggered.connect(win._request_stop_from_tray)
    menu.addSeparator()
    act_exit = menu.addAction("Exit")
    act_exit.triggered.connect(lambda: win._quit_application())
    tray.setContextMenu(menu)

    def _on_activated(reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QtWidgets.QSystemTrayIcon.ActivationReason.Trigger,
            QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            show_main_window(win)

    tray.activated.connect(_on_activated)
    tray.show()
    return tray


def show_main_window(win: QtWidgets.QWidget) -> None:
    win.showNormal()
    win.raise_()
    win.activateWindow()


def update_tray_tooltip(tray: Optional[QtWidgets.QSystemTrayIcon], text: str) -> None:
    if tray is None:
        return
    tray.setToolTip(text[:220])


def destroy_tray_icon(win: QtWidgets.QWidget) -> None:
    """Remove tray icon so QApplication can exit (tray alone keeps the process alive)."""
    tray = getattr(win, "_tray_icon", None)
    if tray is None:
        return
    tray.hide()
    tray.setContextMenu(None)
    tray.deleteLater()
    win._tray_icon = None  # type: ignore[attr-defined]

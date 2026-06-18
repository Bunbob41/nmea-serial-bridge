"""Tray helper smoke tests."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from PySide6 import QtWidgets

from ui.mixin import BridgeLogicMixin
from ui.tray_support import destroy_tray_icon, tray_available, update_tray_tooltip


class TestTraySupport(unittest.TestCase):
    def test_tray_available_is_bool(self) -> None:
        with patch.object(
            QtWidgets.QSystemTrayIcon,
            "isSystemTrayAvailable",
            return_value=True,
        ):
            self.assertTrue(tray_available())

    def test_update_tray_tooltip_noop_without_icon(self) -> None:
        update_tray_tooltip(None, "Serial Link — running")

    def test_destroy_tray_icon_clears_reference(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        win = QtWidgets.QWidget()
        tray = QtWidgets.QSystemTrayIcon(win)
        win._tray_icon = tray  # type: ignore[attr-defined]
        destroy_tray_icon(win)
        self.assertIsNone(getattr(win, "_tray_icon", "missing"))

    def test_quit_application_calls_stop_bridge(self) -> None:
        """Tray Exit must use stop_bridge(), not removed _stop_bridge()."""

        class _FakeWin:
            _force_quit = False
            _stats_popout_window = None
            stop_bridge_called = False

            def _is_bridge_running(self) -> bool:
                return True

            def stop_bridge(self) -> None:
                self.stop_bridge_called = True

            def _shutdown_background_services(self) -> None:
                pass

            def _close_auxiliary_windows(self) -> None:
                pass

            def close(self) -> None:
                pass

            def _request_application_quit(self) -> None:
                pass

        win = _FakeWin()
        with patch("ui.tray_support.destroy_tray_icon"):
            BridgeLogicMixin._quit_application(win)  # type: ignore[arg-type]
        self.assertTrue(win.stop_bridge_called)
        self.assertTrue(win._force_quit)


if __name__ == "__main__":
    unittest.main()

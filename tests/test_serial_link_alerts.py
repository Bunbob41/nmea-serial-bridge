"""Serial link disconnect alert helpers."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from PySide6 import QtWidgets

from ui.serial_link_alerts import (
    maybe_notify_serial_disconnect_tray,
    serial_disconnect_edge,
    should_tray_notify_serial_disconnect,
    sync_serial_control_card,
)


class TestSerialDisconnectEdge(unittest.TestCase):
    def test_open_to_reconnecting(self) -> None:
        self.assertTrue(serial_disconnect_edge("open", "reconnecting"))

    def test_ignores_other_transitions(self) -> None:
        self.assertFalse(serial_disconnect_edge("closed", "reconnecting"))
        self.assertFalse(serial_disconnect_edge("reconnecting", "open"))
        self.assertFalse(serial_disconnect_edge("open", "open"))


class TestSerialControlCard(unittest.TestCase):
    def test_reconnecting_shows_badge(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        card = QtWidgets.QFrame()
        badge = QtWidgets.QLabel()
        win = QtWidgets.QWidget()
        win._serial_control_card = card  # type: ignore[attr-defined]
        win._serial_link_status_badge = badge  # type: ignore[attr-defined]
        sync_serial_control_card(win, "reconnecting", com="COM7")
        self.assertEqual(card.property("serialLinkState"), "reconnecting")
        self.assertEqual(badge.text(), "Reconnecting…")
        self.assertTrue(badge.isVisible())

    def test_open_hides_badge(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        card = QtWidgets.QFrame()
        badge = QtWidgets.QLabel("Reconnecting…")
        badge.show()
        win = QtWidgets.QWidget()
        win._serial_control_card = card  # type: ignore[attr-defined]
        win._serial_link_status_badge = badge  # type: ignore[attr-defined]
        sync_serial_control_card(win, "open")
        self.assertFalse(badge.isVisible())


class TestTrayNotify(unittest.TestCase):
    def test_tray_when_minimized(self) -> None:
        win = MagicMock()
        win.isVisible.return_value = True
        win.isMinimized.return_value = True
        self.assertTrue(should_tray_notify_serial_disconnect(win))

    def test_no_tray_on_control_tab_when_visible(self) -> None:
        win = MagicMock()
        win.isVisible.return_value = True
        win.isMinimized.return_value = False
        win._modern_current_section_sid.return_value = "control"
        self.assertFalse(should_tray_notify_serial_disconnect(win))

    def test_tray_on_other_modern_tab(self) -> None:
        win = MagicMock()
        win.isVisible.return_value = True
        win.isMinimized.return_value = False
        win._modern_current_section_sid.return_value = "nmea"
        self.assertTrue(should_tray_notify_serial_disconnect(win))

    def test_maybe_notify_on_edge(self) -> None:
        tray = MagicMock()
        win = MagicMock()
        win._tray_icon = tray
        win._serial_disconnect_notify_mono = 0.0
        win.isVisible.return_value = False
        win.isMinimized.return_value = True
        maybe_notify_serial_disconnect_tray(
            win,
            prev_state="open",
            cur_state="reconnecting",
            com="COM7",
        )
        tray.showMessage.assert_called_once()


if __name__ == "__main__":
    unittest.main()

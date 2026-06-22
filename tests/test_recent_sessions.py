"""Recent session apply — NMEA mode and stop-first guard."""
from __future__ import annotations

import sys
import unittest
from unittest import mock

from PySide6 import QtGui, QtWidgets

from ui.mixin import BridgeLogicMixin


def _make_host() -> QtWidgets.QWidget:
    win = QtWidgets.QWidget()
    nmea_box = QtWidgets.QWidget(win)
    win.bridge = None
    win._starting = False
    win.com_cb = QtWidgets.QComboBox()
    win.com_cb.addItem("COM3")
    win.baud_edit = QtWidgets.QComboBox()
    win.baud_edit.setEditable(True)
    win.baud_edit.addItem("115200")
    win.udp_host = QtWidgets.QLineEdit()
    win.udp_port = QtWidgets.QLineEdit()
    win.rb_nmea_passthrough = QtWidgets.QRadioButton(nmea_box)
    win.rb_nmea_strict = QtWidgets.QRadioButton(nmea_box)
    win.rb_nmea_raw = QtWidgets.QRadioButton(nmea_box)
    win.rb_nmea_passthrough.setChecked(True)
    win._sync_log_hex_toggle = lambda: None
    win._refresh_nmea_status_chip = lambda: None
    win._log_ui = lambda _t: None
    return win


class TestRecentSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_apply_recent_session_sets_strict_nmea(self) -> None:
        host = _make_host()
        entry = {
            "com": "COM3",
            "baud": 115200,
            "udp_host": "0.0.0.0",
            "udp_port": "10110",
            "nmea_mode": "strict",
        }
        BridgeLogicMixin._apply_recent_session(host, entry)  # type: ignore[arg-type]
        self.assertTrue(host.rb_nmea_strict.isChecked())
        self.assertEqual(host.rb_nmea_passthrough.isChecked(), False)

    def test_recent_menu_trigger_passes_session_entry(self) -> None:
        host = _make_host()
        entry = {
            "com": "COM9",
            "baud": 9600,
            "udp_host": "127.0.0.1",
            "udp_port": "4001",
            "nmea_mode": "passthrough",
        }
        menu = QtWidgets.QMenu()
        act = QtGui.QAction("COM9 @ 9600", host)
        act.triggered.connect(
            lambda _checked=False, ent=entry: BridgeLogicMixin._apply_recent_session(  # type: ignore[arg-type]
                host, ent
            )
        )
        menu.addAction(act)
        act.trigger()
        self.assertEqual(host.com_cb.currentText(), "COM9")
        self.assertEqual(host.udp_host.text(), "127.0.0.1")
        self.assertEqual(host.udp_port.text(), "4001")

    def test_apply_recent_blocked_when_bridge_running(self) -> None:
        host = _make_host()
        host.bridge = object()
        with mock.patch.object(
            QtWidgets.QMessageBox, "information"
        ) as info:
            BridgeLogicMixin._apply_recent_session(  # type: ignore[arg-type]
                host,
                {"com": "COM3", "baud": 115200, "nmea_mode": "passthrough"},
            )
            info.assert_called_once()
            title = info.call_args[0][1]
            self.assertEqual(title, "Recent session")


if __name__ == "__main__":
    unittest.main()

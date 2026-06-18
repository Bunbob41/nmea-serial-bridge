"""Header status elision and web port unlock countdown."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from PySide6 import QtWidgets

from ui.header_status import ElidedStatusLabel
from ui.mixin import BridgeLogicMixin


class TestElidedStatusLabel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QtWidgets.QApplication.instance() is None:
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

    def test_elides_long_status_line(self) -> None:
        lbl = ElidedStatusLabel()
        lbl.resize(220, 24)
        msg = "Stopped - Pick a COM port and UDP settings, then Start."
        lbl.set_full_text(msg)
        self.assertEqual(lbl.full_text(), msg)
        self.assertLess(len(lbl.text()), len(msg))
        self.assertIn("Stopped", lbl.text())

    def test_shows_full_text_when_width_fits(self) -> None:
        lbl = ElidedStatusLabel()
        msg = "Stopped - Pick a COM port and UDP settings, then Start."
        lbl.set_full_text(msg)
        lbl.resize(900, 24)
        lbl.refresh_elide()
        self.assertEqual(lbl.text(), msg)


class TestWebPortUnlockCountdown(unittest.TestCase):
    def test_sync_chrome_shows_live_seconds(self) -> None:
        win = object.__new__(BridgeLogicMixin)
        win.chk_web_port_unlock = MagicMock()
        win.chk_web_port_unlock.isChecked.return_value = True
        win.lbl_web_port_status = QtWidgets.QLabel()
        win._web_port_unlock_seconds_left = 7
        BridgeLogicMixin._sync_web_port_unlock_chrome(win, True)
        self.assertIn("7s", win.lbl_web_port_status.text())


if __name__ == "__main__":
    unittest.main()
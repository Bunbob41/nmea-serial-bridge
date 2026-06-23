"""Header status elision and web port unlock countdown."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6 import QtCore, QtWidgets

from ui.header_status import ElidedStatusLabel
from ui.mixin import BridgeLogicMixin


class TestElidedStatusLabel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QtWidgets.QApplication.instance() is None:
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

    def test_keeps_stopped_title_when_narrow(self) -> None:
        lbl = ElidedStatusLabel()
        lbl.resize(48, 24)
        msg = "Stopped · Pick a COM port and UDP settings, then Start."
        lbl.set_full_text(msg)
        self.assertEqual(lbl.text(), "Stopped")

    def test_keeps_stopped_title_when_label_narrow_but_container_wide(self) -> None:
        container = QtWidgets.QWidget()
        container.setObjectName("modernHeaderStatusContainer")
        container.resize(520, 32)
        banner = QtWidgets.QFrame(container)
        banner.setObjectName("modernStatusBanner")
        banner.setGeometry(0, 0, 520, 30)
        lbl = ElidedStatusLabel(banner)
        lbl.resize(42, 24)
        msg = "Stopped · Set COM & UDP, then Start."
        lbl.set_full_text(msg)
        self.assertEqual(lbl.text(), "Stopped")

    def test_elides_long_status_line(self) -> None:
        lbl = ElidedStatusLabel()
        lbl.resize(220, 24)
        msg = "Stopped · Pick a COM port and UDP settings, then Start."
        lbl.set_full_text(msg)
        self.assertEqual(lbl.full_text(), msg)
        self.assertLess(len(lbl.text()), len(msg))
        self.assertIn("Stopped", lbl.text())

    def test_uses_container_width_when_label_is_still_laying_out(self) -> None:
        container = QtWidgets.QWidget()
        container.setObjectName("modernHeaderStatusContainer")
        container.resize(480, 32)
        lbl = ElidedStatusLabel(container)
        lbl.resize(0, 24)
        msg = "Stopped · Set COM & UDP, then Start."
        lbl.set_full_text(msg)
        lbl.refresh_elide()
        self.assertEqual(lbl.text(), "Stopped")

    def test_shows_full_text_when_label_is_wide_enough(self) -> None:
        lbl = ElidedStatusLabel()
        msg = "Stopped · Set COM & UDP, then Start."
        lbl.set_full_text(msg)
        lbl.resize(420, 24)
        lbl.refresh_elide()
        self.assertEqual(lbl.text(), msg)

    def test_shows_full_text_when_width_fits(self) -> None:
        lbl = ElidedStatusLabel()
        msg = "Stopped - Pick a COM port and UDP settings, then Start."
        lbl.set_full_text(msg)
        lbl.resize(900, 24)
        lbl.refresh_elide()
        self.assertEqual(lbl.text(), msg)

    def test_never_shows_partial_title_on_zero_width(self) -> None:
        lbl = ElidedStatusLabel()
        lbl.resize(1, 24)
        lbl.set_full_text("Stopped · Set COM & UDP, then Start.")
        lbl.refresh_elide()
        self.assertEqual(lbl.text(), "Stopped")
        self.assertNotIn("(", lbl.text())

    def test_deferred_elide_timers_cancel_on_delete(self) -> None:
        lbl = ElidedStatusLabel()
        lbl.set_full_text("Stopped · Pick a COM port and UDP settings, then Start.")
        lbl.deleteLater()
        QtWidgets.QApplication.processEvents()
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(150, loop.quit)
        loop.exec()
        QtWidgets.QApplication.processEvents()


class TestFileLogLocation(unittest.TestCase):
    def test_open_uses_active_file_log_path(self) -> None:
        win = object.__new__(BridgeLogicMixin)
        win._file_log = MagicMock()
        win._file_log.path = Path("C:/logs/bridge_survey.log")
        with patch.object(BridgeLogicMixin, "_reveal_path_in_file_manager") as reveal:
            BridgeLogicMixin._open_file_log_location(win)
            reveal.assert_called_once_with(win._file_log.path)

    def test_open_falls_back_to_path_field(self) -> None:
        win = object.__new__(BridgeLogicMixin)
        win._file_log = None
        win.file_log_path = MagicMock()
        win.file_log_path.text.return_value = "D:/data/session.log"
        with patch.object(BridgeLogicMixin, "_reveal_path_in_file_manager") as reveal:
            BridgeLogicMixin._open_file_log_location(win)
            reveal.assert_called_once_with("D:/data/session.log")


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
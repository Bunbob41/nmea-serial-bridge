"""Tests for main-window screen clamp."""
from __future__ import annotations

import unittest
from unittest import mock
from unittest.mock import MagicMock

from PySide6 import QtCore, QtWidgets

from ui import window_present


class TestWindowPresent(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not QtWidgets.QApplication.instance():
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

    def test_clamp_moves_frame_below_work_area_top(self) -> None:
        win = QtWidgets.QWidget()
        avail = QtCore.QRect(0, 40, 1920, 1040)
        frame = QtCore.QRect(100, -28, 900, 700)

        win.windowState = MagicMock(
            return_value=QtCore.Qt.WindowState.WindowNoState
        )
        win.isVisible = MagicMock(return_value=True)
        win.width = MagicMock(return_value=frame.width())
        win.height = MagicMock(return_value=frame.height())
        win.frameGeometry = MagicMock(return_value=QtCore.QRect(frame))
        win.move = MagicMock()
        win.resize = MagicMock()

        with mock.patch.object(
            window_present, "_work_area_for_window", return_value=avail
        ):
            window_present.clamp_main_window_to_screen(win)
        win.move.assert_called_once_with(100, 40)

    def test_clamp_skips_when_maximized(self) -> None:
        win = QtWidgets.QWidget()
        win.windowState = MagicMock(
            return_value=QtCore.Qt.WindowState.WindowMaximized
        )
        win.isVisible = MagicMock(return_value=True)
        win.move = MagicMock()
        window_present.clamp_main_window_to_screen(win)
        win.move.assert_not_called()


if __name__ == "__main__":
    unittest.main()
"""Mission Review layout helpers - path elision and chart bands."""
from __future__ import annotations

import unittest

from PySide6 import QtWidgets

from ui import mission_review
from ui.local_backup_settings import ElidedPathLabel, set_mission_session_path_label


class TestElidedPathLabel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QtWidgets.QApplication.instance() is None:
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

    def test_elides_long_windows_path(self) -> None:
        lbl = ElidedPathLabel()
        lbl.resize(180, 24)
        long_path = r"C:\Users\Operator\Projects\logs\2026-06-16_21-22\backup_20260617_1426.raw"
        lbl.set_full_path(long_path)
        self.assertEqual(lbl.full_path(), long_path)
        self.assertLess(len(lbl.text()), len(long_path))
        self.assertTrue(lbl.text().endswith("1426.raw"))

    def test_set_mission_session_path_label_enables_copy(self) -> None:
        class Win:
            pass

        win = Win()
        win._mission_session_path_label = ElidedPathLabel()
        win._mission_session_path_copy = QtWidgets.QToolButton()
        set_mission_session_path_label(win, r"C:\logs\session.raw")
        self.assertTrue(win._mission_session_path_copy.isEnabled())
        set_mission_session_path_label(win, "")
        self.assertFalse(win._mission_session_path_copy.isEnabled())


class TestMissionChartBands(unittest.TestCase):
    def test_title_band_clears_bar_area(self) -> None:
        self.assertGreaterEqual(mission_review._CHART_TITLE_BAND, 28)
        self.assertGreaterEqual(mission_review.ThroughputBarChart().minimumHeight(), 160)


if __name__ == "__main__":
    unittest.main()

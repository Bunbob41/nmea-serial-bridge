"""Mission Review layout helpers - path elision and chart bands."""
from __future__ import annotations

import unittest

from PySide6 import QtWidgets

from ui import mission_review
from ui.local_backup_settings import ElidedPathLabel, set_mission_session_path_label
from ui.mission_summary import _elide_path_middle


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


class TestMissionPathElision(unittest.TestCase):
    def test_middle_elide_keeps_ends(self) -> None:
        path = r"C:\Users\Morgan\Projects\udp-com-bridge\logs\2026-06-16_21-22\backup_20260619_0212.raw"
        short = _elide_path_middle(path, max_chars=40)
        self.assertIn("…", short)
        self.assertTrue(short.startswith(r"C:\Users"))
        self.assertTrue(short.endswith(".raw"))


class TestMissionChartBands(unittest.TestCase):
    def test_title_band_clears_bar_area(self) -> None:
        self.assertGreaterEqual(mission_review._CHART_TITLE_BAND, 20)
        chart = mission_review.ThroughputBarChart()
        self.assertLessEqual(chart.maximumHeight(), 120)
        chart.set_values([100])
        self.assertLessEqual(chart.height(), 88)

    def test_max_value_pill_helper_exists(self) -> None:
        self.assertTrue(callable(mission_review._draw_max_value_pill))


class TestModernNavOrdering(unittest.TestCase):
    def test_groups_stay_contiguous(self) -> None:
        from ui.tool_tabs import order_modern_tools_nav_names

        scrambled = ["Inject", "Hub", "NMEA", "Presets", "Activity", "Control"]
        ordered = order_modern_tools_nav_names(scrambled)
        self.assertEqual(ordered.index("Control"), 0)
        self.assertEqual(ordered.index("Activity"), 1)
        self.assertLess(ordered.index("Activity"), ordered.index("Presets"))
        self.assertEqual(len(ordered), len(scrambled))


if __name__ == "__main__":
    unittest.main()

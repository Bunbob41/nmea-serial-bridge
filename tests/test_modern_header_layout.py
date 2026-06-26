"""Multi-pass modern header layout planner."""
from __future__ import annotations

import unittest

from PySide6 import QtWidgets

from ui.modern_header_layout import (
    compact_status_display,
    measure_status_capsule_width,
    plan_header_layout,
)


class TestModernHeaderLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QtWidgets.QApplication.instance() is None:
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

    def test_compact_status_display_lowercase(self) -> None:
        self.assertEqual(compact_status_display("stopped", "Stopped"), "stopped")
        self.assertEqual(compact_status_display("running", "Running"), "running")

    def test_status_capsule_width_covers_stopped(self) -> None:
        lbl = QtWidgets.QLabel()
        width = measure_status_capsule_width(lbl, "stopped", include_dot=True)
        fm = lbl.fontMetrics()
        self.assertGreaterEqual(width, fm.horizontalAdvance("stopped") + 10)

    def test_plan_never_allocates_status_below_measured_text(self) -> None:
        cluster = QtWidgets.QWidget()
        lbl = QtWidgets.QLabel()
        plan = plan_header_layout(
            520,
            run_cluster=cluster,
            status_display="stopped",
            status_label=lbl,
            chips_labeled_w=480,
            chips_icon_w=220,
            trail_w=240,
            handle_width=1,
            chips_icon_only=False,
            chips_mode="labels",
        )
        need = measure_status_capsule_width(lbl, "stopped", include_dot=True)
        self.assertGreaterEqual(plan.sizes[1], need)
        from ui.modern_header_split import header_split_mins

        self.assertGreaterEqual(plan.sizes[2], header_split_mins()[2])

    def test_plan_compacts_start_when_tight(self) -> None:
        cluster = QtWidgets.QWidget()
        lbl = QtWidgets.QLabel()
        wide = plan_header_layout(
            1200,
            run_cluster=cluster,
            status_display="stopped",
            status_label=lbl,
            chips_labeled_w=600,
            chips_icon_w=240,
            trail_w=260,
            handle_width=1,
            chips_icon_only=False,
            chips_mode="auto",
        )
        tight = plan_header_layout(
            420,
            run_cluster=cluster,
            status_display="stopped",
            status_label=lbl,
            chips_labeled_w=600,
            chips_icon_w=240,
            trail_w=260,
            handle_width=1,
            chips_icon_only=False,
            chips_mode="auto",
        )
        self.assertLessEqual(tight.sizes[0], wide.sizes[0])
        self.assertTrue(tight.start_compact)
        self.assertIsNone(tight.force_chips_icon_only)


if __name__ == "__main__":
    unittest.main()

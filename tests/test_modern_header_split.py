"""Modern global header splitter sizing and chip scroll."""
from __future__ import annotations

import unittest

from PySide6 import QtWidgets

from ui.modern_header_split import ModernHeaderSplitter, header_split_mins
from ui.modern_tools_chips import (
    ModernToolsChipScrollArea,
    reveal_active_header_chip,
    snap_header_chip_scroll,
)


class TestModernHeaderSplit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_run_pane_min_fits_start_label(self) -> None:
        mins = header_split_mins()
        self.assertGreaterEqual(mins[0], 110)

    def test_set_clamped_sizes_gives_slack_to_chips_when_bar_grows(self) -> None:
        host = QtWidgets.QWidget()
        host.resize(900, 48)
        splitter = ModernHeaderSplitter(host)
        splitter.resize(900, 48)
        for _ in range(4):
            splitter.addWidget(QtWidgets.QWidget())
        splitter.set_clamped_sizes([106, 122, 755, 274])
        sizes = splitter.sizes()
        self.assertGreaterEqual(sizes[2], 400)
        self.assertGreater(sum(sizes), 850)

    def test_set_clamped_sizes_shrinks_trail_before_chips_when_tight(self) -> None:
        host = QtWidgets.QWidget()
        host.resize(780, 48)
        splitter = ModernHeaderSplitter(host)
        splitter.resize(780, 48)
        for _ in range(4):
            splitter.addWidget(QtWidgets.QWidget())
        splitter.set_clamped_sizes([106, 122, 755, 274])
        sizes = splitter.sizes()
        mins = header_split_mins()
        self.assertGreaterEqual(sizes[2], mins[2])
        self.assertGreaterEqual(sizes[2], 300)
        self.assertGreater(sum(sizes), 740)


class TestModernToolsChipScroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _make_rail(self, widths: list[int]) -> tuple[ModernToolsChipScrollArea, list[QtWidgets.QPushButton]]:
        scroll = ModernToolsChipScrollArea()
        scroll.resize(120, 32)
        inner = QtWidgets.QWidget()
        inner.setFixedHeight(30)
        lay = QtWidgets.QHBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        buttons: list[QtWidgets.QPushButton] = []
        for idx, width in enumerate(widths):
            btn = QtWidgets.QPushButton(f"C{idx}")
            btn.setFixedSize(width, 28)
            buttons.append(btn)
            lay.addWidget(btn)
        inner.setFixedWidth(sum(widths) + 4 * max(0, len(widths) - 1))
        scroll.setWidget(inner)
        self._app.processEvents()
        return scroll, buttons

    def test_reveal_resets_scroll_when_row_fits(self) -> None:
        scroll, buttons = self._make_rail([60, 60, 60])
        scroll.horizontalScrollBar().setValue(40)
        reveal_active_header_chip(scroll, buttons, buttons[2])
        self.assertEqual(scroll.horizontalScrollBar().value(), 0)

    def test_snap_removes_partial_chip_on_left_edge(self) -> None:
        scroll, buttons = self._make_rail([80, 80, 80, 80])
        scroll.horizontalScrollBar().setValue(37)
        snap_header_chip_scroll(scroll, buttons)
        self.assertEqual(scroll.horizontalScrollBar().value(), 0)

    def test_reveal_active_chip_without_clipping_first(self) -> None:
        scroll, buttons = self._make_rail([80, 80, 80, 80, 80])
        scroll.resize(180, 32)
        self._app.processEvents()
        reveal_active_header_chip(scroll, buttons, buttons[3])
        first_left = buttons[0].x() - scroll.horizontalScrollBar().value()
        self.assertGreaterEqual(first_left, 0)


if __name__ == "__main__":
    unittest.main()

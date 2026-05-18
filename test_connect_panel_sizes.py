"""Connect panel splitter: collapsed strips stay minimal; expanded sizes persist."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6 import QtWidgets

from ui import connect_panels, ui_prefs


def _mock_row(expanded: bool, *, hint_h: int = 72) -> MagicMock:
    row = MagicMock()
    btn = MagicMock()
    btn.isChecked.return_value = expanded
    row.tool_button.return_value = btn
    body = MagicMock()
    row.body_widget.return_value = body
    sh = MagicMock()
    sh.height.return_value = hint_h
    row.sizeHint.return_value = sh
    row.minimumSizeHint.return_value = sh
    return row


class _MockWin:
    def __init__(self, order: list[str], sizes: list[int], expanded: dict[str, bool]) -> None:
        self._ui_mode = "standard"
        self._connect_panel_order = order
        self._connect_panel_disclosures = {k: _mock_row(expanded[k]) for k in order}
        self._connect_panel_splitter = MagicMock()
        self._connect_panel_splitter.sizes.return_value = sizes


class ConnectPanelSizesTests(unittest.TestCase):
    def test_normalize_keeps_all_collapsed_state(self) -> None:
        order = list(connect_panels.CONNECT_PANEL_KEYS)
        collapsed = {k: True for k in order}
        out_c, out_s, use_def = connect_panels._normalize_connect_launch_prefs(
            collapsed, {"run": 26, "hint": 28}, order
        )
        self.assertTrue(all(out_c.get(k) for k in order))
        _ = use_def

    def test_splitter_content_height_includes_handles(self) -> None:
        splitter = MagicMock()
        splitter.handleWidth.return_value = 6
        h = connect_panels._splitter_content_height(splitter, [26, 26, 80])
        self.assertEqual(h, 26 + 26 + 80 + 12)

    def test_normalize_keeps_partial_collapse(self) -> None:
        order = ["run", "quick_log", "connection"]
        collapsed = {"quick_log": True}
        sizes = {"run": 80, "connection": 260}
        out_c, out_s, use_def = connect_panels._normalize_connect_launch_prefs(collapsed, sizes, order)
        self.assertTrue(out_c.get("quick_log"))
        self.assertEqual(out_s, sizes)
        self.assertFalse(use_def)

    def test_persist_skips_collapsed_panels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_connect_panel_prefs(
                    "standard",
                    ["run", "quick_log"],
                    {"quick_log": True},
                    sizes={"run": 200, "quick_log": 140},
                )
                win = _MockWin(
                    ["run", "quick_log"],
                    [26, 140],
                    {"run": False, "quick_log": True},
                )
                connect_panels._persist_connect_splitter_sizes(win)  # type: ignore[arg-type]
                loaded = ui_prefs.load_connect_panel_prefs("standard")
                self.assertEqual(loaded["sizes"].get("run"), 200)
                self.assertEqual(loaded["sizes"].get("quick_log"), 140)

    def test_capture_before_collapse_keeps_expanded_height(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_connect_panel_prefs("standard", ["quick_log"], {}, sizes={})
                win = _MockWin(["quick_log"], [180], {"quick_log": True})
                connect_panels._capture_expanded_size_from_splitter(win, "quick_log")  # type: ignore[arg-type]
                loaded = ui_prefs.load_connect_panel_prefs("standard")
                self.assertEqual(loaded["sizes"].get("quick_log"), 180)

    def test_single_expanded_panel_uses_zero_stretch(self) -> None:
        splitter = MagicMock()
        splitter.count.return_value = 3
        splitter.handleWidth.return_value = 8
        host = MagicMock()
        host_lay = MagicMock()
        host_lay.indexOf = MagicMock(return_value=0)
        tab_lay = MagicMock()
        tab_lay.indexOf = MagicMock(return_value=0)
        tab_lay.contentsMargins.return_value = MagicMock(
            top=MagicMock(return_value=0), bottom=MagicMock(return_value=0)
        )
        tab_lay.spacing.return_value = 0
        tab_lay.count.return_value = 1
        tab_lay.itemAt.return_value = None
        win = MagicMock()
        win._connect_panel_splitter = splitter
        win._connect_panel_host = host
        win._connect_panel_host_lay = host_lay
        win._connect_tab_layout = tab_lay
        win._connect_panel_scroll = MagicMock()
        win._connect_tab_widget = MagicMock()
        win._connect_panel_order = ["run", "hint", "quick_log"]
        win._connect_panel_disclosures = {
            "run": _mock_row(True),
            "hint": _mock_row(False),
            "quick_log": _mock_row(False),
        }
        win._ui_mode = "standard"
        with patch.object(
            connect_panels,
            "load_connect_panel_prefs",
            return_value={"collapsed": {"hint": True, "quick_log": True}, "sizes": {"run": 72}},
        ):
            connect_panels._apply_connect_splitter_sizes(win)
        for i in range(3):
            splitter.setStretchFactor.assert_any_call(i, 0)
        splitter.setFixedHeight.assert_not_called()
        splitter.setMinimumHeight.assert_called()
        sizes_arg = splitter.setSizes.call_args_list[-1][0][0]
        self.assertGreaterEqual(sizes_arg[0], 48)

    def test_target_row_height_uses_size_hint_floor(self) -> None:
        row = _mock_row(True, hint_h=40)
        h = connect_panels._target_row_height(row, "run", {})
        self.assertGreaterEqual(h, 48)

    def test_target_row_height_never_clips_natural_content(self) -> None:
        row = _mock_row(True, hint_h=150)
        h = connect_panels._target_row_height(row, "run", {"run": 60})
        self.assertEqual(h, 150)

    def test_apply_sizes_uses_strip_for_collapsed(self) -> None:
        splitter = MagicMock()
        splitter.count.return_value = 2
        splitter.height.return_value = 500
        splitter.handleWidth.return_value = 8
        host = MagicMock()
        tab = MagicMock()
        tab.height.return_value = 480
        host.parentWidget.return_value = tab
        margins = MagicMock()
        margins.top.return_value = 0
        margins.bottom.return_value = 0
        lay = MagicMock()
        lay.indexOf.return_value = 1
        lay.count.return_value = 3
        lay.contentsMargins.return_value = margins
        lay.spacing.return_value = 4
        lay.itemAt.return_value = None
        win = MagicMock()
        win._connect_tab_layout = lay
        win._connect_panel_splitter = splitter
        win._connect_panel_host = host
        win._connect_tab_layout = lay
        win._connect_panel_order = ["run", "quick_log"]
        win._connect_panel_disclosures = {
            "run": _mock_row(True),
            "quick_log": _mock_row(False),
        }
        win._ui_mode = "standard"
        with patch.object(
            connect_panels,
            "load_connect_panel_prefs",
            return_value={"collapsed": {"quick_log": True}, "sizes": {"run": 80}},
        ):
            connect_panels._apply_connect_splitter_sizes(win)
        sizes_arg = splitter.setSizes.call_args[0][0]
        self.assertEqual(sizes_arg[1], connect_panels._COLLAPSED_STRIP_HEIGHT)

    def test_default_collapsed_only_run_and_connection_open(self) -> None:
        self.assertFalse(connect_panels._default_collapsed("run"))
        self.assertFalse(connect_panels._default_collapsed("connection"))
        self.assertTrue(connect_panels._default_collapsed("hint"))
        self.assertTrue(connect_panels._default_collapsed("ntrip"))

    def test_splitter_target_uses_tab_height(self) -> None:
        host = MagicMock()
        tab = MagicMock()
        tab.height.return_value = 400
        host.parentWidget.return_value = tab
        splitter = MagicMock()
        splitter.handleWidth.return_value = 8
        margins = MagicMock()
        margins.top.return_value = 0
        margins.bottom.return_value = 0
        lay = MagicMock()
        lay.contentsMargins.return_value = margins
        lay.count.return_value = 2
        lay.itemAt.return_value = None
        lay.spacing.return_value = 4
        win = MagicMock()
        win._connect_panel_host = host
        win._connect_panel_splitter = splitter
        win._connect_tab_layout = lay
        order = ["run", "connection"]
        disclosures = {"run": _mock_row(True), "connection": _mock_row(True)}
        sizes = [72, 260]
        target = connect_panels._connect_splitter_target_height(win, order, disclosures, sizes)
        self.assertGreaterEqual(target, 220)
        self.assertLessEqual(target, 400)

    def test_panel_expanded_size_respects_cap(self) -> None:
        h = connect_panels._panel_expanded_size("run", {"run": 400})
        self.assertEqual(h, connect_panels._PANEL_EXPANDED_CAP["run"])

    def test_fit_window_no_longer_resizes(self) -> None:
        win = MagicMock()
        win.height.return_value = 520
        connect_panels._fit_window_to_connect_content(win)  # type: ignore[arg-type]
        win.resize.assert_not_called()

    def test_collapse_reflow_does_not_schedule_window_fit(self) -> None:
        host = MagicMock()
        splitter = MagicMock()
        splitter.handleWidth.return_value = 8
        scroll = MagicMock()
        lay = MagicMock()
        lay.indexOf.side_effect = lambda w: 1 if w is scroll else -1
        host_lay = MagicMock()
        host_lay.indexOf.return_value = 0
        win = MagicMock()
        win._connect_tab_layout = lay
        win._connect_panel_scroll = scroll
        win._connect_tab_widget = MagicMock()
        win._connect_panel_page = MagicMock()
        win._connect_page_in_main_scroll = True
        win._connect_panel_splitter = splitter
        win._connect_panel_host = host
        win._connect_panel_host_lay = host_lay
        win._connect_panel_order = ["run", "hint"]
        win._connect_panel_disclosures = {
            "run": _mock_row(False),
            "hint": _mock_row(False),
        }
        with patch.object(connect_panels, "schedule_fit_window_to_connect") as mock_fit:
            connect_panels._reflow_connect_panel_host(win, [26, 26])  # type: ignore[arg-type]
            mock_fit.assert_not_called()

    def test_sync_scroll_compact_height(self) -> None:
        scroll = MagicMock()
        page = MagicMock()
        tab = MagicMock()
        win = MagicMock()
        win._connect_panel_scroll = scroll
        win._connect_panel_page = page
        win._connect_tab_widget = tab
        win._connect_tab_layout = MagicMock()
        win._connect_panel_host = MagicMock()
        with patch.object(
            connect_panels, "_connect_tab_chrome_height", return_value=40
        ):
            connect_panels._sync_connect_panel_scroll_geometry(
                win, content_h=180, expanded_any=False
            )  # type: ignore[arg-type]
        scroll.setMinimumHeight.assert_called_with(180)
        scroll.setMaximumHeight.assert_called_with(180)
        tab.setMaximumHeight.assert_called()

    def test_sync_scroll_geometry_reapplies_when_signature_same(self) -> None:
        scroll = MagicMock()
        page = MagicMock()
        page.layout.return_value = QtWidgets.QVBoxLayout()
        tab = MagicMock()
        win = MagicMock()
        win._connect_panel_scroll = scroll
        win._connect_panel_page = page
        win._connect_tab_widget = tab
        win._connect_tab_layout = MagicMock()
        win._connect_panel_host = MagicMock()
        with patch.object(
            connect_panels, "_connect_tab_chrome_height", return_value=40
        ):
            connect_panels._sync_connect_panel_scroll_geometry(
                win, content_h=220, expanded_any=True
            )  # type: ignore[arg-type]
            first_calls = scroll.setMinimumHeight.call_count
            connect_panels._sync_connect_panel_scroll_geometry(
                win, content_h=220, expanded_any=True
            )  # type: ignore[arg-type]
        self.assertGreater(scroll.setMinimumHeight.call_count, first_calls)

    def test_expand_restores_short_window(self) -> None:
        win = MagicMock()
        win.height.return_value = 300
        win.minimumHeight.return_value = 380
        connect_panels._maybe_restore_connect_window_height(win)  # type: ignore[arg-type]
        win.resize.assert_called_once()
        self.assertGreaterEqual(win.resize.call_args[0][1], 380)

    def test_sync_connect_panel_layout_triggers_reflow(self) -> None:
        win = MagicMock()
        win._connect_panel_splitter = MagicMock()
        with patch.object(connect_panels, "_apply_connect_splitter_sizes") as apply_sizes, patch.object(
            connect_panels.QtCore.QTimer, "singleShot"
        ) as single_shot:
            connect_panels.sync_connect_panel_layout(win)  # type: ignore[arg-type]
            apply_sizes.assert_called()
            self.assertEqual(single_shot.call_count, 2)


if __name__ == "__main__":
    unittest.main()

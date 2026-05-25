"""Tab layout invariants (widget parenting, NMEA strict panel state)."""
from __future__ import annotations

import sys
import unittest

from PySide6 import QtWidgets


def _tab_page_containing(widget: QtWidgets.QWidget) -> QtWidgets.QWidget | None:
    w: QtWidgets.QWidget | None = widget
    while w is not None:
        parent = w.parentWidget()
        if parent is None:
            break
        if isinstance(parent, QtWidgets.QTabWidget):
            return w
        if isinstance(parent, QtWidgets.QStackedWidget):
            grand = parent.parentWidget()
            if isinstance(grand, QtWidgets.QTabWidget):
                return w
        w = parent
    return None


class TestUiTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_standard_advanced_net_on_connect_tab(self) -> None:
        from ui.standard import BridgeWindowStandard

        win = BridgeWindowStandard()
        tabs = win._main_tabs
        labels = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertIn("Connect", labels)
        connect_page = tabs.widget(labels.index("Connect"))
        self.assertIsNotNone(connect_page)
        self.assertIn("Log", labels)
        log_page = tabs.widget(labels.index("Log"))
        self.assertIsNotNone(log_page)
        self.assertIs(
            _tab_page_containing(win.chk_advanced_net),
            connect_page,
            "Advanced network must stay on Connect, not Presets",
        )
        if "Presets" in labels:
            presets_page = tabs.widget(labels.index("Presets"))
            self.assertIsNot(
                _tab_page_containing(win.chk_advanced_net),
                presets_page,
                "Advanced network must stay on Connect, not Presets",
            )

    def test_standard_has_theme_tab(self) -> None:
        from ui.standard import BridgeWindowStandard

        win = BridgeWindowStandard()
        tabs = win._main_tabs
        labels = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertIn("Log", labels)
        # "Theme" is now inside the Tools drawer, not a top-level tab
        self.assertIn("Tools", labels)
        tools_nav = getattr(win, "_tools_nav", None)
        self.assertIsNotNone(tools_nav, "_tools_nav sidebar must exist on Standard layout")
        nav_labels = [tools_nav.item(i).text() for i in range(tools_nav.count())]  # type: ignore[union-attr]
        self.assertIn("Theme", nav_labels)
        self.assertTrue(tabs.tabBar().isMovable())
        self.assertIs(_tab_page_containing(win.log_view), tabs.widget(labels.index("Log")))
        self.assertTrue(hasattr(win, "connect_mini_log"))
        self.assertTrue(hasattr(win, "connect_terminal_out"))
        self.assertTrue(hasattr(win, "_connect_panel_disclosures"))
        stack = getattr(win, "_connect_panel_stack", None)
        self.assertIsNotNone(stack)
        disclosures = getattr(win, "_connect_panel_disclosures", {})
        self.assertGreaterEqual(len(disclosures), 4)

    def test_field_advanced_net_on_presets_tab(self) -> None:
        from ui.field import BridgeWindowField

        win = BridgeWindowField()
        win._drawer_btn.setChecked(True)
        self._app.processEvents()
        tabs = win._drawer_tabs
        presets_page = tabs.widget(0)
        self.assertIs(
            _tab_page_containing(win.chk_advanced_net),
            presets_page,
            "Field layout exposes Advanced network under Tools → Presets",
        )
        labels = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertIn("Theme", labels)
        self.assertTrue(tabs.tabBar().isMovable())

    def test_preset_list_click_loads_when_stopped(self) -> None:
        from ui.standard import BridgeWindowStandard

        win = BridgeWindowStandard()
        win.show()
        self._app.processEvents()
        lst = win.preset_list
        self.assertGreaterEqual(lst.count(), 1)
        if lst.count() < 2:
            return
        second = win._preset_name_from_item(lst.item(1))
        win._on_preset_list_item_clicked(lst.item(1))
        self._app.processEvents()
        self.assertEqual(win._active_preset_name, second)
        self.assertEqual(lst.currentRow(), 1)
        self.assertTrue(win.btn_preset_load.isEnabled())

    def test_preset_named_one_loads(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import bench_config as bc
        from ui.standard import BridgeWindowStandard

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "path_presets.json"
            with patch.object(bc, "USER_PRESETS_PATH", path):
                bc.save_preset(
                    "1",
                    {
                        "com": "COM9",
                        "baud": 9600,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10111,
                    },
                )
                bc.save_preset(
                    "Boat / INS",
                    {
                        "com": "COM3",
                        "baud": 115200,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10110,
                        "pc_ip": "192.168.1.10",
                    },
                    boat_style=True,
                )
                win = BridgeWindowStandard()
                win.show()
                self._app.processEvents()
                one_item = win.preset_list.item(0)
                self.assertEqual(win._preset_name_from_item(one_item), "1")
                win._on_preset_list_item_clicked(one_item)
                self._app.processEvents()
                self.assertEqual(win._active_preset_name, "1")
                self.assertEqual(win.com_cb.currentText(), "COM9")
                self.assertEqual(win.udp_port.text(), "10111")

    def test_preset_buttons_disabled_while_running(self) -> None:
        from ui.standard import BridgeWindowStandard

        win = BridgeWindowStandard()
        win.show()
        self._app.processEvents()
        win._starting = False
        win.bridge = object()  # type: ignore[assignment]
        win._sync_preset_action_buttons()
        self.assertFalse(win.btn_preset_load.isEnabled())
        self.assertTrue(win.btn_preset_save_as.isEnabled())
        self.assertTrue(win.btn_preset_new.isEnabled())

    def test_quick_preset_starts_bridge_without_checklist(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        import bench_config as bc
        from ui.standard import BridgeWindowStandard

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "path_presets.json"
            with patch.object(bc, "USER_PRESETS_PATH", path):
                bc.save_preset(
                    "Bench",
                    {
                        "com": "COM7",
                        "baud": 115200,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10110,
                    },
                )
                win = BridgeWindowStandard()
                win.start_bridge = MagicMock()  # type: ignore[method-assign]
                win.stop_bridge = MagicMock()  # type: ignore[method-assign]
                with patch.object(win, "_diag_run_check_setup") as mock_check:
                    win._quick_connect_preset("Bench")
                    mock_check.assert_not_called()
                win.start_bridge.assert_called_once()
                self.assertEqual(win._active_preset_name, "Bench")

    def test_checklist_uses_active_saved_preset(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import bench_config as bc
        from ui.standard import BridgeWindowStandard

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "path_presets.json"
            with patch.object(bc, "USER_PRESETS_PATH", path):
                bc.save_preset(
                    "Alpha",
                    {
                        "com": "COM11",
                        "baud": 115200,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10115,
                    },
                )
                win = BridgeWindowStandard()
                win._set_active_preset("Alpha")
                args = win._diag_check_setup_args(production=False)
                self.assertIn("--port", args)
                self.assertIn("10115", args)
                self.assertIn("--com", args)
                self.assertIn("COM11", args)

    def test_boat_checklist_falls_back_from_desk_preset(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import bench_config as bc
        from ui.standard import BridgeWindowStandard

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "path_presets.json"
            with patch.object(bc, "USER_PRESETS_PATH", path):
                bc.save_preset(
                    "Desk test",
                    {
                        "com": "COM7",
                        "baud": 115200,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10110,
                    },
                )
                bc.save_preset(
                    "Boat / INS",
                    {
                        "com": "COM3",
                        "baud": 115200,
                        "udp_host": "0.0.0.0",
                        "udp_port": 10112,
                        "pc_ip": "192.168.1.10",
                    },
                    boat_style=True,
                )
                win = BridgeWindowStandard()
                win._set_active_preset("Desk test")
                args = win._diag_check_setup_args(production=True)
                self.assertIn("--production", args)
                self.assertIn("--host", args)
                self.assertIn("192.168.1.10", args)

    def test_field_intent_hint_visible_when_stopped(self) -> None:
        from ui.field import BridgeWindowField

        win = BridgeWindowField()
        win.show()
        self._app.processEvents()
        win._refresh_intent_hint()
        self._app.processEvents()
        self.assertTrue(win.intent_hint.text())
        self.assertTrue(win.intent_hint.toolTip())

    def test_nmea_strict_grid_disabled_by_default(self) -> None:
        from ui.standard import BridgeWindowStandard

        win = BridgeWindowStandard()
        box = win._nmea_strict_types_box
        self.assertIsNotNone(box)
        self.assertFalse(box.isEnabled())
        win.rb_nmea_strict.setChecked(True)
        win._sync_nmea_mode_ui()
        self.assertTrue(box.isEnabled())

    def test_stats_tick_handles_non_bridge_object(self) -> None:
        from ui.standard import BridgeWindowStandard

        win = BridgeWindowStandard()
        win.bridge = object()  # type: ignore[assignment]
        win._starting = False
        win._tick_stats()
        self._app.processEvents()
        self.assertTrue("Stopped" in win.lbl_stats.text())

    def test_status_chips_handle_non_bridge_object(self) -> None:
        from ui.standard import BridgeWindowStandard

        win = BridgeWindowStandard()
        win.bridge = object()  # type: ignore[assignment]
        win._refresh_nmea_status_chip()
        self._app.processEvents()
        self.assertTrue(bool(win.status_nmea.text().strip()))
        self.assertTrue(bool(win.status_gnss.text().strip()))


    def test_compact_intent_elides(self) -> None:
        from ui.controls import apply_compact_intent_hint

        lbl = QtWidgets.QLabel()
        lbl.resize(80, 20)
        long = (
            "Preset «Bench»: bridge owns COM7. Send UDP to 127.0.0.1:10110 (bench). "
            "Watch paired com0com, not COM7."
        )
        apply_compact_intent_hint(lbl, long)
        self.assertTrue(lbl.isVisible())
        self.assertEqual(lbl.toolTip(), long)
        self.assertLess(len(lbl.text()), len(long))


if __name__ == "__main__":
    unittest.main()

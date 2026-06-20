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
            if parent.objectName() == "modernSettingsStack":
                return w
            grand = parent.parentWidget()
            if isinstance(grand, QtWidgets.QTabWidget):
                return w
        w = parent
    return None


class TestUiTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_modern_theme_page_professional_controls(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        theme_idx = win._tools_section_index["theme"]
        theme_page = win._tools_stack.widget(theme_idx)
        self.assertEqual(theme_page.objectName(), "modernThemePage")
        self.assertTrue(hasattr(win, "cmb_theme_choice"))
        self.assertTrue(hasattr(win, "theme_zone_list"))
        self.assertFalse(hasattr(win, "btn_theme_randomize"))
        self.assertFalse(hasattr(win, "btn_theme_standardize"))
        self.assertFalse(hasattr(win, "chk_theme_seed_lock"))

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

    def test_preset_list_click_selects_without_loading_connect(self) -> None:
        from ui.field import BridgeWindowField

        win = BridgeWindowField()
        win.show()
        self._app.processEvents()
        lst = win.preset_list
        self.assertGreaterEqual(lst.count(), 1)
        if lst.count() < 2:
            return
        second_item = lst.item(1)
        second = win._preset_name_from_item(second_item)
        com_before = win.com_cb.currentText()
        lst.setCurrentItem(second_item)
        win._on_preset_list_item_clicked(second_item)
        self._app.processEvents()
        self.assertEqual(win._preset_editor_selection, second)
        self.assertTrue(win.btn_preset_load.isEnabled())
        self.assertEqual(win.com_cb.currentText(), com_before)

    def test_preset_named_one_loads(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import bench_config as bc
        from ui.field import BridgeWindowField

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
                win = BridgeWindowField()
                win.show()
                self._app.processEvents()
                one_item = win.preset_list.item(0)
                self.assertEqual(win._preset_name_from_item(one_item), "1")
                win.preset_list.setCurrentItem(one_item)
                win._preset_load_selected()
                self._app.processEvents()
                self.assertEqual(win._active_preset_name, "1")
                self.assertEqual(win.com_cb.currentText(), "COM9")
                self.assertEqual(win.udp_port.text(), "10111")

    def test_preset_buttons_disabled_while_running(self) -> None:
        from ui.field import BridgeWindowField

        win = BridgeWindowField()
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
        from ui.field import BridgeWindowField

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
                win = BridgeWindowField()
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
        from ui.field import BridgeWindowField

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
                win = BridgeWindowField()
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
        from ui.field import BridgeWindowField

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
                win = BridgeWindowField()
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
        full = win.intent_hint.text()
        self.assertTrue(full)
        if getattr(win, "_compact_intent_hint", False):
            self.assertEqual(win.intent_hint.toolTip(), full.strip())
        else:
            self.assertEqual(win.intent_hint.toolTip(), "")

    def test_nmea_strict_grid_disabled_by_default(self) -> None:
        from ui.field import BridgeWindowField

        win = BridgeWindowField()
        box = win._nmea_strict_types_box
        self.assertIsNotNone(box)
        win.rb_nmea_passthrough.setChecked(True)
        win._sync_nmea_mode_ui()
        self.assertFalse(box.isEnabled())
        win.rb_nmea_strict.setChecked(True)
        win._sync_nmea_mode_ui()
        self.assertTrue(box.isEnabled())

    def test_stats_tick_handles_non_bridge_object(self) -> None:
        from ui.field import BridgeWindowField

        win = BridgeWindowField()
        win.bridge = object()  # type: ignore[assignment]
        win._starting = False
        win._tick_stats()
        self._app.processEvents()
        self.assertTrue("Stopped" in win.lbl_stats.text())

    def test_status_chips_handle_non_bridge_object(self) -> None:
        from ui.field import BridgeWindowField

        win = BridgeWindowField()
        win.bridge = object()  # type: ignore[assignment]
        win._refresh_nmea_status_chip()
        self._app.processEvents()
        self.assertTrue(bool(win.status_nmea.text().strip()))
        self.assertTrue(bool(win.status_gnss.text().strip()))


    def test_modern_activity_tab_consolidates_traffic_view(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        self.assertIsNotNone(getattr(win, "_tools_stack", None))
        self.assertIsNotNone(getattr(win, "_modern_sidebar_scroll", None))
        activity_idx = win._tools_section_index["activity"]
        activity_page = win._tools_stack.widget(activity_idx)
        self.assertIsNotNone(activity_page)
        self.assertEqual(activity_page.objectName(), "modernLiveActivityPage")
        self.assertIs(_tab_page_containing(win.bridge_terminal._view), activity_page)
        self.assertTrue(hasattr(win, "log_view"))
        bar = win._survey_top_bar
        hidden = bar.hidden()
        for key in ("presets", "recent", "ui_editor", "copy_stats", "shortcuts"):
            self.assertIn(key, hidden)

    def test_modern_header_embeds_nav(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        lay = win.layout()
        self.assertIsInstance(lay, QtWidgets.QVBoxLayout)
        first = lay.itemAt(0).widget()
        self.assertEqual(first.objectName(), "modernGlobalHeader")
        nav = win.findChild(QtWidgets.QWidget, "modernHeaderNav")
        self.assertIsNotNone(nav)
        track = nav.findChild(QtWidgets.QWidget, "surveyTopBarTrack")
        self.assertIsNotNone(track)
        bar = win._survey_top_bar
        self.assertFalse(bar.isVisible())
        hdr = win._modern_global_header
        self.assertGreaterEqual(hdr.minimumHeight(), 40)
        win._ensure_modern_launch_layout()
        self.assertGreaterEqual(hdr.minimumHeight(), 40)

    def test_modern_tools_nav_sections(self) -> None:
        from ui.modern import BridgeWindowModern
        from ui.tool_tabs import build_modern_tools_nav

        win = BridgeWindowModern()
        # Ensure expanded so buttons show "icon  label" rather than icon-only
        if getattr(win, "_modern_sidebar_collapsed", True):
            win._apply_modern_sidebar_collapsed(False, persist=False)
        nav_spec = build_modern_tools_nav()
        labels = [btn.text().strip() for btn in win._tools_nav_buttons]
        self.assertEqual(len(labels), len(nav_spec))
        for _sid, label, icon in nav_spec:
            self.assertIn(f"{icon}  {label}", labels)
        joined = " ".join(labels)
        self.assertNotIn("More", joined)
        self.assertNotIn("Remote", joined)
        self.assertNotIn("Clear view", joined)
        self.assertEqual(len(labels), 13)
        self.assertIn("🎨  Theme", labels)
        self.assertNotIn("📖  Guide", joined)
        self.assertIn("🎛  Control", labels)
        self.assertIn("🛰  Hub", labels)
        self.assertIn("🔀  Fleet", labels)
        self.assertIn("📱  Dashboard", joined)
        checks_idx = win._tools_section_index["checks"]
        checks_page = win._tools_stack.widget(checks_idx)
        self.assertEqual(checks_page.objectName(), "modernChecksPage")
        output = getattr(win, "diag_output", None)
        self.assertIsNotNone(output)
        self.assertGreaterEqual(output.maximumHeight(), 1000)
        self.assertEqual(win._tools_section_index["inject"], labels.index("💉  Inject"))
        self.assertIn("guide", win._tools_section_index)
        control_idx = win._tools_section_index["control"]
        activity_idx = win._tools_section_index["activity"]
        self.assertEqual(activity_idx, labels.index("📋  Activity"))
        self.assertEqual(control_idx + 1, activity_idx)
        self.assertLess(
            activity_idx,
            win._tools_section_index["black_box"],
        )
        self.assertIn("theme", win._tools_section_index)
        theme_page = win._tools_stack.widget(win._tools_section_index["theme"])
        self.assertEqual(theme_page.objectName(), "modernThemePage")
        collapse_btn = getattr(win, "_modern_sidebar_collapse_btn", None)
        self.assertIsNotNone(collapse_btn)

    def test_modern_tools_nav_top_chips_mode(self) -> None:
        from ui.modern import BridgeWindowModern
        from ui.tool_tabs import build_modern_tools_nav

        win = BridgeWindowModern()
        nav_spec = build_modern_tools_nav()
        win._apply_modern_tools_nav_mode("sidebar", persist=False)
        self.assertEqual(win._modern_tools_nav_mode, "sidebar")
        self.assertTrue(win._modern_tools_chip_rail.isHidden())
        self.assertFalse(win._modern_sidebar_scroll.isHidden())

        win._apply_modern_tools_nav_mode("top_chips", persist=False)
        self.assertEqual(win._modern_tools_nav_mode, "top_chips")
        chip_sep = getattr(win, "_header_chip_sep", None)
        self.assertIsNotNone(chip_sep)
        self.assertIs(chip_sep.parentWidget(), win._header_chip_host)
        self.assertIs(chip_sep.window(), win)
        self.assertTrue(win._modern_tools_chip_rail.isHidden())
        self.assertFalse(win._header_chip_host.isHidden())
        inner = win._modern_tools_chip_inner
        scroll = win._modern_tools_chip_scroll
        self.assertIs(scroll.widget(), inner)
        self.assertIs(scroll.parentWidget(), win._header_chip_host)
        self.assertTrue(win._modern_sidebar_scroll.isHidden())
        rail_lbl = win.findChild(QtWidgets.QLabel, "modernToolsChipRailLabel")
        self.assertIsNotNone(rail_lbl)
        self.assertTrue(rail_lbl.isHidden())
        chip_labels = [str(btn.property("navLabel")) for btn in win._tools_chip_buttons]
        dropdowns = getattr(win, "_tools_chip_dropdowns", [])
        self.assertEqual(len(chip_labels), 6)
        self.assertNotIn("Theme", chip_labels)
        self.assertEqual(len(dropdowns), 2)
        tier_keys = {str(b.property("navTierKey")) for b in dropdowns}
        self.assertEqual(tier_keys, {"logging", "bench_tools"})
        self.assertIn("Activity", chip_labels)
        self.assertIn("Control", chip_labels)
        control_pos = chip_labels.index("Control")
        activity_pos = chip_labels.index("Activity")
        self.assertEqual(activity_pos, control_pos + 1)
        for _sid, label, icon in nav_spec:
            if _sid == "guide":
                continue
            if _sid in {"black_box", "file_log", "phone", "inject", "terminal", "checks"}:
                continue
            if _sid == "theme":
                continue
            self.assertIn(label, chip_labels)
            for btn in win._tools_chip_buttons:
                if str(btn.property("navLabel")) == label:
                    self.assertIn(icon, btn.text())
                    self.assertIn(label, btn.text())
                    break
            else:
                self.fail(f"chip for {label} not found")

        win._tools_nav_select(win._tools_section_index["presets"])
        preset_idx = win._tools_section_index["presets"]
        for btn in win._tools_chip_buttons:
            if int(btn.property("navIndex")) == preset_idx:
                self.assertEqual(str(btn.property("navActive")).lower(), "true")
                break
        else:
            self.fail("presets chip not found")

        win._apply_modern_tools_nav_mode("sidebar", persist=False)
        self.assertTrue(win._modern_tools_chip_rail.isHidden())
        self.assertFalse(win._modern_sidebar_scroll.isHidden())

    def test_modern_header_chips_keep_labels_and_scroll_when_narrow(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        win._apply_modern_tools_nav_mode("top_chips", persist=False)
        win._header_chips_icon_only = True
        win._sync_modern_header_chip_compression()
        self.assertFalse(win._header_chips_icon_only)
        for btn in win._tools_chip_buttons:
            icon = str(btn.property("navIcon") or "").strip()
            label = str(btn.property("navLabel") or "").strip()
            self.assertIn(icon, btn.text())
            self.assertIn(label, btn.text())

        bench_dd = next(
            b
            for b in win._tools_chip_dropdowns
            if str(b.property("navTierKey")) == "bench_tools"
        )
        child_sids = list(bench_dd.property("navChildSids"))
        self.assertIn("theme", child_sids)

    def test_modern_header_chips_launch_scroll_not_clipped(self) -> None:
        from PySide6 import QtCore

        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        win.resize(1200, 800)
        win._apply_modern_tools_nav_mode("top_chips", persist=False)
        win._restore_modern_header_split()
        self._app.processEvents()
        win._sync_modern_header_chip_scroll()
        scroll = win._modern_tools_chip_scroll
        self.assertEqual(scroll.horizontalScrollBar().value(), 0)
        control = next(
            b for b in win._tools_chip_buttons if str(b.property("navLabel")) == "Control"
        )
        self.assertIn("Control", control.text())
        vp_left = control.mapTo(scroll.viewport(), QtCore.QPoint(0, 0)).x()
        self.assertGreaterEqual(vp_left, 0)

    def test_modern_header_chips_icon_only_when_narrow(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        win._apply_modern_tools_nav_mode("top_chips", persist=False)
        win._apply_embedded_header_chip_styles()
        for btn in win._tools_chip_buttons:
            icon = str(btn.property("navIcon") or "").strip()
            label = str(btn.property("navLabel") or "").strip()
            self.assertIn(icon, btn.text())
            self.assertIn(label, btn.text())
            self.assertEqual(str(btn.property("headerIconOnly")).lower(), "false")

    def test_logging_indicator_reserves_header_trail_width(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        win._sync_modern_embedded_topbar_chrome()
        trail = win._header_pane_trail
        self.assertIsNotNone(trail)
        win._logging_indicator.hide()
        win._sync_header_trail_layout()
        hidden_min = trail.minimumWidth()
        win._logging_indicator.show()
        win._sync_header_trail_layout()
        self.assertGreater(win._header_trail_leading_width(), 0)
        self.assertGreater(trail.minimumWidth(), hidden_min)

    def test_modern_dropdown_chip_cycles_children(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        win._apply_modern_tools_nav_mode("top_chips", persist=False)
        logging_dd = next(
            b for b in win._tools_chip_dropdowns if str(b.property("navTierKey")) == "logging"
        )
        child_sids = list(logging_dd.property("navChildSids"))
        self.assertGreaterEqual(len(child_sids), 2)
        win._open_modern_section_by_sid(child_sids[0])
        self._app.processEvents()
        self.assertIn("Black box", logging_dd.text())
        win._cycle_modern_tools_dropdown("logging", child_sids)
        self._app.processEvents()
        self.assertEqual(
            win._tools_stack.currentIndex(),
            win._tools_section_index[child_sids[1]],
        )
        self.assertIn("File log", logging_dd.text())

    def test_modern_dashboard_nav_label(self) -> None:
        from ui.tool_tabs import build_modern_tools_nav

        nav = build_modern_tools_nav()
        phone = next((lbl, icon) for sid, lbl, icon in nav if sid == "phone")
        self.assertEqual(phone, ("Dashboard", "📱"))

    def test_modern_control_forms_stack_narrow(self) -> None:
        from ui.modern import BridgeWindowModern, CONTROL_FORMS_STACK_BELOW_W

        win = BridgeWindowModern()
        win._apply_control_forms_responsive(640)
        self.assertFalse(win._control_forms_vertical)

        win._apply_control_forms_responsive(CONTROL_FORMS_STACK_BELOW_W - 40)
        self.assertTrue(win._control_forms_vertical)
        grid = getattr(win, "_control_forms_grid", None)
        self.assertIsNotNone(grid)
        network_item = grid.itemAtPosition(1, 0)  # type: ignore[union-attr]
        self.assertIsNotNone(network_item)

        win._apply_control_forms_responsive(CONTROL_FORMS_STACK_BELOW_W + 40)
        self.assertFalse(win._control_forms_vertical)
        network_item = grid.itemAtPosition(0, 1)  # type: ignore[union-attr]
        self.assertIsNotNone(network_item)

    def test_phone_dashboard_stacks_narrow(self) -> None:
        from ui.modern import BridgeWindowModern
        from ui.tool_tabs import PHONE_CARDS_STACK_BELOW_W, apply_phone_dashboard_responsive

        win = BridgeWindowModern()
        apply_phone_dashboard_responsive(win, PHONE_CARDS_STACK_BELOW_W - 40)
        self.assertTrue(win._phone_cards_vertical)
        apply_phone_dashboard_responsive(win, PHONE_CARDS_STACK_BELOW_W + 80)
        self.assertFalse(win._phone_cards_vertical)

    def test_modern_control_page_chrome(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        ctrl_idx = win._tools_section_index["control"]
        ctrl_page = win._tools_stack.widget(ctrl_idx)
        self.assertEqual(ctrl_page.objectName(), "modernControlTab")
        self.assertIsNotNone(ctrl_page.findChild(QtWidgets.QFrame, "modernToolsPageHeader"))
        self.assertIsNotNone(getattr(win, "_control_preset_bar", None))
        self.assertEqual(win.intent_hint.objectName(), "modernToolsLiveStatus")

    def test_modern_fleet_page(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        fleet_idx = win._tools_section_index["fleet"]
        fleet_page = win._tools_stack.widget(fleet_idx)
        self.assertEqual(fleet_page.objectName(), "modernFleetTab")
        self.assertIsNotNone(fleet_page.findChild(QtWidgets.QTableWidget, "modernFleetTable"))
        self.assertIsNotNone(getattr(win, "_fleet_panel", None))

    def test_modern_hub_page_banner(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        hub_idx = win._tools_section_index["hub"]
        hub_page = win._tools_stack.widget(hub_idx)
        self.assertIsNotNone(hub_page.findChild(QtWidgets.QFrame, "modernToolsPageHeader"))
        hub = getattr(win, "connection_hub", None)
        self.assertIsNotNone(hub)
        self.assertIsNone(hub.findChild(QtWidgets.QLabel, "connectionHubTitle"))

    def test_modern_ui_editor_catalogs(self) -> None:
        from ui.modern import BridgeWindowModern
        from ui.ui_editor import UiEditorDialog

        from ui.tool_tabs import build_modern_tools_nav

        win = BridgeWindowModern()
        main = win._tab_catalog.get("main_tabs", {})
        tools = win._tab_catalog.get("tools_tabs", {})
        self.assertEqual(main, {})
        self.assertIn("Control", tools)
        self.assertIn("Hub", tools)
        self.assertIn("Fleet", tools)
        self.assertEqual(len(tools), len(build_modern_tools_nav()))

        dlg = UiEditorDialog(win)
        tab_names = [dlg._tabs.tabText(i) for i in range(dlg._tabs.count())]
        self.assertNotIn("Main tabs", tab_names)
        self.assertIn("Navigation", tab_names)
        self.assertNotIn("Connect", tab_names)
        self.assertIn("Header", tab_names)
        topbar_rows = [r.key for r in dlg._topbar_page._rows]
        self.assertEqual(topbar_rows, ["view", "hud", "ui_switch"])
        self.assertTrue(hasattr(win, "lbl_file_log_live_status"))
        self.assertTrue(hasattr(win, "lbl_presets_live_status"))
        file_log_page = win._tools_stack.widget(win._tools_section_index["file_log"])
        self.assertEqual(file_log_page.objectName(), "modernFileLogPage")
        activity_page = win._tools_stack.widget(win._tools_section_index["activity"])
        self.assertEqual(activity_page.objectName(), "modernLiveActivityPage")
        self.assertIsNotNone(getattr(win, "bridge_terminal", None))
        guide_page = win._tools_stack.widget(win._tools_section_index["guide"])
        guide_panel = guide_page.findChild(QtWidgets.QWidget, "operatorGuidePanel")
        self.assertIsNotNone(guide_panel)

    def test_modern_chip_rail_respects_saved_nav_order(self) -> None:
        from ui.modern import BridgeWindowModern
        from ui.ui_prefs import save_tab_order

        win = BridgeWindowModern()
        save_tab_order(
            "modern",
            "tools_tabs",
            ["NMEA", "Hub", "Control", "Presets"],
        )
        win._rebuild_modern_tools_nav_from_state("tools_tabs")
        labels = [
            btn.property("navLabel")
            for btn in getattr(win, "_tools_chip_buttons", [])
        ]
        self.assertEqual(labels, ["NMEA", "Hub", "Control", "Presets"])

    def test_modern_ui_editor_apply_keeps_chip_rail(self) -> None:
        from ui.modern import BridgeWindowModern
        from ui.ui_editor import UiEditorDialog
        from ui.ui_prefs import save_tab_order

        win = BridgeWindowModern()
        win._apply_modern_tools_nav_mode("top_chips", persist=False)
        save_tab_order(
            "modern",
            "tools_tabs",
            ["Terminal", "NMEA", "Hub", "Control", "Presets"],
        )
        dlg = UiEditorDialog(win)
        dlg._apply()
        self._app.processEvents()
        self.assertFalse(win._header_chip_host.isHidden())
        self.assertTrue(win._modern_tools_chip_rail.isHidden())
        self.assertGreater(
            len(win._tools_chip_buttons) + len(win._tools_chip_dropdowns),
            0,
        )

    def test_modern_open_full_map_handler(self) -> None:
        from unittest.mock import patch

        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        self.assertTrue(callable(getattr(win, "_on_web_open_dashboard_map", None)))
        opened: list[str] = []

        def _fake() -> None:
            opened.append("yes")

        with patch.object(win, "_on_web_open_dashboard_map", side_effect=_fake):
            win.control_position_map.open_full_map_requested.emit()
        self.assertEqual(opened, ["yes"])

    def test_modern_control_has_position_map(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        widget = getattr(win, "control_position_map", None)
        self.assertIsNotNone(widget)
        self.assertEqual(widget.objectName(), "modernControlMap")
        widget.update_position(lat=40.7128, lon=-74.0060, quality=1, fix_label="GPS")
        self._app.processEvents()

    def test_modern_header_status_banner_opens_control(self) -> None:
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QMouseEvent

        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        self.assertTrue(bool(win.status_banner.property("clickable")))
        filt = getattr(win, "_modern_status_banner_click_filter", None)
        self.assertIsNotNone(filt)
        win._open_modern_section_by_sid("activity")
        pos = win.status_banner.rect().center()
        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        filt.eventFilter(win.status_banner, release)
        self._app.processEvents()
        self.assertEqual(win._tools_stack.currentIndex(), win._tools_section_index["control"])

    def test_modern_header_guide_opens_guide(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        self.assertIsNone(getattr(win, "_floating_guide", None))
        win._open_modern_section_by_sid("control")
        win._open_modern_section_by_sid("guide")
        self._app.processEvents()
        self.assertEqual(win._tools_stack.currentIndex(), win._tools_section_index["guide"])

    def test_modern_header_status_banner_content_width(self) -> None:
        from PySide6.QtWidgets import QSizePolicy

        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        win._apply_modern_tools_nav_mode("top_chips", persist=False)
        self.assertEqual(
            win.status_banner.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Preferred,
        )
        win._set_status_banner("stopped", "Short", "")
        self._app.processEvents()
        short_hint = win.status_banner_text.sizeHint().width()
        short_w = win._header_status_container.width()
        win._set_status_banner(
            "stopped",
            "Stopped · Pick a COM port and UDP settings, then Start.",
            "",
        )
        self._app.processEvents()
        long_hint = win.status_banner_text.sizeHint().width()
        long_text = win.status_banner_text.text()
        self.assertGreater(long_hint, short_hint)
        self.assertIn("Stopped", long_text)
        splitter = getattr(win, "_header_splitter", None)
        self.assertIsNotNone(splitter)
        self.assertEqual(splitter.count(), 4)

    def test_modern_header_phone_opens_dashboard(self) -> None:
        from unittest.mock import patch

        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        opened: list[str] = []

        def _fake_open() -> None:
            opened.append("yes")

        with patch.object(win, "_on_web_open_dashboard", side_effect=_fake_open):
            win._btn_header_phone_qr.click()
        self.assertEqual(opened, ["yes"])

    def test_modern_shipped_view_menu_is_trimmed(self) -> None:
        import sys
        from unittest.mock import patch

        from ui.modern import BridgeWindowModern

        def _menu_labels(menu: QtWidgets.QMenu) -> list[str]:
            out: list[str] = []
            for act in menu.actions():
                if act.isSeparator():
                    continue
                if isinstance(act, QtWidgets.QWidgetAction):
                    widget = act.defaultWidget()
                    if widget is not None:
                        lbl = widget.findChild(QtWidgets.QLabel, "viewMenuActionLabel")
                        if lbl is not None:
                            out.append(lbl.text().replace("&", "").strip())
                            continue
                text = act.text().replace("&", "").strip()
                if text:
                    out.append(text)
            return out

        with patch.object(sys, "frozen", True, create=True):
            win = BridgeWindowModern()
            menu = win._topbar_widgets["view"].menu()
            self.assertIsNotNone(menu)
            labels = _menu_labels(menu)
        self.assertIn("Full screen", labels)
        self.assertNotIn("Save UI as product default…", labels)
        self.assertNotIn("Reset top bar layout", labels)
        self.assertNotIn("Show all top bar chips", labels)
        self.assertNotIn("Move top bar to bottom", labels)
        self.assertTrue(any("UI editor" in label for label in labels))
        self.assertTrue(any("Reset UI to product default" in label for label in labels))
        self.assertTrue(any("Standard" in label for label in labels))

    def test_open_hud_single_window_modern(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        win.show()
        self._app.processEvents()
        win._open_hud()
        self._app.processEvents()
        self.assertIsNotNone(win._stats_popout_window)
        self.assertIsNone(win._dashboard_window)

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

    def test_bridge_stats_show_live_traffic(self) -> None:
        from ui.modern import bridge_stats_show_live_traffic

        self.assertFalse(bridge_stats_show_live_traffic({}))
        self.assertFalse(bridge_stats_show_live_traffic({"hz_down": 0, "lines_up": 0}))
        self.assertTrue(bridge_stats_show_live_traffic({"hz_down": 1.2}))
        self.assertTrue(bridge_stats_show_live_traffic({"lines_up": 3}))

    def test_smart_peek_switches_to_control_on_traffic(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        win._smart_peek_pending = True
        win._open_modern_section_by_sid("activity")
        self.assertEqual(win._modern_current_section_sid(), "activity")
        win._maybe_finish_smart_peek({"hz_down": 2.0, "lines_down": 4})
        self._app.processEvents()
        self.assertFalse(win._smart_peek_pending)
        self.assertEqual(win._modern_current_section_sid(), "control")

    def test_smart_peek_skips_control_if_user_left_activity(self) -> None:
        from ui.modern import BridgeWindowModern

        win = BridgeWindowModern()
        win._smart_peek_pending = True
        win._open_modern_section_by_sid("hub")
        win._maybe_finish_smart_peek({"hz_up": 1.0})
        self._app.processEvents()
        self.assertFalse(win._smart_peek_pending)
        self.assertEqual(win._modern_current_section_sid(), "hub")


if __name__ == "__main__":
    unittest.main()

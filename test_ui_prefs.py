"""ui_prefs.json — recent sessions and minimal drawer persistence."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ui import ui_prefs


class TestUiPrefs(unittest.TestCase):
    def test_push_recent_session_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                base = {
                    "com": "COM7",
                    "baud": 115200,
                    "net_mode": "udp_listen",
                    "udp_host": "0.0.0.0",
                    "udp_port": 10110,
                    "nmea_mode": "passthrough",
                }
                ui_prefs.push_recent_session(dict(base))
                ui_prefs.push_recent_session({**base, "nmea_mode": "strict"})
                sessions = ui_prefs.load_recent_sessions()
                self.assertEqual(len(sessions), 2)
                ui_prefs.push_recent_session(dict(base))
                sessions = ui_prefs.load_recent_sessions()
                self.assertEqual(len(sessions), 2)
                self.assertEqual(sessions[0]["nmea_mode"], "passthrough")

    def test_minimal_prefs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_minimal_prefs({"tools_open": True})
                loaded = ui_prefs.load_minimal_prefs()
                self.assertTrue(loaded["tools_open"])
                raw = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("minimal", raw)

    def test_recent_sessions_reorder_and_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.push_recent_session(
                    {
                        "com": "COM1",
                        "baud": 115200,
                        "net_mode": "udp_listen",
                        "udp_host": "0.0.0.0",
                        "udp_port": 10110,
                        "nmea_mode": "passthrough",
                    }
                )
                ui_prefs.push_recent_session(
                    {
                        "com": "COM2",
                        "baud": 115200,
                        "net_mode": "udp_listen",
                        "udp_host": "0.0.0.0",
                        "udp_port": 10111,
                        "nmea_mode": "strict",
                    }
                )
                entries = ui_prefs.load_recent_sessions()
                keys = [ui_prefs.recent_session_key(e) for e in entries]
                self.assertEqual(len(keys), 2)
                self.assertTrue(ui_prefs.set_recent_session_pinned(keys[1], True))
                reordered = [keys[0], keys[1]]
                self.assertTrue(ui_prefs.reorder_recent_sessions(reordered))
                out = ui_prefs.load_recent_sessions()
                self.assertEqual(ui_prefs.recent_session_key(out[0]), keys[0])
                self.assertTrue(bool(out[1].get("pinned", False)))

    def test_tab_order_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_tab_order("standard", "main_tabs", ["Connect", "Theme", "Presets"])
                loaded = ui_prefs.load_tab_order("standard", "main_tabs")
                self.assertEqual(loaded, ["Connect", "Theme", "Presets"])

    def test_tab_order_terminal_kept_when_inject_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs._write_json(
                    {
                        "tab_order": {
                            "standard": {
                                "tools_tabs": [
                                    "Guide",
                                    "Terminal",
                                    "Inject",
                                    "Theme",
                                ]
                            }
                        }
                    }
                )
                loaded = ui_prefs.load_tab_order("standard", "tools_tabs")
                self.assertEqual(loaded, ["Guide", "Terminal", "Inject", "Theme"])

    def test_tab_order_legacy_terminal_maps_to_inject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs._write_json(
                    {
                        "tab_order": {
                            "standard": {"tools_tabs": ["Presets", "Terminal", "Theme"]}
                        }
                    }
                )
                loaded = ui_prefs.load_tab_order("standard", "tools_tabs")
                self.assertEqual(loaded, ["Presets", "Inject", "Theme"])

    def test_save_tab_order_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_tab_order(
                    "standard",
                    "tools_tabs",
                    ["Inject", "Theme", "Inject", "NMEA"],
                )
                loaded = ui_prefs.load_tab_order("standard", "tools_tabs")
                self.assertEqual(loaded, ["Inject", "Theme", "NMEA"])

    def test_diag_card_sizes_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_diag_card_sizes(
                    "field",
                    {"screen_log": 72, "automated_checks": 300},
                )
                loaded = ui_prefs.load_diag_card_sizes("field")
                self.assertEqual(loaded["screen_log"], 72)
                self.assertEqual(loaded["automated_checks"], 300)

    def test_diag_card_order_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_diag_card_order(
                    "standard",
                    ["automated_checks", "file_log", "quick_ui_switch"],
                )
                loaded = ui_prefs.load_diag_card_order("standard")
                self.assertEqual(loaded, ["automated_checks", "file_log", "quick_ui_switch"])

    def test_hidden_tabs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_hidden_tabs("standard", "main_tabs", ["Diagnostics", "Theme"])
                loaded = ui_prefs.load_hidden_tabs("standard", "main_tabs")
                self.assertEqual(loaded, ["Diagnostics", "Theme"])

    def test_hidden_tabs_tools_tabs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_hidden_tabs("field", "tools_tabs", ["Theme", "Guide"])
                loaded = ui_prefs.load_hidden_tabs("field", "tools_tabs")
                self.assertEqual(loaded, ["Theme", "Guide"])

    def test_file_log_prefs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_file_log_prefs(25, 10)
                loaded = ui_prefs.load_file_log_prefs()
                self.assertEqual(loaded, {"max_mb": 25, "backups": 10})

    def test_local_backup_prefs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_local_backup_prefs(enabled=False)
                loaded = ui_prefs.load_local_backup_prefs()
                self.assertEqual(loaded, {"enabled": False})

    def test_web_ui_defaults_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                loaded = ui_prefs.load_web_ui_prefs()
                self.assertTrue(loaded["enabled"])

    def test_web_dashboard_layout_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_web_dashboard_layout(
                    layout_mode="gridstack",
                    local_storage={
                        "nmea-gridstack-layout-v2": '[{"id":"log"}]',
                        "nmea-bridge-web-token": "must-strip",
                    },
                )
                loaded = ui_prefs.load_web_dashboard_layout()
                self.assertEqual(loaded["layout_mode"], "gridstack")
                self.assertIn("nmea-gridstack-layout-v2", loaded["local_storage"])
                self.assertNotIn("nmea-bridge-web-token", loaded["local_storage"])

    def test_web_ui_migration_enables_missing_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            path.write_text('{"schema_version": 2}', encoding="utf-8")
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                loaded = ui_prefs.load_web_ui_prefs()
                self.assertTrue(loaded["enabled"])

    def test_file_log_prefs_accepts_zero_backups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_file_log_prefs(50, 0)
                loaded = ui_prefs.load_file_log_prefs()
                self.assertEqual(loaded, {"max_mb": 50, "backups": 0})

    def test_connect_panel_prefs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_connect_panel_prefs(
                    "standard",
                    ["run", "quick_terminal", "quick_log", "connection"],
                    {"quick_log": True},
                    sizes={"quick_log": 140, "connection": 300},
                    toolbar_order=["reset_sizes", "ui_editor", "expand_all", "collapse_all"],
                )
                loaded = ui_prefs.load_connect_panel_prefs("standard")
                self.assertEqual(loaded["order"][:4], ["run", "quick_terminal", "quick_log", "connection"])
                self.assertTrue(loaded["collapsed"].get("quick_log"))
                self.assertNotIn("ntrip", loaded["order"])
                self.assertEqual(loaded["sizes"].get("connection"), 300)
                self.assertNotIn("reset_sizes", loaded["toolbar_order"])
                self.assertEqual(loaded["toolbar_order"][0], "ui_editor")

    def test_bench_setup_prefs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_bench_setup_prefs(hide_dialog=True)
                loaded = ui_prefs.load_bench_setup_prefs()
                self.assertTrue(loaded["hide_dialog"])

    def test_ntrip_prefs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_ntrip_prefs(
                    {
                        "enabled": True,
                        "caster": "caster:2101",
                        "mountpoint": "BASE",
                        "username": "u",
                        "password": "p",
                    }
                )
                loaded = ui_prefs.load_ntrip_prefs()
                self.assertFalse(loaded["enabled"])
                self.assertEqual(loaded["mountpoint"], "BASE")

    def test_top_bar_prefs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_top_bar_prefs(
                    "standard",
                    {
                        "order": ["view", "presets", "recent"],
                        "hidden": ["recent"],
                        "shortcuts_visible": True,
                        "position": "bottom",
                    },
                )
                loaded = ui_prefs.load_top_bar_prefs("standard")
                self.assertEqual(loaded["order"], ["view", "presets", "recent"])
                self.assertEqual(loaded["hidden"], ["recent"])
                self.assertTrue(loaded["shortcuts_visible"])
                self.assertEqual(loaded["position"], "bottom")

    def test_schema_written_on_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_minimal_prefs({"tools_open": True})
                raw = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(raw.get("schema_version"), ui_prefs.PREFS_SCHEMA_VERSION)

    def test_malformed_json_recovers_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            path.write_text("{bad json", encoding="utf-8")
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                loaded = ui_prefs.load_minimal_prefs()
                self.assertIn("tools_open", loaded)
                raw = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(raw.get("schema_version"), ui_prefs.PREFS_SCHEMA_VERSION)

    def test_connect_panel_order_migrates_legacy_factory_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            legacy = {
                "schema_version": ui_prefs.PREFS_SCHEMA_VERSION,
                "connect_panels": {
                    "standard": {
                        "order": list(ui_prefs._LEGACY_CONNECT_PANEL_ORDER),
                        "collapsed": {},
                        "sizes": {},
                        "hidden": [],
                    }
                },
            }
            path.write_text(json.dumps(legacy), encoding="utf-8")
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                loaded = ui_prefs.load_connect_panel_prefs("standard")
                self.assertEqual(loaded["order"], list(ui_prefs._CONNECT_PANEL_DEFAULT_ORDER))

    def test_connect_toolbar_order_migrates_for_old_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            old = {
                "schema_version": 1,
                "connect_panels": {
                    "standard": {
                        "order": ["run", "connection"],
                        "collapsed": {},
                        "sizes": {},
                        "hidden": [],
                    }
                },
            }
            path.write_text(json.dumps(old), encoding="utf-8")
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                loaded = ui_prefs.load_connect_panel_prefs("standard")
                self.assertIn("toolbar_order", loaded)
                self.assertTrue(loaded["toolbar_order"])
                raw = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(raw.get("schema_version"), ui_prefs.PREFS_SCHEMA_VERSION)

    def test_mixin_imports_field_and_logfirst_prefs(self) -> None:
        """Regression: Field layout must load log prefs without NameError."""
        from ui import mixin

        for name in (
            "load_field_prefs",
            "save_field_prefs",
            "load_logfirst_prefs",
            "save_logfirst_prefs",
        ):
            self.assertTrue(hasattr(mixin, name), name)


if __name__ == "__main__":
    unittest.main()

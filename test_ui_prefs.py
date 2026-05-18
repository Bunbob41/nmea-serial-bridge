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

    def test_file_log_prefs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_file_log_prefs(25, 10)
                loaded = ui_prefs.load_file_log_prefs()
                self.assertEqual(loaded, {"max_mb": 25, "backups": 10})

    def test_connect_panel_prefs_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_connect_panel_prefs(
                    "standard",
                    ["run", "quick_terminal", "quick_log", "connection"],
                    {"ntrip": True, "quick_log": False},
                    sizes={"quick_log": 140, "connection": 300},
                    toolbar_order=["reset_sizes", "ui_editor", "expand_all", "collapse_all"],
                )
                loaded = ui_prefs.load_connect_panel_prefs("standard")
                self.assertEqual(loaded["order"][:4], ["run", "quick_terminal", "quick_log", "connection"])
                self.assertTrue(loaded["collapsed"].get("ntrip"))
                self.assertFalse(loaded["collapsed"].get("quick_log"))
                self.assertEqual(loaded["sizes"].get("connection"), 300)
                self.assertEqual(loaded["toolbar_order"][0], "reset_sizes")

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
                self.assertTrue(loaded["enabled"])
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

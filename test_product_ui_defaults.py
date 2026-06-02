"""Tests for product UI defaults (layout chrome only)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from product_ui_defaults import (
    PRODUCT_UI_FILENAME,
    apply_product_ui_defaults_to_user,
    capture_ui_layout_snapshot_from_user_profile,
    default_ui_layout_id,
    load_merged_product_ui_defaults,
    sanitize_ui_prefs_for_product_export,
    seed_user_ui_prefs_if_missing,
)
from ui.registry import UI_STANDARD


class TestProductUiDefaults(unittest.TestCase):
    def test_sanitize_strips_web_dashboard_token_storage(self) -> None:
        raw = {
            "web_dashboard": {
                "layout_mode": "gridstack",
                "local_storage": {
                    "nmea-bridge-web-token": "secret",
                    "nmea-gridstack-layout-v2": "[]",
                },
            },
        }
        clean = sanitize_ui_prefs_for_product_export(raw)
        ls = clean["web_dashboard"]["local_storage"]
        self.assertNotIn("nmea-bridge-web-token", ls)
        self.assertIn("nmea-gridstack-layout-v2", ls)

    def test_sanitize_strips_machine_phone_url(self) -> None:
        raw = {"web_ui": {"phone_base_url": "http://100.1.2.3:10110", "port": 10110}}
        clean = sanitize_ui_prefs_for_product_export(raw)
        self.assertNotIn("phone_base_url", clean["web_ui"])

    def test_sanitize_strips_operator_keys(self) -> None:
        raw = {
            "recent_sessions": [{"com": "COM7"}],
            "last_known_good": {"x": 1},
            "terminal_ping": {"host": "1.2.3.4"},
            "web_ui": {"token": "secret", "port": 8765},
            "connect_layout": {"order": ["run"]},
        }
        clean = sanitize_ui_prefs_for_product_export(raw)
        self.assertNotIn("recent_sessions", clean)
        self.assertNotIn("last_known_good", clean)
        self.assertNotIn("terminal_ping", clean)
        self.assertEqual(clean["web_ui"], {"port": 8765})
        self.assertEqual(clean["connect_layout"], {"order": ["run"]})

    def test_default_ui_is_standard(self) -> None:
        with mock.patch(
            "product_ui_defaults.load_merged_product_ui_defaults",
            return_value={"ui": "standard", "ui_prefs": {}},
        ):
            self.assertEqual(default_ui_layout_id(), UI_STANDARD)

    def test_merge_local_overrides_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / PRODUCT_UI_FILENAME
            local = root / "product_ui_defaults.local.json"
            base.write_text(
                json.dumps({"ui": "standard", "ui_prefs": {"a": 1}}),
                encoding="utf-8",
            )
            local.write_text(
                json.dumps({"ui_prefs": {"b": 2}}),
                encoding="utf-8",
            )
            with mock.patch("product_ui_defaults.product_defaults_roots", return_value=[root]):
                merged = load_merged_product_ui_defaults()
            self.assertEqual(merged["ui"], "standard")
            self.assertEqual(merged["ui_prefs"]["a"], 1)
            self.assertEqual(merged["ui_prefs"]["b"], 2)

    def test_seed_writes_ui_choice_when_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            prefs_path = cfg / "ui_prefs.json"
            choice_path = cfg / "ui_choice.json"
            with (
                mock.patch("ui.ui_prefs.CONFIG_PATH", prefs_path),
                mock.patch("ui.picker.CONFIG_PATH", choice_path),
                mock.patch(
                    "product_ui_defaults.load_merged_product_ui_defaults",
                    return_value={"ui": "standard", "ui_prefs": {}},
                ),
            ):
                self.assertTrue(seed_user_ui_prefs_if_missing())
                self.assertTrue(choice_path.is_file())
                data = json.loads(choice_path.read_text(encoding="utf-8"))
                self.assertEqual(data.get("ui"), UI_STANDARD)

    def test_apply_writes_prefs_and_choice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            prefs_path = cfg / "ui_prefs.json"
            choice_path = cfg / "ui_choice.json"
            merged = {
                "ui": "standard",
                "ui_prefs": {
                    "schema_version": 3,
                    "connect_layout": {"order": ["run", "connection"]},
                },
            }
            with (
                mock.patch("ui.ui_prefs.CONFIG_PATH", prefs_path),
                mock.patch("ui.picker.CONFIG_PATH", choice_path),
                mock.patch(
                    "product_ui_defaults.load_merged_product_ui_defaults",
                    return_value=merged,
                ),
            ):
                self.assertTrue(apply_product_ui_defaults_to_user(overwrite=True))
            self.assertTrue(prefs_path.is_file())
            self.assertTrue(choice_path.is_file())

    def test_capture_snapshot_strips_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            prefs_path = cfg / "ui_prefs.json"
            choice_path = cfg / "ui_choice.json"
            prefs_path.write_text(
                json.dumps(
                    {
                        "schema_version": 3,
                        "recent_sessions": [1],
                        "connect_layout": {"order": ["run"]},
                    }
                ),
                encoding="utf-8",
            )
            choice_path.write_text(json.dumps({"ui": "standard"}), encoding="utf-8")
            with (
                mock.patch("ui.ui_prefs.CONFIG_PATH", prefs_path),
                mock.patch("ui.picker.CONFIG_PATH", choice_path),
            ):
                snap = capture_ui_layout_snapshot_from_user_profile()
            self.assertEqual(snap["ui"], UI_STANDARD)
            self.assertNotIn("recent_sessions", snap["ui_prefs"])


if __name__ == "__main__":
    unittest.main()

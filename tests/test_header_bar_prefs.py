"""Tests for header bar icon import validation."""
from __future__ import annotations

import json
import unittest

from ui.header_bar_prefs import (
    CHIP_ICON_SCHEMA_VERSION,
    example_chip_icons_json,
    merge_chip_icon,
    normalize_header_chips_icon_mode,
    parse_chip_icons_import,
)


class TestHeaderBarPrefs(unittest.TestCase):
    def test_normalize_icon_mode(self) -> None:
        self.assertEqual(normalize_header_chips_icon_mode("icons"), "icons")
        self.assertEqual(normalize_header_chips_icon_mode("bogus"), "auto")

    def test_parse_valid_import(self) -> None:
        text = example_chip_icons_json()
        icons = parse_chip_icons_import(text)
        self.assertIn("control", icons)
        self.assertEqual(icons["control"], "🎛")

    def test_reject_unknown_key(self) -> None:
        payload = json.dumps({"icons": {"not_a_section": "?"}})
        with self.assertRaises(ValueError):
            parse_chip_icons_import(payload)

    def test_reject_long_glyph(self) -> None:
        payload = json.dumps({"icons": {"control": "abcdef"}})
        with self.assertRaises(ValueError):
            parse_chip_icons_import(payload)

    def test_merge_chip_icon_override(self) -> None:
        self.assertEqual(merge_chip_icon("control", "🎛", {"control": "⚡"}), "⚡")
        self.assertEqual(merge_chip_icon("hub", "🛰", {}), "🛰")

    def test_schema_version_gate(self) -> None:
        payload = json.dumps({"schema_version": CHIP_ICON_SCHEMA_VERSION + 1, "icons": {"control": "🎛"}})
        with self.assertRaises(ValueError):
            parse_chip_icons_import(payload)


if __name__ == "__main__":
    unittest.main()

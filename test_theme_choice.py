"""Theme persistence, randomize snapshots, and favorite round-trip."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ui import theme_choice
from ui.theme_palette import (
    apply_theme_colors,
    build_zone_theme_map,
    generate_random_theme_map,
    generate_random_zone_colors,
    generate_standardized_zone_colors,
)


class TestThemeChoice(unittest.TestCase):
    def test_random_theme_current_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                random_map = generate_random_theme_map(seed=7)
                theme_choice.save_random_theme_current(random_map)
                loaded = theme_choice.load_random_theme_current()
                self.assertTrue(loaded)
                self.assertEqual(set(loaded.keys()), set(random_map.keys()))
                self.assertTrue(all(v.startswith("#") and len(v) == 7 for v in loaded.values()))

    def test_save_current_random_as_favorite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                self.assertFalse(theme_choice.save_random_current_as_favorite())
                theme_choice.save_random_theme_current({"#111111": "#222222"})
                self.assertTrue(theme_choice.save_random_current_as_favorite())
                self.assertEqual(
                    theme_choice.load_random_theme_favorite(),
                    {"#111111": "#222222"},
                )

    def test_apply_theme_colors_uses_saved_random_current_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                theme_choice.save_random_theme_current({"#2f2329": "#123456"})
                css = "QWidget { background-color: #2f2329; color: #f4f0ea; }"
                out = apply_theme_colors(css, theme_choice.THEME_RANDOM_CURRENT)
                self.assertIn("#123456", out)
                self.assertNotIn("#2f2329", out)

    def test_random_seed_lock_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                self.assertFalse(theme_choice.load_random_seed_lock())
                theme_choice.save_random_seed_lock(True)
                self.assertTrue(theme_choice.load_random_seed_lock())

    def test_locked_variant_sequence_uses_same_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                fam1, var1 = theme_choice.next_locked_random_variant()
                fam2, var2 = theme_choice.next_locked_random_variant()
                self.assertGreater(fam1, 0)
                self.assertEqual(fam1, fam2)
                self.assertEqual(var1, 0)
                self.assertEqual(var2, 1)

    def test_random_theme_current_zones_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                zones = generate_random_zone_colors(seed=99)
                theme_choice.save_random_theme_current_zones(zones)
                loaded = theme_choice.load_random_theme_current_zones()
                self.assertEqual(set(loaded.keys()), set(theme_choice.THEME_ZONE_KEYS))
                self.assertEqual(loaded["background"], zones["background"])

    def test_build_zone_theme_map_changes_zone_tokens(self) -> None:
        zones = {
            "background": "#112233",
            "topbar": "#224466",
            "tabs": "#663399",
            "buttons": "#c05080",
            "inputs": "#226677",
            "logs": "#110022",
            "accent": "#eebb44",
        }
        mapping = build_zone_theme_map(zones)
        self.assertIn("#2f2329", mapping)
        self.assertIn("#3a2a31", mapping)
        self.assertIn("#d4af37", mapping)

    def test_save_current_as_favorite_copies_zone_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                zones = generate_random_zone_colors(seed=42)
                theme_choice.save_random_theme_current(build_zone_theme_map(zones))
                theme_choice.save_random_theme_current_zones(zones)
                self.assertTrue(theme_choice.save_random_current_as_favorite())
                fav = theme_choice.load_random_theme_favorite_zones()
                self.assertEqual(fav, zones)

    def test_theme_pack_build_and_normalize(self) -> None:
        zones = {
            "background": "#112233",
            "topbar": "#224466",
            "tabs": "#663399",
            "buttons": "#c05080",
            "inputs": "#226677",
            "logs": "#110022",
            "accent": "#eebb44",
        }
        pack = theme_choice.build_theme_pack(
            theme_choice.THEME_RANDOM_CURRENT,
            zones,
            seed_lock=True,
            favorite_zones={"background": "#334455", "accent": "#ffaa33"},
        )
        parsed = theme_choice.normalize_theme_pack(pack)
        assert parsed is not None
        self.assertEqual(parsed["theme"], theme_choice.THEME_RANDOM_CURRENT)
        self.assertTrue(parsed["seed_lock"])
        self.assertEqual(parsed["zones"]["buttons"], "#c05080")
        self.assertIn("favorite_zones", parsed)

    def test_theme_preset_crud(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                preset = {
                    "theme": theme_choice.THEME_RANDOM_CURRENT,
                    "seed_lock": True,
                    "zones": {
                        "background": "#112233",
                        "topbar": "#224466",
                        "tabs": "#663399",
                        "buttons": "#c05080",
                        "inputs": "#226677",
                        "logs": "#110022",
                        "accent": "#eebb44",
                    },
                }
                self.assertTrue(theme_choice.save_theme_preset("Party", preset))
                names = theme_choice.list_theme_preset_names()
                self.assertEqual(names, ["Party"])
                loaded = theme_choice.load_theme_preset("Party")
                assert loaded is not None
                self.assertTrue(loaded["seed_lock"])
                self.assertEqual(loaded["zones"]["accent"], "#eebb44")
                self.assertTrue(theme_choice.delete_theme_preset("Party"))
                self.assertEqual(theme_choice.list_theme_preset_names(), [])

    def test_theme_preset_reorder_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                base = {
                    "theme": theme_choice.THEME_RANDOM_CURRENT,
                    "seed_lock": False,
                    "zones": {
                        "background": "#112233",
                        "topbar": "#224466",
                        "tabs": "#663399",
                        "buttons": "#c05080",
                        "inputs": "#226677",
                        "logs": "#110022",
                        "accent": "#eebb44",
                    },
                }
                self.assertTrue(theme_choice.save_theme_preset("One", base))
                self.assertTrue(theme_choice.save_theme_preset("Two", base))
                self.assertTrue(theme_choice.save_theme_preset("Three", base))
                self.assertEqual(theme_choice.list_theme_preset_names(), ["One", "Two", "Three"])
                self.assertTrue(theme_choice.reorder_theme_presets(["Three", "One", "Two"]))
                self.assertEqual(theme_choice.list_theme_preset_names(), ["Three", "One", "Two"])

    def test_theme_zone_order_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "ui_theme.json"
            with patch.object(theme_choice, "CONFIG_PATH", cfg):
                order = list(theme_choice.THEME_ZONE_KEYS)[::-1]
                self.assertTrue(theme_choice.save_theme_zone_order(order))
                self.assertEqual(theme_choice.load_theme_zone_order(), order)

    def test_standardized_zone_generator_has_all_zones(self) -> None:
        zones = generate_standardized_zone_colors(seed=123)
        self.assertEqual(set(zones.keys()), set(theme_choice.THEME_ZONE_KEYS))
        self.assertTrue(all(v.startswith("#") and len(v) == 7 for v in zones.values()))


if __name__ == "__main__":
    unittest.main()

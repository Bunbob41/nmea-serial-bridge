"""Theme studio zone color inference."""
from __future__ import annotations

import unittest

from ui.theme_choice import THEME_FOREST, THEME_OCEAN, THEME_SLATE, _normalize_theme_id
from ui.theme_palette import (
    DEFAULT_ZONE_COLORS,
    zone_colors_for_theme,
    zone_colors_from_theme_map,
)


class TestThemeZones(unittest.TestCase):
    def test_arctic_theme_maps_to_slate(self) -> None:
        self.assertEqual(_normalize_theme_id("arctic_day"), THEME_SLATE)

    def test_forest_zone_colors_differ_from_generic_defaults(self) -> None:
        forest = zone_colors_for_theme(THEME_FOREST)
        self.assertNotEqual(forest["background"], DEFAULT_ZONE_COLORS["background"])
        self.assertTrue(forest["background"].startswith("#"))

    def test_ocean_zone_colors_from_map(self) -> None:
        from ui.theme_palette import THEME_COLOR_MAPS

        ocean = zone_colors_from_theme_map(THEME_COLOR_MAPS[THEME_OCEAN])
        self.assertEqual(ocean["background"], "#1a2838")


if __name__ == "__main__":
    unittest.main()

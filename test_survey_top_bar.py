"""Survey top bar chip order helpers."""
from __future__ import annotations

import unittest

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from ui.survey_top_bar import (
    COMPACT_EXIT_ABOVE_PX,
    DEFAULT_TOPBAR_ORDER,
    EXPANDED_FIT_SLACK_PX,
    TOPBAR_ALWAYS_FILL_TRACK,
    SurveyTopBar,
    TopBarChip,
    build_ui_switch_inner,
    choose_compact_mode,
    compact_letter_for,
    configure_topbar_button,
    distribute_equal_widths,
    normalize_topbar_order,
    preferred_compact_for,
    snap_insert_index,
    text_body_width,
)


class SurveyTopBarTests(unittest.TestCase):
    def test_normalize_adds_defaults_and_ui_switch(self) -> None:
        order = normalize_topbar_order(["view", "presets"])
        self.assertEqual(order[:2], ["view", "presets"])
        self.assertIn("ui_switch", order)
        self.assertEqual(len(order), len(DEFAULT_TOPBAR_ORDER))

    def test_compact_display_for_known_keys(self) -> None:
        self.assertEqual(compact_letter_for("view", "View"), "View")
        self.assertEqual(compact_letter_for("shortcuts", "Shortcuts"), "Keys")
        self.assertEqual(compact_letter_for("randomize_theme", "Randomize theme"), "Rand")
        self.assertEqual(compact_letter_for("standardize_theme", "Standardize theme"), "Strd")
        self.assertEqual(compact_letter_for("ui_switch", "Layout"), "Layout")

    def test_preferred_compact_words_for_random_and_standardize(self) -> None:
        self.assertEqual(preferred_compact_for("randomize_theme", "Randomize theme"), "Random")
        self.assertEqual(preferred_compact_for("standardize_theme", "Standardize theme"), "Slate")

    def test_layout_button_always_says_layout(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        toggled: list[str] = []

        class _Host(QtWidgets.QWidget):
            _ui_mode = "standard"

        host = _Host()
        btn = build_ui_switch_inner(host, on_toggle=lambda: toggled.append("ok") or True)
        self.assertEqual(btn.text(), "Layout")
        self.assertEqual(str(btn.property("topBarFullText") or ""), "Layout")

    def test_layout_button_single_click_toggles(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        toggled: list[str] = []
        host = QtWidgets.QWidget()
        btn = build_ui_switch_inner(host, on_toggle=lambda: toggled.append("ok") or True)
        host.resize(120, 40)
        host.show()
        app.processEvents()
        QtTest.QTest.mouseClick(btn, QtCore.Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertEqual(toggled, ["ok"])
        self.assertTrue(btn.isEnabled())

    def test_layout_button_double_click_toggles(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        toggled: list[str] = []
        host = QtWidgets.QWidget()
        btn = build_ui_switch_inner(host, on_toggle=lambda: toggled.append("ok") or True)
        host.resize(120, 40)
        host.show()
        app.processEvents()
        QtTest.QTest.mouseDClick(btn, QtCore.Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertEqual(toggled, ["ok"])
        self.assertTrue(btn.isEnabled())

    def test_layout_button_stays_enabled_when_toggle_fails(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        host = QtWidgets.QWidget()
        btn = build_ui_switch_inner(host, on_toggle=lambda: False)
        host.resize(120, 40)
        host.show()
        app.processEvents()
        QtTest.QTest.mouseClick(btn, QtCore.Qt.MouseButton.LeftButton)
        app.processEvents()
        self.assertTrue(btn.isEnabled())

    def test_compact_chip_prefers_word_before_abbreviation(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        btn = QtWidgets.QToolButton()
        configure_topbar_button(btn, "Randomize theme")
        chip = TopBarChip("randomize_theme", btn, full_label="Randomize theme")
        chip.set_compact(True)
        chip.set_spring_width(112)
        app.processEvents()
        self.assertEqual(btn.text(), "Random")

    def test_compact_display_fallback_shortens_unknown(self) -> None:
        self.assertEqual(compact_letter_for("custom", "Widgets"), "Widgets")

    def test_expanded_only_when_labels_fit(self) -> None:
        need = 1000
        need_c = 400
        self.assertTrue(
            choose_compact_mode(
                avail=need - EXPANDED_FIT_SLACK_PX - 1,
                need_expanded=need,
                need_compact=need_c,
                currently_compact=False,
            )
        )
        self.assertFalse(
            choose_compact_mode(
                avail=need + EXPANDED_FIT_SLACK_PX + 20,
                need_expanded=need,
                need_compact=need_c,
                currently_compact=False,
            )
        )

    def test_compact_hysteresis_stays_compact_until_wide_enough(self) -> None:
        need = 1000
        need_c = 400
        avail = need + COMPACT_EXIT_ABOVE_PX - 10
        self.assertTrue(
            choose_compact_mode(
                avail=avail,
                need_expanded=need,
                need_compact=need_c,
                currently_compact=True,
            )
        )
        avail2 = need + COMPACT_EXIT_ABOVE_PX + 10
        self.assertFalse(
            choose_compact_mode(
                avail=avail2,
                need_expanded=need,
                need_compact=need_c,
                currently_compact=True,
            )
        )

    def test_hide_chip_removes_from_layout(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bar = SurveyTopBar()
        for key, label in (("demo", "Demo"), ("copy_stats", "Copy stats")):
            btn = QtWidgets.QToolButton()
            configure_topbar_button(btn, label)
            bar.register(key, label, btn)
        bar.set_prefs(["demo", "copy_stats"], set())
        bar.hide_chip("copy_stats")
        self.assertIn("copy_stats", bar.hidden())
        self.assertFalse(bar.chip("copy_stats").isVisible())
        lay = bar._track.layout()
        self.assertIsInstance(lay, QtWidgets.QHBoxLayout)
        layout_widgets = []
        for i in range(lay.count()):
            item = lay.itemAt(i)
            w = item.widget() if item is not None else None
            if w is not None:
                layout_widgets.append(w)
        self.assertNotIn(bar.chip("copy_stats"), layout_widgets)

    def test_text_body_width_scales_with_label(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        btn = QtWidgets.QToolButton()
        fm = btn.fontMetrics()
        narrow = text_body_width(fm, "View")
        wide = text_body_width(fm, "Randomize theme")
        self.assertLess(narrow, wide)

    def test_spring_fill_invariant_enabled(self) -> None:
        self.assertTrue(TOPBAR_ALWAYS_FILL_TRACK)

    def test_distribute_equal_widths_uses_remainder(self) -> None:
        widths = distribute_equal_widths(200, 3)
        self.assertEqual(sum(widths), 200)
        self.assertEqual(widths, [67, 67, 66])

    def test_equal_chip_widths_sum_to_track(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bar = SurveyTopBar()
        labels = (
            ("view", "View"),
            ("presets", "Presets"),
            ("demo", "Demo"),
            ("tools", "Tools"),
        )
        for key, label in labels:
            btn = QtWidgets.QToolButton()
            configure_topbar_button(btn, label)
            bar.register(key, label, btn)
        bar.set_prefs([k for k, _ in labels], set())
        bar.resize(480, 40)
        bar.show()
        app.processEvents()
        bar._apply_spring_layout()
        keys = bar._visible_keys()
        total = sum(bar._chips[k].width() for k in keys)
        spacing = bar._track_lay.spacing() * max(0, len(keys) - 1)
        m = bar._track_lay.contentsMargins()
        inner = bar._track.width() - m.left() - m.right()
        self.assertGreaterEqual(total + spacing, inner - 4)

    def test_spring_layout_has_no_gap_stretch(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bar = SurveyTopBar()
        for key, label in (("view", "View"), ("presets", "Presets"), ("demo", "Demo")):
            btn = QtWidgets.QToolButton()
            configure_topbar_button(btn, label)
            bar.register(key, label, btn)
        bar.set_prefs(["view", "presets", "demo"], set())
        bar.resize(600, 40)
        bar.show()
        app.processEvents()
        lay = bar._track_lay
        for i in range(lay.count()):
            item = lay.itemAt(i)
            self.assertIsNotNone(item)
            assert item is not None
            self.assertIsNone(item.spacerItem())

    def test_narrow_bar_uses_short_text_without_ellipsis(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bar = SurveyTopBar()
        for key, label in (
            ("view", "View"),
            ("presets", "Presets"),
            ("ui_editor", "UI editor"),
            ("demo", "Demo"),
        ):
            btn = QtWidgets.QToolButton()
            configure_topbar_button(btn, label)
            bar.register(key, label, btn)
        bar.set_prefs(["view", "presets", "ui_editor", "demo"], set())
        bar.resize(260, 40)
        bar.show()
        app.processEvents()
        bar._apply_spring_layout()
        for key in bar._visible_keys():
            chip = bar.chip(key)
            self.assertIsNotNone(chip)
            assert isinstance(chip, TopBarChip)
            text = chip._inner.text() if isinstance(chip._inner, QtWidgets.QToolButton) else ""
            self.assertNotIn("…", text)
            self.assertNotIn("...", text)

    def test_wide_share_shows_full_label(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        host = QtWidgets.QWidget()
        host.resize(1200, 400)
        bar = SurveyTopBar()
        for key, label in (("view", "View"), ("presets", "Presets")):
            btn = QtWidgets.QToolButton()
            configure_topbar_button(btn, label)
            bar.register(key, label, btn)
        bar.set_prefs(["view", "presets"], set())
        bar.set_host_window(host)
        bar.resize(1200, 40)
        bar.show()
        app.processEvents()
        bar._apply_spring_layout()
        view = bar.chip("view")
        self.assertIsNotNone(view)
        assert isinstance(view, TopBarChip)
        self.assertFalse(view._compact)
        self.assertEqual(view._inner.text(), "View")

    def test_snap_insert_index_left(self) -> None:
        rects = [
            ("a", QtCore.QRect(10, 0, 40, 20)),
            ("b", QtCore.QRect(60, 0, 40, 20)),
        ]
        self.assertEqual(snap_insert_index(5, rects), 0)
        self.assertEqual(snap_insert_index(45, rects), 1)
        self.assertEqual(snap_insert_index(200, rects), 2)

    def test_cluster_layout_content_sized_not_stretched(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bar = SurveyTopBar()
        for key, label in (("view", "View"), ("hud", "HUD"), ("ui_switch", "Layout")):
            btn = QtWidgets.QToolButton()
            configure_topbar_button(btn, label)
            bar.register(key, label, btn, pin_right=(key == "ui_switch"))
        bar.set_layout_mode("cluster")
        bar.set_interactive_chrome(False)
        bar.set_prefs(["view", "hud", "ui_switch"], set())
        host = QtWidgets.QWidget()
        host.resize(900, 40)
        lay = QtWidgets.QHBoxLayout(host)
        bar.embed_track_in(host, lay)
        host.show()
        app.processEvents()
        bar._apply_cluster_layout()
        keys = bar._visible_keys()
        total = sum(bar._chips[k].width() for k in keys)
        self.assertLess(total, 900 // 2)
        view = bar.chip("view")
        self.assertIsNotNone(view)
        assert view is not None
        self.assertFalse(view._grip.isVisible())
        self.assertFalse(view._resize_edge.isVisible())
        layout_chip = bar.chip("ui_switch")
        self.assertIsNotNone(layout_chip)
        assert layout_chip is not None
        inner = layout_chip._inner
        self.assertIsInstance(inner, QtWidgets.QToolButton)
        self.assertEqual(inner.text(), "Layout")

    def test_embed_track_in_uses_minimum_size_policy(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bar = SurveyTopBar()
        btn = QtWidgets.QToolButton()
        configure_topbar_button(btn, "Layout")
        bar.register("ui_switch", "Layout", btn, pin_right=True)
        bar.set_layout_mode("cluster")
        host = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(host)
        bar.embed_track_in(host, lay)
        track = bar._track
        self.assertEqual(
            track.sizePolicy().horizontalPolicy(),
            QtWidgets.QSizePolicy.Policy.Minimum,
        )

    def test_embedded_nav_minimum_width_fits_chip_labels(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bar = SurveyTopBar()
        keys_labels = (("view", "View"), ("hud", "HUD"), ("ui_switch", "Layout"))
        for key, label in keys_labels:
            btn = QtWidgets.QToolButton()
            configure_topbar_button(btn, label)
            bar.register(key, label, btn, pin_right=(key == "ui_switch"))
        bar.set_prefs([k for k, _ in keys_labels], set())
        bar.set_layout_mode("cluster")
        bar.set_interactive_chrome(False)
        natural_sum = sum(
            bar._chips[key].natural_total_width(compact=False) for key, _ in keys_labels
        )
        nav = QtWidgets.QWidget()
        nav_lay = QtWidgets.QHBoxLayout(nav)
        widths: list[int] = []

        def _on_width(need: int) -> None:
            widths.append(need)
            nav.setMinimumWidth(need)

        bar.set_cluster_width_callback(_on_width)
        bar.embed_track_in(nav, nav_lay)
        nav.show()
        app.processEvents()
        bar._apply_cluster_layout()
        app.processEvents()
        self.assertTrue(widths)
        self.assertGreaterEqual(nav.minimumWidth(), natural_sum)
        layout_chip = bar.chip("ui_switch")
        self.assertIsNotNone(layout_chip)
        assert layout_chip is not None
        inner = layout_chip._inner
        self.assertIsInstance(inner, QtWidgets.QToolButton)
        self.assertEqual(inner.text(), "Layout")

    def test_embedded_layout_toggle_shows_full_label(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bar = SurveyTopBar()

        class _Host(QtWidgets.QWidget):
            _ui_mode = "modern"

        host = _Host()
        btn = build_ui_switch_inner(host, on_toggle=lambda: True)
        bar.register("ui_switch", "Layout", btn, pin_right=True)
        bar.set_layout_mode("cluster")
        bar.set_interactive_chrome(False)
        bar.set_prefs(["view", "hud", "ui_switch"], {"hud", "tools"})
        nav = QtWidgets.QWidget()
        nav_lay = QtWidgets.QHBoxLayout(nav)
        bar.embed_track_in(nav, nav_lay)
        nav.resize(400, 40)
        nav.show()
        app.processEvents()
        bar._apply_cluster_layout()
        app.processEvents()
        chip = bar.chip("ui_switch")
        self.assertIsNotNone(chip)
        assert chip is not None
        self.assertEqual(btn.text(), "Layout")
        self.assertGreaterEqual(btn.maximumWidth(), btn.minimumWidth())
        self.assertGreaterEqual(chip.minimumWidth(), 90)

    def test_cluster_layout_survives_pending_spring_timer(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bar = SurveyTopBar()
        for key, label in (("view", "View"), ("hud", "HUD"), ("ui_switch", "Layout")):
            btn = QtWidgets.QToolButton()
            configure_topbar_button(btn, label)
            bar.register(key, label, btn, pin_right=(key == "ui_switch"))
        bar.set_prefs(["view", "hud", "ui_switch"], set(), {"view": 2.0, "hud": 1.0})
        bar._spring_layout_timer.start(16)
        bar.set_layout_mode("cluster")
        bar.set_interactive_chrome(False)
        host = QtWidgets.QWidget()
        host.resize(900, 40)
        lay = QtWidgets.QHBoxLayout(host)
        bar.embed_track_in(host, lay)
        host.show()
        app.processEvents()
        bar._spring_layout_timer.stop()
        bar._apply_spring_layout()
        bar._apply_cluster_layout()
        keys = bar._visible_keys()
        total = sum(bar._chips[k].width() for k in keys)
        self.assertLess(total, 900 // 2)


class ModernToolsChipCompressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QtWidgets.QApplication.instance() is None:
            cls._app = QtWidgets.QApplication([])
        else:
            cls._app = QtWidgets.QApplication.instance()

    def test_should_use_header_icon_only_hysteresis(self) -> None:
        from ui.modern_tools_chips import should_use_header_icon_only

        self.assertTrue(
            should_use_header_icon_only(200, 300, currently_icon_only=False)
        )
        self.assertFalse(
            should_use_header_icon_only(320, 300, currently_icon_only=False)
        )
        self.assertTrue(
            should_use_header_icon_only(310, 300, currently_icon_only=True)
        )
        self.assertFalse(
            should_use_header_icon_only(330, 300, currently_icon_only=True)
        )

    def test_icon_only_chip_shows_icon_not_label(self) -> None:
        from ui.modern_tools_chips import apply_embedded_header_chip_style

        btn = QtWidgets.QPushButton()
        btn.setObjectName("modernToolsNavChip")
        btn.setProperty("navIcon", "*")
        btn.setProperty("navLabel", "Control")
        apply_embedded_header_chip_style(btn, compact=True, icon_only=True)
        self.assertEqual(btn.text(), "*")
        self.assertNotIn("Control", btn.text())
        self.assertEqual(btn.toolTip(), "Control")

    def test_embedded_chip_inner_width_matches_row(self) -> None:
        from ui.modern_tools_chips import (
            estimate_embedded_chips_row_width,
            sync_embedded_chip_inner_width,
        )

        buttons: list[QtWidgets.QPushButton] = []
        for icon, label in (("A", "Control"), ("B", "Activity")):
            btn = QtWidgets.QPushButton()
            btn.setObjectName("modernToolsNavChip")
            btn.setProperty("navIcon", icon)
            btn.setProperty("navLabel", label)
            buttons.append(btn)
        inner = QtWidgets.QWidget()
        row = sync_embedded_chip_inner_width(inner, buttons, [], icon_only=True)
        self.assertEqual(inner.minimumWidth(), row)
        self.assertEqual(
            row,
            estimate_embedded_chips_row_width(buttons, [], icon_only=True),
        )


if __name__ == "__main__":
    unittest.main()

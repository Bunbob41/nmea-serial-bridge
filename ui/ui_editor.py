"""Workspace UI editor — top bar tiles, Connect sections, and main tabs."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.connect_panels import (
    CONNECT_TOOLBAR_KEYS,
    CONNECT_TOOLBAR_LABELS,
    CONNECT_PANEL_KEYS,
    CONNECT_PANEL_LABELS,
    REQUIRED_CONNECT_PANELS,
    _rebuild_connect_panels,
    restore_connect_panel_layout,
    sanitize_connect_panel_hidden,
)
from ui.survey_top_bar import DEFAULT_TOPBAR_ORDER, TOPBAR_SHORT_LABEL, normalize_topbar_order
from ui.ui_prefs import (
    dedupe_preserve_order,
    load_connect_panel_prefs,
    load_tab_order,
    save_connect_panel_prefs,
    save_tab_order,
)

TOP_BAR_CHIP_LABELS: dict[str, str] = {
    "view": "View menu",
    "presets": "Presets",
    "recent": "Recent sessions",
    "hud": "Survey HUD",
    "tools": "Tools drawer",
    "randomize_theme": "Randomize theme",
    "standardize_theme": "Standardize theme",
    "ui_editor": "UI editor",
    "shortcuts": "Shortcuts legend",
    "copy_stats": "Copy stats",
    "ui_switch": "Layout (click toggles Standard / Field)",
}

CONNECT_PANEL_HINTS: dict[str, str] = {
    "run": "Start/Stop",
    "hint": "Intent / preset guidance",
    "quick_log": "Compact live log",
    "quick_terminal": "Bench script output",
    "connection": "COM, baud, UDP/TCP",
}
CONNECT_TOOLBAR_HINTS: dict[str, str] = {
    "ui_editor": "Open this layout editor",
    "expand_all": "Expand all Connect sections",
    "collapse_all": "Collapse all Connect sections",
}

MAIN_TAB_HINTS: dict[str, str] = {
    "Connect": "COM, UDP/TCP, Start/Stop",
    "Log": "Bridge log and filters",
    "Tools": "Presets, Phone, NMEA, Theme, Guide",
    "Activity": "Live bridge traffic, terminal, filters, and pause/save",
    "Control": "COM, baud, UDP/TCP listen, and connection presets",
    "Presets": "Named COM/UDP presets",
    "Hub": "Connection hub — scan, fan-out, and quick picks",
    "NMEA": "Passthrough, strict, or raw",
    "Theme": "Optional colors (bench)",
    "Guide": "UDP/TCP workflows",
    "Phone": "Web API, token, QR",
    "Dashboard": "Web API, token, QR",
    "Terminal": "Local PowerShell / cmd",
    "Inject": "Send test NMEA to serial / network",
    "Diagnostics": "Bench checks and file log",
    "Black box": "Raw session capture (.raw)",
    "File log": "Rotating bridge text log",
    "Checks": "Automated bench checks",
}

DEFAULT_TOPBAR_HIDDEN_CHIPS: frozenset[str] = frozenset(
    {"randomize_theme", "standardize_theme"}
)

MODERN_HEADER_CHIP_KEYS: frozenset[str] = frozenset({"view", "hud", "ui_switch"})

_EDITOR_DIALOG_MIN_W = 680
_EDITOR_DIALOG_MIN_H = 460
_EDITOR_DIALOG_DEFAULT_W = 760
_EDITOR_DIALOG_DEFAULT_H = 540


def migrate_topbar_order(order: list[str]) -> list[str]:
    return normalize_topbar_order(order)


def migrate_topbar_hidden(hidden: set[str] | list[str]) -> set[str]:
    h = {str(x).strip() for x in hidden if str(x).strip()}
    h.discard("demo")
    h.discard("hidden_tabs")
    h.discard("view")
    return h


def build_main_tab_editor_rows(
    catalog: dict[str, tuple[QtWidgets.QWidget, str]],
    hidden: set[str],
    *,
    ui_mode: str = "standard",
    tabs_key: str = "main_tabs",
) -> list[tuple[str, str, str, bool, bool]]:
    saved = load_tab_order(ui_mode, tabs_key)
    order = [n for n in saved if n in catalog]
    for name in catalog:
        if name not in order:
            order.append(name)
    rows: list[tuple[str, str, str, bool, bool]] = []
    for name in order:
        _widget, tip = catalog[name]
        subtitle = (tip or "").strip() or MAIN_TAB_HINTS.get(name, "")
        rows.append((name, name, subtitle, name not in hidden, True))
    return rows


def build_connect_panel_editor_rows(ui_mode: str) -> list[tuple[str, str, str, bool, bool]]:
    prefs = load_connect_panel_prefs(ui_mode)
    order = [str(k).strip() for k in prefs.get("order", []) if str(k).strip() in CONNECT_PANEL_KEYS]
    for key in CONNECT_PANEL_KEYS:
        if key not in order:
            order.append(key)
    hidden = set(sanitize_connect_panel_hidden(prefs.get("hidden", [])))
    rows: list[tuple[str, str, str, bool, bool]] = []
    for key in order:
        title = CONNECT_PANEL_LABELS.get(key, key)
        subtitle = CONNECT_PANEL_HINTS.get(key, "")
        rows.append((key, title, subtitle, key not in hidden, True))
    return rows


def build_connect_toolbar_rows(ui_mode: str) -> list[tuple[str, str, str, bool, bool]]:
    prefs = load_connect_panel_prefs(ui_mode)
    order = [str(k).strip() for k in prefs.get("toolbar_order", []) if str(k).strip() in CONNECT_TOOLBAR_KEYS]
    for key in CONNECT_TOOLBAR_KEYS:
        if key not in order:
            order.append(key)
    rows: list[tuple[str, str, str, bool, bool]] = []
    for key in order:
        rows.append(
            (
                key,
                CONNECT_TOOLBAR_LABELS.get(key, key),
                CONNECT_TOOLBAR_HINTS.get(key, ""),
                True,
                True,
            )
        )
    return rows


class _EditorRow(QtWidgets.QFrame):
    """One checklist row with ↑ ↓ reorder buttons."""

    def __init__(
        self,
        key: str,
        title: str,
        subtitle: str,
        *,
        visible: bool,
        hideable: bool,
        on_move: Callable[[str, int], None],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("uiEditorRow")
        self._key = key
        self._on_move = on_move
        row_lay = QtWidgets.QHBoxLayout(self)
        row_lay.setContentsMargins(8, 6, 8, 6)
        row_lay.setSpacing(8)

        self._chk = QtWidgets.QCheckBox()
        self._chk.setChecked(visible)
        self._chk.setEnabled(hideable)
        if hideable:
            self._chk.setToolTip(f"Show «{title}»")
        else:
            self._chk.setChecked(True)
            self._chk.setToolTip("Always shown (reorder with ↑ ↓ only)")
        row_lay.addWidget(self._chk, 0)

        text_col = QtWidgets.QVBoxLayout()
        text_col.setSpacing(2)
        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setObjectName("uiEditorRowTitle")
        text_col.addWidget(title_lbl)
        if subtitle.strip():
            sub_lbl = QtWidgets.QLabel(subtitle.strip())
            sub_lbl.setWordWrap(True)
            sub_lbl.setObjectName("tabNote")
            text_col.addWidget(sub_lbl)
        row_lay.addLayout(text_col, 1)

        btn_col = QtWidgets.QVBoxLayout()
        btn_col.setSpacing(2)
        self._btn_up = QtWidgets.QToolButton()
        self._btn_up.setText("↑")
        self._btn_up.setToolTip("Move up")
        self._btn_up.setFixedSize(32, 26)
        self._btn_up.clicked.connect(lambda: self._on_move(self._key, -1))
        self._btn_down = QtWidgets.QToolButton()
        self._btn_down.setText("↓")
        self._btn_down.setToolTip("Move down")
        self._btn_down.setFixedSize(32, 26)
        self._btn_down.clicked.connect(lambda: self._on_move(self._key, 1))
        btn_col.addWidget(self._btn_up)
        btn_col.addWidget(self._btn_down)
        row_lay.addLayout(btn_col, 0)

    def set_move_enabled(self, *, up: bool, down: bool) -> None:
        self._btn_up.setEnabled(up)
        self._btn_down.setEnabled(down)

    @property
    def key(self) -> str:
        return self._key

    def is_visible(self) -> bool:
        return self._chk.isChecked()


class _EditorListPage(QtWidgets.QWidget):
    """Checklist page with ↑ ↓ reorder (replaces drag-and-drop list)."""

    def __init__(
        self,
        intro: str,
        *,
        legend: str = "↑ ↓ reorder rows. Checkbox = visible in the app.",
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(8)
        hint = QtWidgets.QLabel(intro)
        hint.setWordWrap(True)
        hint.setObjectName("tabHint")
        lay.addWidget(hint)
        legend_lbl = QtWidgets.QLabel(legend)
        legend_lbl.setWordWrap(True)
        legend_lbl.setObjectName("tabNote")
        lay.addWidget(legend_lbl)

        scroll = QtWidgets.QScrollArea()
        scroll.setObjectName("uiEditorScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._container = QtWidgets.QWidget()
        self._container.setObjectName("uiEditorListHost")
        self._list_lay = QtWidgets.QVBoxLayout(self._container)
        self._list_lay.setContentsMargins(4, 4, 4, 4)
        self._list_lay.setSpacing(4)
        self._list_lay.addStretch(0)
        scroll.setWidget(self._container)
        scroll.setMinimumHeight(260)
        lay.addWidget(scroll, 1)
        self._rows: list[_EditorRow] = []

    def _clear_rows(self) -> None:
        for row in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        while self._list_lay.count() > 1:
            item = self._list_lay.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.setParent(None)

    def _move_row(self, key: str, delta: int) -> None:
        keys = [r.key for r in self._rows]
        try:
            idx = keys.index(key)
        except ValueError:
            return
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self._rows):
            return
        self._rows[idx], self._rows[new_idx] = self._rows[new_idx], self._rows[idx]
        self._relayout_rows()

    def _relayout_rows(self) -> None:
        while self._list_lay.count() > 1:
            self._list_lay.takeAt(0)
        n = len(self._rows)
        for i, row in enumerate(self._rows):
            self._list_lay.insertWidget(i, row)
            row.set_move_enabled(up=i > 0, down=i < n - 1)
        self._list_lay.addStretch(0)

    def set_rows(
        self,
        rows: list[tuple[str, str, bool, bool]],
        *,
        locked_keys: frozenset[str] = frozenset(),
        subtitles: dict[str, str] | None = None,
    ) -> None:
        self._clear_rows()
        subs = subtitles or {}
        for key, label, checked, _enabled in rows:
            self._rows.append(
                _EditorRow(
                    key,
                    label,
                    subs.get(key, ""),
                    visible=checked,
                    hideable=key not in locked_keys,
                    on_move=self._move_row,
                    parent=self._container,
                )
            )
        self._relayout_rows()

    def set_tab_rows(
        self,
        rows: list[tuple[str, str, str, bool, bool]],
        *,
        locked_keys: frozenset[str] = frozenset(),
    ) -> None:
        self._clear_rows()
        for key, title, subtitle, visible, _enabled in rows:
            self._rows.append(
                _EditorRow(
                    key,
                    title,
                    subtitle,
                    visible=visible,
                    hideable=key not in locked_keys,
                    on_move=self._move_row,
                    parent=self._container,
                )
            )
        self._relayout_rows()

    def ordered_checked(self) -> tuple[list[str], set[str]]:
        order = [r.key for r in self._rows]
        hidden = {r.key for r in self._rows if not r.is_visible()}
        return order, hidden


_CheckListPage = _EditorListPage


class UiEditorDialog(QtWidgets.QDialog):
    def __init__(
        self,
        win: QtWidgets.QWidget,
        *,
        initial_tab: int = 0,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent or win)
        self.setObjectName("UiEditorDialog")
        self._win = win
        self.setWindowTitle("UI editor")
        self.setMinimumSize(_EDITOR_DIALOG_MIN_W, _EDITOR_DIALOG_MIN_H)
        self.resize(_EDITOR_DIALOG_DEFAULT_W, _EDITOR_DIALOG_DEFAULT_H)

        ui_mode = getattr(win, "_ui_mode", "standard")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        if ui_mode == "standard":
            intro_text = (
                "Customize the <b>Standard</b> layout: survey top bar, Connect sections, "
                "and main tabs. Use <b>↑ ↓</b> on each row to reorder; checkboxes show or hide. "
                "<b>OK</b> applies. <b>Restore defaults</b> resets only the tab you are viewing."
            )
        elif ui_mode == "modern":
            intro_text = (
                "Customize the <b>Modern</b> layout: <b>Header</b> (View, HUD, Layout) and "
                "<b>Navigation</b> (Control, Presets, Hub, chip rail, and sidebar). "
                "Connect section order applies to <b>Standard</b> layout only. "
                "Use <b>↑ ↓</b> to reorder; checkboxes show or hide. <b>OK</b> applies."
            )
        else:
            intro_text = (
                "Customize the <b>Field</b> layout: survey top bar and Tools drawer tabs. "
                "Connect section order is edited in Standard layout. "
                "<b>↑ ↓</b> reorders; checkboxes show or hide. <b>OK</b> applies."
            )
        intro = QtWidgets.QLabel(intro_text)
        intro.setWordWrap(True)
        intro.setObjectName("tabHint")
        root.addWidget(intro)

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setUsesScrollButtons(True)
        root.addWidget(self._tabs, 1)

        bar = getattr(win, "_survey_top_bar", None)
        labels: dict[str, str] = dict(TOP_BAR_CHIP_LABELS)
        labels.update(getattr(win, "_topbar_labels", {}) or {})
        order = list(bar.order()) if bar is not None else list(DEFAULT_TOPBAR_ORDER)
        order = migrate_topbar_order(order)
        hidden_bar = migrate_topbar_hidden(bar.hidden() if bar is not None else set())
        bar_rows: list[tuple[str, str, bool, bool]] = []
        for key in order:
            if key not in labels and key not in TOPBAR_SHORT_LABEL:
                continue
            title = labels.get(key, TOPBAR_SHORT_LABEL.get(key, key))
            bar_rows.append((key, title, key not in hidden_bar, True))
        for key in DEFAULT_TOPBAR_ORDER:
            if key not in {r[0] for r in bar_rows}:
                title = labels.get(key, TOPBAR_SHORT_LABEL.get(key, key))
                bar_rows.append((key, title, key not in hidden_bar, True))

        if ui_mode == "modern":
            bar_rows = [row for row in bar_rows if row[0] in MODERN_HEADER_CHIP_KEYS]

        topbar_intro = (
            "View, HUD, and Layout in the Modern global header."
            if ui_mode == "modern"
            else "Tiles on the survey top bar (Presets, HUD, Layout, …). "
            "You can also drag tiles on the live bar."
        )
        topbar_legend = (
            "↑ ↓ reorder header cluster. Checkbox = show in header. View cannot be hidden."
            if ui_mode == "modern"
            else "↑ ↓ reorder. Checkbox = show on the top bar. View cannot be hidden."
        )
        self._topbar_page = _EditorListPage(
            topbar_intro,
            legend=topbar_legend,
        )
        self._topbar_page.set_rows(bar_rows, locked_keys=frozenset({"view"}))
        self._tabs.addTab(
            self._topbar_page,
            "Header" if ui_mode == "modern" else "Top bar",
        )

        self._connect_page: Optional[_EditorListPage] = None
        self._connect_toolbar_page: Optional[_EditorListPage] = None
        if getattr(win, "_connect_panel_widgets", None):
            ui_mode = getattr(win, "_ui_mode", "standard")
            connect_rows = build_connect_panel_editor_rows(ui_mode)
            self._connect_page = _EditorListPage(
                "Collapsible blocks on the Connect tab.",
                legend="↑ ↓ reorder. Checkbox = show section. "
                "Run bridge and Serial & network are always on.",
            )
            self._connect_page.set_tab_rows(
                connect_rows,
                locked_keys=REQUIRED_CONNECT_PANELS,
            )
            self._tabs.addTab(self._connect_page, "Connect")

            self._connect_toolbar_page = _EditorListPage(
                "Buttons on the right above Connect (UI editor, Expand all, …).",
                legend="↑ ↓ reorder button positions. All buttons stay visible.",
            )
            self._connect_toolbar_page.set_tab_rows(
                build_connect_toolbar_rows(ui_mode),
                locked_keys=frozenset(CONNECT_TOOLBAR_KEYS),
            )
            self._tabs.addTab(self._connect_toolbar_page, "Toolbar")

        self._main_tabs_page: Optional[_EditorListPage] = None
        catalog = getattr(win, "_tab_catalog", {}).get("main_tabs", {})
        if catalog:
            tabs_key = "main_tabs"
            hidden_tabs = set(getattr(win, "_tab_hidden", {}).get(tabs_key, set()))
            tab_rows = build_main_tab_editor_rows(
                catalog, hidden_tabs, ui_mode=ui_mode, tabs_key=tabs_key
            )
            main_intro = (
                "Tabs under the top bar: Activity, Control, Tools."
                if ui_mode == "modern"
                else "Tabs under the top bar: Connect, Log, Tools."
            )
            self._main_tabs_page = _EditorListPage(
                main_intro,
                legend="↑ ↓ reorder. Checkbox = show tab. At least one tab must stay on.",
            )
            self._main_tabs_page.set_tab_rows(tab_rows)
            self._tabs.addTab(self._main_tabs_page, "Main tabs")

        self._tools_tabs_page: Optional[_EditorListPage] = None
        tools_catalog = getattr(win, "_tab_catalog", {}).get("tools_tabs", {})
        if tools_catalog:
            tabs_key = "tools_tabs"
            hidden_tabs = set(getattr(win, "_tab_hidden", {}).get(tabs_key, set()))
            tab_rows = build_main_tab_editor_rows(
                tools_catalog, hidden_tabs, ui_mode=ui_mode, tabs_key=tabs_key
            )
            tools_intro = (
                "Chip rail and sidebar pages (Control, Presets, Hub, Logging ▾, Bench Tools ▾). "
                "Applies to both View → Tools navigation modes."
                if ui_mode == "modern"
                else (
                    "Sidebar inside the Tools main tab (Presets, Phone, NMEA, …)."
                    if ui_mode == "standard"
                    else "Tabs inside the Field Tools drawer."
                )
            )
            tools_tab_label = "Navigation" if ui_mode == "modern" else "Tools tabs"
            self._tools_tabs_page = _EditorListPage(
                tools_intro,
                legend="↑ ↓ reorder. Checkbox = show in navigation. At least one item must stay on.",
            )
            self._tools_tabs_page.set_tab_rows(tab_rows)
            self._tabs.addTab(self._tools_tabs_page, tools_tab_label)

        btn_row = QtWidgets.QHBoxLayout()
        btn_defaults = QtWidgets.QPushButton("Restore defaults")
        btn_defaults.setToolTip("Reset the current tab to recommended defaults.")
        btn_defaults.clicked.connect(self._restore_defaults)
        btn_row.addWidget(btn_defaults)
        btn_row.addStretch(1)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        root.addLayout(btn_row)

        if 0 <= initial_tab < self._tabs.count():
            self._tabs.setCurrentIndex(initial_tab)

    def _restore_defaults(self) -> None:
        ui_mode = getattr(self._win, "_ui_mode", "standard")
        if ui_mode == "modern":
            bar_rows = [
                (key, TOP_BAR_CHIP_LABELS.get(key, TOPBAR_SHORT_LABEL.get(key, key)), True, True)
                for key in ("view", "hud", "ui_switch")
            ]
        else:
            bar_rows = []
            for key in DEFAULT_TOPBAR_ORDER:
                title = TOP_BAR_CHIP_LABELS.get(key, TOPBAR_SHORT_LABEL.get(key, key))
                visible = key not in DEFAULT_TOPBAR_HIDDEN_CHIPS
                bar_rows.append((key, title, visible, True))
        self._topbar_page.set_rows(bar_rows, locked_keys=frozenset({"view"}))
        if self._connect_page is not None:
            restore_connect_panel_layout(self._win)
            ui_mode = getattr(self._win, "_ui_mode", "standard")
            prefs = load_connect_panel_prefs(ui_mode)
            save_connect_panel_prefs(
                ui_mode,
                list(prefs.get("order", [])),
                dict(prefs.get("collapsed", {})),
                sizes=dict(prefs.get("sizes", {})),
                hidden=list(prefs.get("hidden", [])),
                toolbar_order=list(CONNECT_TOOLBAR_KEYS),
            )
            self._connect_page.set_tab_rows(
                build_connect_panel_editor_rows(ui_mode),
                locked_keys=REQUIRED_CONNECT_PANELS,
            )
        if self._connect_toolbar_page is not None:
            ui_mode = getattr(self._win, "_ui_mode", "standard")
            self._connect_toolbar_page.set_tab_rows(
                build_connect_toolbar_rows(ui_mode),
                locked_keys=frozenset(CONNECT_TOOLBAR_KEYS),
            )
        if self._main_tabs_page is not None:
            catalog = getattr(self._win, "_tab_catalog", {}).get("main_tabs", {})
            ui_mode = getattr(self._win, "_ui_mode", "standard")
            if ui_mode == "modern":
                default_names = ["Activity", "Control", "Tools"]
            else:
                default_names = list(catalog.keys())
            tab_rows = [
                (name, name, MAIN_TAB_HINTS.get(name, ""), True, True)
                for name in default_names
                if name in catalog
            ]
            self._main_tabs_page.set_tab_rows(tab_rows)
        if self._tools_tabs_page is not None:
            catalog = getattr(self._win, "_tab_catalog", {}).get("tools_tabs", {})
            ui_mode = getattr(self._win, "_ui_mode", "standard")
            if ui_mode == "modern":
                from ui.tool_tabs import build_modern_tools_nav

                default_names = [lbl for _sid, lbl, _icon in build_modern_tools_nav()]
            else:
                default_names = list(catalog.keys())
            tab_rows = [
                (name, name, MAIN_TAB_HINTS.get(name, ""), True, True)
                for name in default_names
                if name in catalog
            ]
            self._tools_tabs_page.set_tab_rows(tab_rows)

    def _apply_tab_visibility(
        self,
        win: QtWidgets.QWidget,
        *,
        tabs_key: str,
        tab_order: list[str],
        tab_hidden: list[str],
        tab_label: str,
    ) -> bool:
        catalog = getattr(win, "_tab_catalog", {}).get(tabs_key, {})
        all_labels = set(catalog.keys())
        hidden_labels = {lbl for lbl in tab_hidden if lbl in all_labels}
        if len(all_labels) - len(hidden_labels) < 1 and all_labels:
            QtWidgets.QMessageBox.warning(
                self,
                "UI editor",
                f"At least one {tab_label} must remain visible.",
            )
            return False
        win._tab_hidden[tabs_key] = hidden_labels  # type: ignore[attr-defined]
        visible_order = dedupe_preserve_order(
            [
                lbl
                for lbl in tab_order
                if lbl in all_labels and lbl not in hidden_labels
            ]
        )
        if visible_order:
            save_tab_order(getattr(win, "_ui_mode", "standard"), tabs_key, visible_order)
        if tabs_key == "tools_tabs" and getattr(win, "_tools_nav_buttons", None) is not None:
            if hasattr(win, "_rebuild_modern_tools_nav_from_state"):
                try:
                    win._rebuild_modern_tools_nav_from_state(tabs_key)  # type: ignore[attr-defined]
                    if hasattr(win, "_persist_modern_tools_nav_state"):
                        win._persist_modern_tools_nav_state(tabs_key)  # type: ignore[attr-defined]
                except Exception as exc:
                    if hasattr(win, "_log_ui"):
                        win._log_ui(
                            f"[UI editor] Modern Tools sidebar rebuild failed: {exc}"
                        )  # type: ignore[attr-defined]
                    return False
            return True
        if tabs_key == "tools_tabs" and getattr(win, "_tools_nav", None) is not None:
            if hasattr(win, "_rebuild_tools_nav_from_state"):
                try:
                    win._rebuild_tools_nav_from_state(tabs_key)  # type: ignore[attr-defined]
                    if hasattr(win, "_persist_tools_nav_state"):
                        win._persist_tools_nav_state(tabs_key)  # type: ignore[attr-defined]
                except Exception as exc:
                    if hasattr(win, "_log_ui"):
                        win._log_ui(
                            f"[UI editor] Tools sidebar rebuild failed: {exc}"
                        )  # type: ignore[attr-defined]
                    return False
            return True
        modern_main = getattr(win, "_modern_main_tabs", None)
        if tabs_key == "main_tabs" and modern_main is not None and hasattr(
            win, "_rebuild_modern_main_tabs_from_state"
        ):
            try:
                win._rebuild_modern_main_tabs_from_state()  # type: ignore[attr-defined]
                if hasattr(win, "_persist_tab_state"):
                    win._persist_tab_state(modern_main, tabs_key)  # type: ignore[attr-defined]
            except Exception as exc:
                if hasattr(win, "_log_ui"):
                    win._log_ui(
                        f"[UI editor] Modern main tab rebuild failed: {exc}"
                    )  # type: ignore[attr-defined]
                return False
            return True
        tabs = (
            getattr(win, "_main_tabs", None)
            if tabs_key == "main_tabs"
            else getattr(win, "_drawer_tabs", None)
        )
        if tabs is not None and hasattr(win, "_rebuild_tabs_from_state"):
            try:
                win._rebuild_tabs_from_state(tabs, tabs_key)  # type: ignore[attr-defined]
                if hasattr(win, "_persist_tab_state"):
                    win._persist_tab_state(tabs, tabs_key)  # type: ignore[attr-defined]
            except Exception as exc:
                if hasattr(win, "_log_ui"):
                    win._log_ui(f"[UI editor] Tab rebuild failed ({tabs_key}): {exc}")  # type: ignore[attr-defined]
        return True

    def _apply(self) -> None:
        win = self._win
        ui_mode = getattr(win, "_ui_mode", "standard")
        order, hidden = self._topbar_page.ordered_checked()
        order = migrate_topbar_order(order)
        hidden = migrate_topbar_hidden(hidden)
        if ui_mode == "modern":
            prior_order = migrate_topbar_order(
                list(getattr(win, "_topbar_order", [])) or list(DEFAULT_TOPBAR_ORDER)
            )
            tail = [key for key in prior_order if key not in order]
            order = migrate_topbar_order([*order, *tail])
            prior_hidden = migrate_topbar_hidden(getattr(win, "_topbar_hidden", set()))
            hidden = migrate_topbar_hidden(prior_hidden | hidden)
        bar = getattr(win, "_survey_top_bar", None)
        if bar is not None:
            weights = bar.chip_weights()
            bar.set_prefs(order, hidden, weights)
            win._topbar_order = list(order)  # type: ignore[attr-defined]
            win._topbar_hidden = set(hidden)  # type: ignore[attr-defined]
            if hasattr(win, "_save_top_bar_prefs"):
                win._save_top_bar_prefs()  # type: ignore[attr-defined]
            if ui_mode == "modern" and hasattr(win, "_sync_modern_embedded_topbar_chrome"):
                win._sync_modern_embedded_topbar_chrome(bar)  # type: ignore[attr-defined]

        if self._connect_page is not None:
            panel_order, panel_hidden = self._connect_page.ordered_checked()
            hidden_list = sanitize_connect_panel_hidden(panel_hidden)
            visible = [
                k
                for k in panel_order
                if k in CONNECT_PANEL_KEYS and k not in hidden_list
            ]
            if not visible:
                QtWidgets.QMessageBox.warning(
                    self,
                    "UI editor",
                    "At least one Connect section must remain visible.",
                )
                return
            ui_mode = getattr(win, "_ui_mode", "standard")
            prefs = load_connect_panel_prefs(ui_mode)
            from ui.connect_panels import connect_panel_layout_changed

            if connect_panel_layout_changed(panel_order, hidden_list, prefs):
                save_connect_panel_prefs(
                    ui_mode,
                    [k for k in panel_order if k in CONNECT_PANEL_KEYS],
                    dict(prefs.get("collapsed", {})),
                    sizes=dict(prefs.get("sizes", {})),
                    hidden=hidden_list,
                    toolbar_order=list(prefs.get("toolbar_order", [])),
                )
                try:
                    _rebuild_connect_panels(win)
                    from ui.connect_panels import (
                        _schedule_connect_splitter_sizes,
                        sync_connect_panel_layout,
                    )
                    from ui.connect_row_style import apply_connect_row_style

                    apply_connect_row_style(win)
                    sync_connect_panel_layout(win)
                    _schedule_connect_splitter_sizes(win)
                except Exception as exc:
                    if hasattr(win, "_log_ui"):
                        win._log_ui(
                            f"[UI editor] Connect panel rebuild failed: {exc}"
                        )  # type: ignore[attr-defined]
        if self._connect_toolbar_page is not None:
            toolbar_order, _unused_hidden = self._connect_toolbar_page.ordered_checked()
            ui_mode = getattr(win, "_ui_mode", "standard")
            prefs = load_connect_panel_prefs(ui_mode)
            from ui.connect_panels import connect_toolbar_order_changed

            if connect_toolbar_order_changed(toolbar_order, prefs):
                save_connect_panel_prefs(
                    ui_mode,
                    list(prefs.get("order", [])),
                    dict(prefs.get("collapsed", {})),
                    sizes=dict(prefs.get("sizes", {})),
                    hidden=list(prefs.get("hidden", [])),
                    toolbar_order=[k for k in toolbar_order if k in CONNECT_TOOLBAR_KEYS],
                )
                from ui.connect_panels import apply_connect_toolbar_order

                try:
                    apply_connect_toolbar_order(win)
                except Exception as exc:
                    if hasattr(win, "_log_ui"):
                        win._log_ui(
                            f"[UI editor] Connect toolbar rebuild failed: {exc}"
                        )  # type: ignore[attr-defined]

        if self._main_tabs_page is not None:
            tab_order, tab_hidden = self._main_tabs_page.ordered_checked()
            if not self._apply_tab_visibility(
                win,
                tabs_key="main_tabs",
                tab_order=tab_order,
                tab_hidden=tab_hidden,
                tab_label="main tab",
            ):
                return

        if self._tools_tabs_page is not None:
            tab_order, tab_hidden = self._tools_tabs_page.ordered_checked()
            if not self._apply_tab_visibility(
                win,
                tabs_key="tools_tabs",
                tab_order=tab_order,
                tab_hidden=tab_hidden,
                tab_label="Tools tab",
            ):
                return

        if hasattr(win, "_log_ui"):
            win._log_ui("[UI] Layout updated.")  # type: ignore[attr-defined]
        if ui_mode == "modern":
            if hasattr(win, "_ensure_modern_nav_visible"):
                win._ensure_modern_nav_visible()  # type: ignore[attr-defined]
        self.accept()

    def select_tab(self, name: str) -> None:
        for i in range(self._tabs.count()):
            if self._tabs.tabText(i) == name:
                self._tabs.setCurrentIndex(i)
                return


def open_ui_editor(
    win: QtWidgets.QWidget,
    *,
    initial_tab: int = 0,
    focus: str = "",
) -> None:
    """Show the layout editor (top bar, Connect sections, main tabs)."""
    dlg = UiEditorDialog(win, initial_tab=initial_tab, parent=win)
    if focus == "connect":
        dlg.select_tab("Connect")
    elif focus == "tabs":
        dlg.select_tab("Main tabs")
    elif focus == "tools":
        dlg.select_tab("Navigation")
        if dlg._tabs.count() and dlg._tabs.tabText(0) != "Navigation":
            dlg.select_tab("Tools tabs")
    dlg.exec()


def open_connect_panel_editor(win: QtWidgets.QWidget) -> None:
    open_ui_editor(win, focus="connect")

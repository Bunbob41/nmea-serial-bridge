"""Workspace UI editor — top bar tiles, Connect sections, and main tabs."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.collapsible import enable_dialog_content_fit, reflow_window
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
from ui.survey_top_bar import DEFAULT_TOPBAR_ORDER, TOPBAR_SHORT_LABEL
from ui.ui_prefs import (
    load_connect_panel_prefs,
    load_tab_order,
    save_connect_panel_prefs,
    save_tab_order,
)

# Friendly names for top-bar chips (key → title).
TOP_BAR_CHIP_LABELS: dict[str, str] = {
    "view": "View menu",
    "presets": "Presets",
    "recent": "Recent sessions",
    "hud": "Survey HUD",
    "tools": "Tools drawer",
    "hidden_tabs": "Hidden tabs",
    "randomize_theme": "Randomize theme",
    "standardize_theme": "Standardize theme",
    "ui_editor": "UI editor",
    "shortcuts": "Shortcuts legend",
    "copy_stats": "Copy stats",
    "ui_switch": "Layout (double-click toggles Standard / Field)",
}

# Short descriptions for main-window tabs (catalog stores tooltips, often empty at build).
CONNECT_PANEL_HINTS: dict[str, str] = {
    "run": "Start/Stop, bench preset, status banner",
    "hint": "Intent / preset guidance line",
    "quick_log": "Compact live log on Connect",
    "quick_terminal": "Bench output on Connect",
    "connection": "COM, baud, UDP/TCP listen",
    "ntrip": "Optional caster corrections (mux to serial)",
}
CONNECT_TOOLBAR_HINTS: dict[str, str] = {
    "ui_editor": "Open layout/visibility editor for tabs and Connect sections",
    "expand_all": "Expand every Connect section",
    "collapse_all": "Collapse every Connect section",
    "reset_sizes": "Reset Connect splitter heights to defaults",
}

MAIN_TAB_HINTS: dict[str, str] = {
    "Connect": "COM, UDP/TCP, Start/Stop, collapsible panels",
    "Log": "Live bridge log, presets, pause, clear, save",
    "Presets": "Named COM/UDP presets and boat LAN reference",
    "NMEA": "Passthrough, strict filter, or raw binary",
    "Theme": "Colors, randomize, favorites, seed lock",
    "Guide": "Transparent usage notes, strengths, and current limitations",
    "Terminal": "Inject test NMEA to serial or network",
    "Diagnostics": "File log, bench/boat checklists, layout tools",
}

# First-launch top bar: hide theme toys; keep editor visible.
DEFAULT_TOPBAR_HIDDEN_CHIPS: frozenset[str] = frozenset(
    {"randomize_theme", "standardize_theme"}
)

_LIST_OBJECT = "uiEditorList"
_ROW_MIN_H = 34


def migrate_topbar_order(order: list[str]) -> list[str]:
    """Drop removed chips; map legacy demo → ui_editor."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in order:
        key = "ui_editor" if str(raw).strip() == "demo" else str(raw).strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    for key in DEFAULT_TOPBAR_ORDER:
        if key not in seen:
            out.append(key)
            seen.add(key)
    return out


def migrate_topbar_hidden(hidden: set[str] | list[str]) -> set[str]:
    h = {str(x).strip() for x in hidden if str(x).strip()}
    h.discard("demo")
    h.discard("view")
    return h


def build_main_tab_editor_rows(
    catalog: dict[str, tuple[QtWidgets.QWidget, str]],
    hidden: set[str],
    *,
    ui_mode: str = "standard",
    tabs_key: str = "main_tabs",
) -> list[tuple[str, str, str, bool, bool]]:
    """Build list rows: (id, title, subtitle, visible, enabled)."""
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
    """Connect splitter sections: (id, title, subtitle, visible, enabled)."""
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


def _configure_editor_list(list_widget: QtWidgets.QListWidget) -> None:
    list_widget.setObjectName(_LIST_OBJECT)
    list_widget.setSpacing(2)
    list_widget.setAlternatingRowColors(True)
    list_widget.setMinimumHeight(160)


class _EditorListPage(QtWidgets.QWidget):
    """Reorderable checklist with visible labels and optional subtitles."""

    def __init__(
        self,
        intro: str,
        *,
        legend: str = "Drag rows to reorder. Checkbox = show in the UI.",
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
        self.list = QtWidgets.QListWidget()
        _configure_editor_list(self.list)
        lay.addWidget(self.list, 1)

    def set_rows(
        self,
        rows: list[tuple[str, str, bool, bool]],
        *,
        locked_keys: frozenset[str] = frozenset(),
        subtitles: dict[str, str] | None = None,
    ) -> None:
        """rows: (id, label, checked, enabled). Optional subtitles keyed by id."""
        self.list.clear()
        subs = subtitles or {}
        for key, label, checked, enabled in rows:
            sub = subs.get(key, "").strip()
            display = label if not sub else f"{label} — {sub}"
            item = QtWidgets.QListWidgetItem(display)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, key)
            flags = item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable
            if key in locked_keys:
                flags &= ~QtCore.Qt.ItemFlag.ItemIsUserCheckable
                item.setToolTip("Always shown")
            else:
                item.setToolTip(sub or f"Show «{label}» in the UI")
            item.setFlags(flags)
            item.setCheckState(
                QtCore.Qt.CheckState.Checked if checked else QtCore.Qt.CheckState.Unchecked
            )
            if not enabled:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEnabled)
            item.setSizeHint(QtCore.QSize(0, _ROW_MIN_H + (12 if sub else 0)))
            self.list.addItem(item)

    def set_tab_rows(
        self,
        rows: list[tuple[str, str, str, bool, bool]],
        *,
        locked_keys: frozenset[str] = frozenset(),
    ) -> None:
        """rows: (id, title, subtitle, visible, enabled)."""
        self.list.clear()
        for key, title, subtitle, visible, enabled in rows:
            display = title if not subtitle.strip() else f"{title} — {subtitle.strip()}"
            item = QtWidgets.QListWidgetItem(display)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, key)
            flags = item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable
            if key in locked_keys:
                flags &= ~QtCore.Qt.ItemFlag.ItemIsUserCheckable
                item.setToolTip("Always shown")
            else:
                item.setToolTip(subtitle.strip() or f"Show the «{title}» tab")
            item.setFlags(flags)
            item.setCheckState(
                QtCore.Qt.CheckState.Checked if visible else QtCore.Qt.CheckState.Unchecked
            )
            if not enabled:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEnabled)
            item.setSizeHint(QtCore.QSize(0, _ROW_MIN_H + (12 if subtitle.strip() else 0)))
            self.list.addItem(item)

    def ordered_checked(self) -> tuple[list[str], set[str]]:
        order: list[str] = []
        hidden: set[str] = set()
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item is None:
                continue
            key = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "").strip()
            if not key:
                continue
            order.append(key)
            if item.checkState() != QtCore.Qt.CheckState.Checked:
                hidden.add(key)
        return order, hidden


# Back-compat alias
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
        self.resize(520, 480)
        root = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel(
            "Drag rows to reorder. Checkbox = show in the UI. "
            "Click <b>OK</b> to apply; <b>Restore defaults</b> resets the current tab."
        )
        intro.setWordWrap(True)
        intro.setObjectName("tabHint")
        root.addWidget(intro)

        self._tabs = QtWidgets.QTabWidget()
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

        self._topbar_page = _EditorListPage(
            "Top bar quick tiles (Standard, Field, Log-first). "
            "You can also drag tiles on the bar itself.",
            legend="Checkbox = show on the survey top bar. View is always visible.",
        )
        self._topbar_page.set_rows(bar_rows, locked_keys=frozenset({"view"}))
        self._tabs.addTab(self._topbar_page, "Top bar")

        self._connect_page: Optional[_EditorListPage] = None
        self._connect_toolbar_page: Optional[_EditorListPage] = None
        if getattr(win, "_connect_panel_widgets", None):
            ui_mode = getattr(win, "_ui_mode", "standard")
            connect_rows = build_connect_panel_editor_rows(ui_mode)
            self._connect_page = _EditorListPage(
                "Connect tab sections (Standard layout). "
                "Hide optional blocks you do not need; drag to reorder.",
                legend="Checkbox = section visible. Run bridge and Serial & network always stay on.",
            )
            self._connect_page.set_tab_rows(
                connect_rows,
                locked_keys=REQUIRED_CONNECT_PANELS,
            )
            self._tabs.addTab(self._connect_page, "Connect")
            self._connect_toolbar_page = _EditorListPage(
                "Connect toolbar buttons above the sections.",
                legend="Drag rows to reorder button positions (all remain visible).",
            )
            self._connect_toolbar_page.set_tab_rows(
                build_connect_toolbar_rows(ui_mode),
                locked_keys=frozenset(CONNECT_TOOLBAR_KEYS),
            )
            self._tabs.addTab(self._connect_toolbar_page, "Connect toolbar")

        self._main_tabs_page: Optional[_EditorListPage] = None
        catalog = getattr(win, "_tab_catalog", {}).get("main_tabs", {})
        if catalog:
            tabs_key = getattr(win, "_primary_tabs_key", None) or "main_tabs"
            hidden_tabs = set(getattr(win, "_tab_hidden", {}).get(tabs_key, set()))
            ui_mode = getattr(win, "_ui_mode", "standard")
            tab_rows = build_main_tab_editor_rows(
                catalog, hidden_tabs, ui_mode=ui_mode, tabs_key=tabs_key
            )
            self._main_tabs_page = _EditorListPage(
                "Main window tabs below the survey top bar. "
                "Hide tabs you rarely use (e.g. Theme) to reduce clutter.",
                legend="Checkbox = tab visible. At least one tab must stay on.",
            )
            self._main_tabs_page.set_tab_rows(tab_rows)
            self._tabs.addTab(self._main_tabs_page, "Main tabs")

        btn_row = QtWidgets.QHBoxLayout()
        btn_defaults = QtWidgets.QPushButton("Restore defaults")
        btn_defaults.setToolTip("Reset this workspace to the recommended survey layout.")
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

        enable_dialog_content_fit(self, min_width=460)
        if 0 <= initial_tab < self._tabs.count():
            self._tabs.setCurrentIndex(initial_tab)

    def _restore_defaults(self) -> None:
        bar_rows: list[tuple[str, str, bool, bool]] = []
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
            tab_rows = [
                (name, name, MAIN_TAB_HINTS.get(name, ""), True, True)
                for name in catalog
            ]
            self._main_tabs_page.set_tab_rows(tab_rows)

    def _apply(self) -> None:
        win = self._win
        order, hidden = self._topbar_page.ordered_checked()
        order = migrate_topbar_order(order)
        hidden = migrate_topbar_hidden(hidden)
        bar = getattr(win, "_survey_top_bar", None)
        if bar is not None:
            weights = bar.chip_weights()
            bar.set_prefs(order, hidden, weights)
            win._topbar_order = list(order)  # type: ignore[attr-defined]
            win._topbar_hidden = set(hidden)  # type: ignore[attr-defined]
            if hasattr(win, "_save_top_bar_prefs"):
                win._save_top_bar_prefs()  # type: ignore[attr-defined]

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
            save_connect_panel_prefs(
                ui_mode,
                [k for k in panel_order if k in CONNECT_PANEL_KEYS],
                dict(prefs.get("collapsed", {})),
                hidden=hidden_list,
            )
            _rebuild_connect_panels(win)
        if self._connect_toolbar_page is not None:
            toolbar_order, _unused_hidden = self._connect_toolbar_page.ordered_checked()
            ui_mode = getattr(win, "_ui_mode", "standard")
            prefs = load_connect_panel_prefs(ui_mode)
            save_connect_panel_prefs(
                ui_mode,
                list(prefs.get("order", [])),
                dict(prefs.get("collapsed", {})),
                sizes=dict(prefs.get("sizes", {})),
                hidden=list(prefs.get("hidden", [])),
                toolbar_order=[k for k in toolbar_order if k in CONNECT_TOOLBAR_KEYS],
            )
            from ui.connect_panels import apply_connect_toolbar_order

            apply_connect_toolbar_order(win)

        if self._main_tabs_page is not None:
            tab_order, tab_hidden = self._main_tabs_page.ordered_checked()
            catalog = getattr(win, "_tab_catalog", {}).get("main_tabs", {})
            all_labels = set(catalog.keys())
            hidden_labels = {lbl for lbl in tab_hidden if lbl in all_labels}
            if len(all_labels) - len(hidden_labels) < 1 and all_labels:
                QtWidgets.QMessageBox.warning(
                    self,
                    "UI editor",
                    "At least one main tab must remain visible.",
                )
                return
            key = getattr(win, "_primary_tabs_key", None) or "main_tabs"
            win._tab_hidden[key] = hidden_labels  # type: ignore[attr-defined]
            visible_order = [lbl for lbl in tab_order if lbl in all_labels and lbl not in hidden_labels]
            if visible_order:
                save_tab_order(getattr(win, "_ui_mode", "standard"), key, visible_order)
            tabs = getattr(win, "_main_tabs", None)
            if tabs is not None and hasattr(win, "_rebuild_tabs_from_state"):
                win._rebuild_tabs_from_state(tabs, key)  # type: ignore[attr-defined]
                win._persist_tab_state(tabs, key)  # type: ignore[attr-defined]

        if hasattr(win, "_log_ui"):
            win._log_ui("[UI] Layout updated.")  # type: ignore[attr-defined]
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
    """Show the checkbox UI editor (top bar, Connect sections, main tabs)."""
    dlg = UiEditorDialog(win, initial_tab=initial_tab, parent=win)
    if focus == "connect":
        dlg.select_tab("Connect")
    elif focus == "tabs":
        dlg.select_tab("Main tabs")
    dlg.show()
    reflow_window(dlg)
    dlg.exec()


def open_connect_panel_editor(win: QtWidgets.QWidget) -> None:
    """Open UI editor on the Connect sections tab."""
    open_ui_editor(win, focus="connect")

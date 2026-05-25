"""Collapsible, reorderable, vertically resizable panels on the Standard Connect tab."""
from __future__ import annotations

import html

from PySide6 import QtCore, QtGui, QtWidgets

# Connect status strip — compact but readable (between v1.9.64 large and v1.9.65 tiny).
_STATUS_BANNER_TITLE_PT = 9.0
_STATUS_BANNER_DETAIL_PT = 8.5
_STATUS_BANNER_MAX_HEIGHT = 56


def configure_connect_status_banner(
    banner: QtWidgets.QFrame,
    label: QtWidgets.QLabel,
) -> None:
    """Compact Stopped/Running banner above Connect panels (Standard UI)."""
    banner.setMaximumHeight(_STATUS_BANNER_MAX_HEIGHT)
    label.setWordWrap(True)
    label.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    font = QtGui.QFont(label.font())
    font.setPointSizeF(_STATUS_BANNER_TITLE_PT)
    font.setWeight(QtGui.QFont.Weight.DemiBold)
    label.setFont(font)


def format_connect_status_banner_html(title: str, detail: str = "") -> str:
    t = html.escape(title.strip())
    if not detail.strip():
        return (
            f'<span style="font-size:{_STATUS_BANNER_TITLE_PT:.1f}pt;'
            f'font-weight:700;line-height:115%">{t}</span>'
        )
    d = html.escape(detail.strip())
    return (
        f'<span style="font-size:{_STATUS_BANNER_TITLE_PT:.1f}pt;'
        f'font-weight:700;line-height:115%">{t}</span><br>'
        f'<span style="font-size:{_STATUS_BANNER_DETAIL_PT:.1f}pt;'
        f'font-weight:500;line-height:115%">{d}</span>'
    )

from ui.collapsible import DisclosureRow
from ui.ui_prefs import load_connect_panel_prefs, save_connect_panel_prefs

# Retired from Connect UI (Applanix / INS workflows use internal RTK). Kept out of editor + splitter.
OMITTED_CONNECT_PANELS = frozenset({"ntrip"})

# Recommended vertical order: COM/UDP settings directly under Run (less scrolling).
RECOMMENDED_CONNECT_PANEL_ORDER: tuple[str, ...] = (
    "run",
    "connection",
    "hint",
    "quick_log",
    "quick_terminal",
)

CONNECT_PANEL_KEYS: tuple[str, ...] = RECOMMENDED_CONNECT_PANEL_ORDER

CONNECT_PANEL_LABELS: dict[str, str] = {
    "run": "Run bridge",
    "hint": "Status hint",
    "quick_log": "Quick log",
    "quick_terminal": "Quick terminal",
    "connection": "Serial & network",
}
CONNECT_PANEL_COLLAPSED_HINTS: dict[str, str] = {
    "run": "Start/Stop",
    "hint": "Current workflow guidance",
    "quick_log": "Recent bridge messages",
    "quick_terminal": "Bench script output",
    "connection": "COM, baud, UDP/TCP",
}

CONNECT_TOOLBAR_KEYS: tuple[str, ...] = (
    "ui_editor",
    "expand_all",
    "collapse_all",
)
CONNECT_TOOLBAR_LABELS: dict[str, str] = {
    "ui_editor": "UI editor…",
    "expand_all": "Expand all",
    "collapse_all": "Collapse all",
}

# Must stay in the splitter (UI editor shows them as non-toggleable).
REQUIRED_CONNECT_PANELS = frozenset({"run", "connection"})

# Optional sections hidden on Restore defaults (UI editor).
DEFAULT_CONNECT_HIDDEN: frozenset[str] = frozenset()

_DEFAULT_PANEL_HEIGHTS: dict[str, int] = {
    "run": 84,
    "hint": 48,
    "quick_log": 120,
    "quick_terminal": 120,
    "connection": 200,
}

# Ignore persisted heights below these (legacy QSplitter sizes like 26–48px).
_MIN_VALID_SAVED_HEIGHT: dict[str, int] = {
    "run": 72,
    "hint": 40,
    "quick_log": 80,
    "quick_terminal": 80,
    "connection": 160,
}

# Cap scaled height for compact sections (avoids giant Start row when alone expanded).
_PANEL_EXPANDED_CAP: dict[str, int] = {
    "run": 120,   # Start + Stop buttons (36px each) + fan-out checkbox + margins
    "hint": 64,
    "quick_log": 220,
    "quick_terminal": 220,
    "connection": 260,
}


def _filter_connect_panel_order(order: list[str]) -> list[str]:
    return [k for k in order if k in CONNECT_PANEL_KEYS and k not in OMITTED_CONNECT_PANELS]

# Collapsed disclosure strip must fit rounded header padding/text.
_COLLAPSED_STRIP_HEIGHT = 48
_CONNECT_STACK_SPACING = 2
# Legacy splitter constants (tests / persisted size math).
_CONNECT_SPLITTER_HANDLE = 8
_CONNECT_SPLITTER_HANDLE_COMPACT = 2
_WIDGET_SIZE_MAX = 16777215
_STANDARD_CONNECT_WINDOW_HEIGHT = 520


def expand_connect_panel(win: QtWidgets.QWidget, key: str) -> None:
    """Expand one Connect section (e.g. quick terminal for bench setup output)."""
    disclosures: dict[str, DisclosureRow] = getattr(win, "_connect_panel_disclosures", {})
    row = disclosures.get(key)
    if row is None:
        return
    row.set_expanded(True)
    _apply_row_expand_style(row, True, sole_expanded=False)
    if not getattr(win, "_connect_panel_syncing", False):
        QtCore.QTimer.singleShot(0, lambda w=win: _apply_connect_splitter_sizes(w))


def _connect_panel_display_title(key: str) -> str:
    base = CONNECT_PANEL_LABELS.get(key, key)
    hint = CONNECT_PANEL_COLLAPSED_HINTS.get(key, "").strip()
    return base if not hint else f"{base}  |  {hint}"


def _configure_connect_disclosure_row(row: DisclosureRow) -> None:
    """Stylesheet backgrounds need AutoRaise off on Connect disclosure headers."""
    btn = row.tool_button()
    btn.setAutoRaise(False)
    btn.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    row.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)


def sync_connect_panel_layout(win: QtWidgets.QWidget) -> None:
    """Refresh Connect scroll/QR geometry when the tab becomes active (keep panel sizes)."""
    stack: QtWidgets.QWidget | None = getattr(win, "_connect_panel_stack", None)
    if stack is None:
        return
    _apply_connect_panel_layout(win)
    from ui.connect_qr_overlay import schedule_refresh_connect_qr_overlay

    schedule_refresh_connect_qr_overlay(win)


def apply_connect_toolbar_order(win: QtWidgets.QWidget) -> None:
    lay: QtWidgets.QHBoxLayout | None = getattr(win, "_connect_toolbar_layout", None)
    buttons: dict[str, QtWidgets.QPushButton] = getattr(win, "_connect_toolbar_buttons", {})
    if lay is None or not isinstance(buttons, dict):
        return
    prefs = load_connect_panel_prefs(getattr(win, "_ui_mode", "standard"))
    order = [k for k in prefs.get("toolbar_order", []) if k in buttons]
    for key in CONNECT_TOOLBAR_KEYS:
        if key not in order:
            order.append(key)
    for key in order:
        lay.removeWidget(buttons[key])
        lay.addWidget(buttons[key])


def mount_connect_tab_chrome(
    win: QtWidgets.QWidget,
    *,
    subtitle: str,
    banner: QtWidgets.QWidget,
) -> None:
    """Pin version line + status banner above Connect panels (not inside Serial & network)."""
    lay: QtWidgets.QVBoxLayout | None = getattr(win, "_connect_tab_layout", None)
    if lay is None:
        return
    chrome = QtWidgets.QWidget()
    chrome.setObjectName("connectTabChrome")
    chrome.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    chrome_lay = QtWidgets.QVBoxLayout(chrome)
    chrome_lay.setContentsMargins(10, 4, 10, 2)
    chrome_lay.setSpacing(4)
    sub = QtWidgets.QLabel(subtitle)
    sub.setObjectName("appSubtitle")
    sub.setWordWrap(True)
    chrome_lay.addWidget(sub)
    chrome_lay.addWidget(banner)
    lay.insertWidget(1, chrome)
    win._connect_tab_chrome = chrome


def setup_connect_tab_panels(
    win: QtWidgets.QWidget,
    connect_tab: QtWidgets.QWidget,
    panels: dict[str, QtWidgets.QWidget],
) -> None:
    """Mount collapsible panels on Connect tab; call after all panel widgets exist on win."""
    win._connect_tab_widget = connect_tab
    lay = QtWidgets.QVBoxLayout(connect_tab)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    win._connect_tab_layout = lay

    tool_row = QtWidgets.QHBoxLayout()
    btn_ui_editor = QtWidgets.QPushButton(CONNECT_TOOLBAR_LABELS["ui_editor"])
    btn_ui_editor.setToolTip(
        "Reorder or hide Connect sections, top bar chips, and main tabs (checkbox dialog)."
    )
    btn_ui_editor.clicked.connect(lambda: _open_connect_ui_editor(win))
    btn_expand = QtWidgets.QPushButton(CONNECT_TOOLBAR_LABELS["expand_all"])
    btn_expand.clicked.connect(lambda: _set_all_connect_panels(win, True))
    btn_collapse = QtWidgets.QPushButton(CONNECT_TOOLBAR_LABELS["collapse_all"])
    btn_collapse.clicked.connect(lambda: _set_all_connect_panels(win, False))
    toolbar_buttons: dict[str, QtWidgets.QPushButton] = {
        "ui_editor": btn_ui_editor,
        "expand_all": btn_expand,
        "collapse_all": btn_collapse,
    }
    prefs = load_connect_panel_prefs(getattr(win, "_ui_mode", "standard"))
    toolbar_order = [k for k in prefs.get("toolbar_order", []) if k in toolbar_buttons]
    for key in CONNECT_TOOLBAR_KEYS:
        if key not in toolbar_order:
            toolbar_order.append(key)
    # Stretch at the front pushes all buttons to the right edge of the toolbar row.
    tool_row.addStretch(1)
    for key in toolbar_order:
        tool_row.addWidget(toolbar_buttons[key])
    lay.addLayout(tool_row)
    win._connect_toolbar_buttons = toolbar_buttons
    win._connect_toolbar_layout = tool_row

    host = QtWidgets.QWidget()
    host.setObjectName("connectPanelHost")
    host.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    host.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Preferred,
    )
    host_lay = QtWidgets.QVBoxLayout(host)
    host_lay.setContentsMargins(6, 0, 6, 6)
    host_lay.setSpacing(0)

    stack = QtWidgets.QWidget()
    stack.setObjectName("connectPanelStack")
    stack.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    stack_lay = QtWidgets.QVBoxLayout(stack)
    stack_lay.setContentsMargins(0, 0, 0, 0)
    stack_lay.setSpacing(_CONNECT_STACK_SPACING)
    host_lay.addWidget(stack, 0)

    panel_page = QtWidgets.QWidget()
    panel_page.setObjectName("connectMainScrollHost")
    panel_page.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    panel_page.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Minimum,
    )
    page_lay = QtWidgets.QVBoxLayout(panel_page)
    page_lay.setContentsMargins(0, 0, 0, 0)
    page_lay.setSpacing(0)
    page_lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    page_lay.addWidget(host, 0)

    panel_scroll = QtWidgets.QScrollArea()
    panel_scroll.setObjectName("connectMainScroll")
    panel_scroll.setWidgetResizable(True)
    panel_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    panel_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    panel_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    panel_scroll.setFocusPolicy(QtCore.Qt.FocusPolicy.WheelFocus)
    panel_scroll.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    panel_scroll.viewport().setObjectName("connectMainScrollViewport")
    panel_scroll.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    # Permanently Expanding — never switched to Fixed; native scrollbar handles overflow.
    panel_scroll.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Expanding,
    )
    panel_scroll.setWidget(panel_page)
    lay.addWidget(panel_scroll, 1)

    class _ConnectScrollViewportFilter(QtCore.QObject):
        def __init__(self, bridge: QtWidgets.QWidget) -> None:
            super().__init__(bridge)
            self._bridge = bridge

        def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
            if event.type() != QtCore.QEvent.Type.Resize:
                return False
            page = getattr(self._bridge, "_connect_panel_page", None)
            scroll = getattr(self._bridge, "_connect_panel_scroll", None)
            if page is None or scroll is None or watched is not scroll.viewport():
                return False
            disclosures = getattr(self._bridge, "_connect_panel_disclosures", {})
            order = getattr(self._bridge, "_connect_panel_order", [])
            if _expanded_panel_count(disclosures, order) > 0:
                _ensure_connect_scroll_full_width(self._bridge)
            return False

    win._connect_scroll_viewport_filter = _ConnectScrollViewportFilter(win)
    panel_scroll.viewport().installEventFilter(win._connect_scroll_viewport_filter)

    win._connect_panel_host = host
    win._connect_panel_host_lay = host_lay
    win._connect_panel_page = panel_page
    win._connect_panel_scroll = panel_scroll
    win._connect_page_in_main_scroll = True
    win._connect_panel_widgets = dict(panels)
    win._connect_panel_stack = stack
    win._connect_panel_stack_lay = stack_lay
    win._connect_panel_stretch_item = None
    # Legacy alias (specs/tests); points at the vertical panel stack, not a QSplitter.
    win._connect_panel_splitter = stack
    win._connect_panel_disclosures: dict[str, DisclosureRow] = {}
    win._connect_panel_order: list[str] = []
    win._connect_panel_syncing = False
    if not hasattr(win, "_connect_sync_geom_timer"):
        gt = QtCore.QTimer(win)
        gt.setSingleShot(True)
        gt.timeout.connect(lambda w=win: _flush_connect_scroll_geometry(w))
        win._connect_sync_geom_timer = gt
    win._connect_sync_geom_pending = None
    _rebuild_connect_panels(win)
    from ui.connect_qr_overlay import setup_connect_qr_overlay
    from ui.connect_row_style import apply_connect_row_style

    apply_connect_row_style(win)
    setup_connect_qr_overlay(win)


def _clear_connect_panel_stack(lay: QtWidgets.QVBoxLayout) -> None:
    while lay.count():
        item = lay.takeAt(0)
        if item is None:
            continue
        w = item.widget()
        if w is not None:
            w.setParent(None)


def _rebuild_connect_panels(win: QtWidgets.QWidget) -> None:
    stack_lay: QtWidgets.QVBoxLayout | None = getattr(win, "_connect_panel_stack_lay", None)
    widgets: dict[str, QtWidgets.QWidget] = getattr(win, "_connect_panel_widgets", {})
    if stack_lay is None or not widgets:
        return
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    order = _filter_connect_panel_order([k for k in prefs.get("order", []) if k in widgets])
    for k in CONNECT_PANEL_KEYS:
        if k in widgets and k not in order:
            order.append(k)
    collapsed: dict[str, bool] = dict(prefs.get("collapsed", {}))
    saved_sizes: dict[str, int] = dict(prefs.get("sizes", {}))
    hidden_set = {
        str(x).strip()
        for x in sanitize_connect_panel_hidden(prefs.get("hidden", []))
        if str(x).strip()
    }
    visible_order = [k for k in order if k not in hidden_set]
    collapsed, saved_sizes, use_default_sizes = _normalize_connect_launch_prefs(
        collapsed, saved_sizes, visible_order
    )

    host: QtWidgets.QWidget | None = getattr(win, "_connect_panel_host", None)
    # Detach panel bodies before removing rows — orphaned DisclosureRow GC would
    # destroy QLabel/QScrollArea children still referenced on the main window.
    for key in visible_order:
        body = widgets.get(key)
        if body is not None and host is not None:
            body.setParent(host)

    _clear_connect_panel_stack(stack_lay)
    win._connect_panel_stretch_item = None

    disclosures: dict[str, DisclosureRow] = {}
    for key in visible_order:
        body = widgets.get(key)
        if body is None:
            continue
        start_open = not bool(collapsed.get(key, _default_collapsed(key)))
        row = DisclosureRow(
            _connect_panel_display_title(key),
            body,
            start_open=start_open,
            button_object_name="connectPanelDisclosure",
            fill_vertical=False,
        )
        row.setObjectName("connectPanelRow")
        row.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        row.setProperty("connectPanelKey", key)
        _configure_connect_disclosure_row(row)
        row.tool_button().toggled.connect(
            lambda on, k=key, w=win: _on_connect_panel_toggled(w, k, on)
        )
        _apply_row_expand_style(row, start_open, sole_expanded=False)
        disclosures[key] = row
        stack_lay.addWidget(row)
        row.setMinimumHeight(_COLLAPSED_STRIP_HEIGHT)

    win._connect_panel_disclosures = disclosures
    win._connect_panel_order = list(visible_order)
    # `saved_sizes` was already cleaned by _normalize_connect_launch_prefs:
    # - corrupted (zeros, all-at-strip-height) → {} so ghost state is never re-baked
    # - valid user drag heights → preserved so the layout is restored next launch
    save_connect_panel_prefs(
        ui_mode,
        order,
        collapsed,
        sizes=saved_sizes,
        hidden=list(hidden_set),
    )
    # use_default_sizes is False when valid saved sizes exist, True when they were
    # cleared by the corruption guard.  This restores the user's last layout on
    # every normal boot while still booting from defaults after a corrupted state.
    _schedule_connect_splitter_sizes(win, use_defaults=use_default_sizes)
    from ui.connect_row_style import apply_connect_row_style

    apply_connect_row_style(win)


def _default_collapsed(key: str) -> bool:
    """Compact Connect by default — only Run + Serial/network start expanded."""
    return key in {"hint", "quick_log", "quick_terminal"}


def sanitize_connect_panel_hidden(hidden: list[str] | set[str]) -> list[str]:
    """Required / omitted panels cannot be hidden (non-checkable list rows read as unchecked)."""
    return [
        k
        for k in hidden
        if k not in REQUIRED_CONNECT_PANELS and k not in OMITTED_CONNECT_PANELS
    ]


def _normalized_connect_panel_order(raw_order: list[str]) -> list[str]:
    order = _filter_connect_panel_order([str(k).strip() for k in raw_order if str(k).strip()])
    for key in CONNECT_PANEL_KEYS:
        if key not in order:
            order.append(key)
    return order


def connect_panel_layout_changed(
    panel_order: list[str],
    hidden_list: list[str] | set[str],
    prefs: dict,
) -> bool:
    """True when Connect section order or visibility changed (UI editor should rebuild)."""
    new_order = _normalized_connect_panel_order(panel_order)
    old_order = _normalized_connect_panel_order(
        [str(x) for x in prefs.get("order", []) if str(x).strip()]
    )
    new_hidden = set(sanitize_connect_panel_hidden(hidden_list))
    old_hidden = set(sanitize_connect_panel_hidden(prefs.get("hidden", [])))
    return new_order != old_order or new_hidden != old_hidden


def connect_toolbar_order_changed(toolbar_order: list[str], prefs: dict) -> bool:
    new_order = [k for k in toolbar_order if k in CONNECT_TOOLBAR_KEYS]
    for key in CONNECT_TOOLBAR_KEYS:
        if key not in new_order:
            new_order.append(key)
    old_order = [k for k in prefs.get("toolbar_order", []) if k in CONNECT_TOOLBAR_KEYS]
    for key in CONNECT_TOOLBAR_KEYS:
        if key not in old_order:
            old_order.append(key)
    return new_order != old_order


def default_connect_collapsed(order: list[str]) -> dict[str, bool]:
    return {k: _default_collapsed(k) for k in order}


def restore_connect_panel_layout(win: QtWidgets.QWidget) -> None:
    """Survey-default Connect sections: show all active panels, reset collapse and sizes."""
    widgets: dict = getattr(win, "_connect_panel_widgets", {})
    if not widgets:
        return
    ui_mode = getattr(win, "_ui_mode", "standard")
    order = [k for k in RECOMMENDED_CONNECT_PANEL_ORDER if k in widgets]
    hidden = [k for k in DEFAULT_CONNECT_HIDDEN if k in widgets]
    collapsed = default_connect_collapsed(order)
    save_connect_panel_prefs(
        ui_mode,
        order,
        collapsed,
        sizes={},
        hidden=hidden,
    )
    _rebuild_connect_panels(win)


def _panel_collapsed_in_prefs(collapsed: dict[str, bool], key: str) -> bool:
    return bool(collapsed.get(key, _default_collapsed(key)))


def _normalize_connect_launch_prefs(
    collapsed: dict[str, bool],
    sizes: dict[str, int],
    order: list[str],
) -> tuple[dict[str, bool], dict[str, int], bool]:
    """Keep saved collapse state; discard size prefs on any ghost-state signal.

    Ghost-state signals (either of these → wipe sizes and boot from defaults):
    - No sizes at all.
    - All saved expanded-panel sizes collapsed down to strip height (old crash artifact).
    - ANY saved size is 0 or negative (corrupted QSplitter state blob bled into JSON).
    """
    if not order:
        return collapsed, sizes, not bool(sizes)
    use_defaults = not sizes
    if sizes:
        # Any zero/negative value is a definitive corruption marker.
        if any(sizes.get(k, 1) <= 0 for k in order if k in sizes):
            use_defaults = True
            sizes = {}
        # All panels saved at or below the collapsed strip height → ghost state.
        elif all(
            sizes.get(k, _DEFAULT_PANEL_HEIGHTS.get(k, 80)) <= _COLLAPSED_STRIP_HEIGHT + 4
            for k in order
        ):
            use_defaults = True
            sizes = {}
        else:
            sizes = _sanitize_saved_panel_sizes(sizes)
            if not sizes:
                use_defaults = True
    return collapsed, sizes, use_defaults


def _sanitize_saved_panel_sizes(saved: dict[str, int]) -> dict[str, int]:
    """Drop strip-height and other junk left from old splitter layout prefs."""
    cleaned: dict[str, int] = {}
    for key, raw in saved.items():
        if key not in CONNECT_PANEL_KEYS:
            continue
        try:
            h = int(raw)
        except (TypeError, ValueError):
            continue
        if h <= _COLLAPSED_STRIP_HEIGHT + 4:
            continue
        min_valid = _MIN_VALID_SAVED_HEIGHT.get(
            key, max(_DEFAULT_PANEL_HEIGHTS.get(key, 80) // 2, 56)
        )
        if h < min_valid:
            continue
        cap = _PANEL_EXPANDED_CAP.get(key, h)
        cleaned[key] = min(h, cap)
    return cleaned


def _splitter_content_height(splitter: QtWidgets.QSplitter, sizes: list[int]) -> int:
    try:
        hw = int(splitter.handleWidth())
    except (TypeError, ValueError, AttributeError):
        hw = 8
    handles = max(0, len(sizes) - 1) * hw
    return sum(int(s) for s in sizes) + handles


def _stack_content_height(heights: list[int]) -> int:
    if not heights:
        return 0
    gaps = max(0, len(heights) - 1) * _CONNECT_STACK_SPACING
    return sum(int(h) for h in heights) + gaps


def _panel_row_heights(
    order: list[str],
    disclosures: dict[str, DisclosureRow],
    saved: dict[str, int],
) -> list[int]:
    heights: list[int] = []
    for key in order:
        row = disclosures.get(key)
        if not _panel_expanded(row):
            heights.append(_COLLAPSED_STRIP_HEIGHT)
        else:
            heights.append(_target_row_height(row, key, saved))
    return heights


def _remove_connect_stack_stretch(win: QtWidgets.QWidget) -> None:
    lay: QtWidgets.QVBoxLayout | None = getattr(win, "_connect_panel_stack_lay", None)
    item = getattr(win, "_connect_panel_stretch_item", None)
    if lay is None or item is None:
        return
    lay.removeItem(item)
    win._connect_panel_stretch_item = None


def _any_panel_expanded(disclosures: dict[str, DisclosureRow], order: list[str]) -> bool:
    return any(_panel_expanded(disclosures.get(key)) for key in order)


def _release_height_lock(widget: QtWidgets.QWidget) -> None:
    widget.setMinimumHeight(0)
    widget.setMaximumHeight(_WIDGET_SIZE_MAX)
    widget.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Preferred,
    )


def _release_geometry_lock(widget: QtWidgets.QWidget) -> None:
    """Clear fixed width/height pins from compact scroll layout."""
    widget.setMinimumWidth(0)
    widget.setMaximumWidth(_WIDGET_SIZE_MAX)
    _release_height_lock(widget)


def _connect_viewport_width(scroll: QtWidgets.QScrollArea | None) -> int:
    if scroll is None:
        return 0
    vp = scroll.viewport()
    try:
        w = int(vp.width()) if vp is not None else 0
    except (TypeError, ValueError, AttributeError):
        w = 0
    if w > 0:
        return w
    try:
        return int(scroll.width())
    except (TypeError, ValueError, AttributeError):
        return 0


def _ensure_connect_scroll_full_width(win: QtWidgets.QWidget) -> None:
    """Clear stale narrow width locks so Connect panels use the full tab."""
    scroll: QtWidgets.QScrollArea | None = getattr(win, "_connect_panel_scroll", None)
    page: QtWidgets.QWidget | None = getattr(win, "_connect_panel_page", None)
    if scroll is None or page is None:
        return
    host: QtWidgets.QWidget | None = getattr(win, "_connect_panel_host", None)
    stack: QtWidgets.QWidget | None = getattr(win, "_connect_panel_stack", None)
    _release_geometry_lock(page)
    if host is not None:
        _release_geometry_lock(host)
    if stack is not None:
        _release_geometry_lock(stack)
    scroll.setWidgetResizable(True)


def _pin_compact_scroll_page(
    scroll: QtWidgets.QScrollArea | None,
    page: QtWidgets.QWidget,
    *,
    page_h: int,
) -> None:
    """Compact collapsed stack: pin height only (width follows viewport via widgetResizable)."""
    _ = scroll
    _release_geometry_lock(page)
    page.setMinimumHeight(page_h)
    page.setMaximumHeight(page_h)
    page.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )


def _panel_expanded_size(key: str, saved: dict[str, int]) -> int:
    default = _DEFAULT_PANEL_HEIGHTS.get(key, 80)
    if key not in saved:
        return min(default, _PANEL_EXPANDED_CAP.get(key, default))
    raw = int(saved[key])
    cap = _PANEL_EXPANDED_CAP.get(key, raw)
    floor = _MIN_VALID_SAVED_HEIGHT.get(key, max(default // 2, _COLLAPSED_STRIP_HEIGHT))
    return max(min(raw, cap), floor)


def _connect_splitter_target_height(
    win: QtWidgets.QWidget,
    order: list[str],
    disclosures: dict[str, DisclosureRow],
    sizes: list[int],
) -> int:
    natural = _stack_content_height(sizes)
    host: QtWidgets.QWidget | None = getattr(win, "_connect_panel_host", None)
    if host is None:
        return max(natural, 220)
    tab = host.parentWidget()
    try:
        tab_h = int(tab.height()) if tab is not None else 0
    except (TypeError, ValueError, AttributeError):
        tab_h = 0
    if tab_h > 120:
        tab_budget = max(tab_h - _connect_tab_chrome_height(win), 160)
        return min(max(natural, 220), tab_budget)
    return max(natural, 220)


def mount_connection_hub_on_diagnostics(
    win: QtWidgets.QWidget,
    lay: QtWidgets.QVBoxLayout,
) -> None:
    """Connection hub card grid on Tools → Diagnostics (not Connect)."""
    from ui.connection_hub import ConnectionHubWidget

    hub = ConnectionHubWidget(standalone=True)
    hub.attach_bridge_window(win)
    win.connection_hub = hub
    lay.addWidget(hub, 0)


def embed_connection_hub_on_connect_body(
    win: QtWidgets.QWidget,
    connect_body: QtWidgets.QWidget,
    legacy_widgets: list[QtWidgets.QWidget],
) -> None:
    """Deprecated — hub moved to Diagnostics; legacy widgets stay on Connect body."""
    layout = connect_body.layout()
    if layout is None:
        return
    for widget in legacy_widgets:
        layout.addWidget(widget, 0)


def configure_connect_tab_scroll(win: QtWidgets.QWidget) -> None:
    """Legacy hook — panel scroll is configured in setup_connect_tab_panels."""
    _ = win


def schedule_fit_window_to_connect(win: QtWidgets.QWidget) -> None:
    """No-op: main window height is user-controlled; use tab scroll instead."""
    _ = win


def _set_connect_tab_stretch(win: QtWidgets.QWidget, *, compact: bool) -> None:
    """Keep scroll area at stretch=1 regardless of panel state.

    The old compact→stretch=0 path was the root cause of the scroll area
    disappearing and panels clipping.  Native Qt scrolling requires the area to
    always fill the tab; the scrollbar handles any content overflow.
    """
    lay: QtWidgets.QVBoxLayout | None = getattr(win, "_connect_tab_layout", None)
    scroll: QtWidgets.QScrollArea | None = getattr(win, "_connect_panel_scroll", None)
    if lay is None or scroll is None:
        return
    try:
        scroll_idx = int(lay.indexOf(scroll))
    except (TypeError, ValueError, AttributeError):
        scroll_idx = -1
    if scroll_idx >= 0:
        lay.setStretch(scroll_idx, 1)
    host_lay: QtWidgets.QVBoxLayout | None = getattr(win, "_connect_panel_host_lay", None)
    stack: QtWidgets.QWidget | None = getattr(win, "_connect_panel_stack", None)
    if host_lay is not None and stack is not None:
        try:
            sp_idx = int(host_lay.indexOf(stack))
        except (TypeError, ValueError, AttributeError):
            sp_idx = -1
        if sp_idx >= 0:
            host_lay.setStretch(sp_idx, 0)


def _schedule_connect_scroll_geometry(
    win: QtWidgets.QWidget,
    *,
    content_h: int,
    expanded_any: bool,
) -> None:
    """Debounce scroll/tab height updates (avoids layout feedback loops)."""
    win._connect_sync_geom_pending = (int(content_h), bool(expanded_any))
    timer: QtCore.QTimer | None = getattr(win, "_connect_sync_geom_timer", None)
    if timer is not None:
        timer.start(16)


def _flush_connect_scroll_geometry(win: QtWidgets.QWidget) -> None:
    pending = getattr(win, "_connect_sync_geom_pending", None)
    if pending is None:
        return
    content_h, expanded_any = pending
    _sync_connect_panel_scroll_geometry(
        win, content_h=content_h, expanded_any=expanded_any
    )


def _sync_connect_panel_scroll_geometry(
    win: QtWidgets.QWidget,
    *,
    content_h: int,
    expanded_any: bool,
    stacked_expand: bool = False,
) -> None:
    """Size the scroll host: compact when collapsed, else full-width flexible scroll."""
    _ = stacked_expand
    scroll: QtWidgets.QScrollArea | None = getattr(win, "_connect_panel_scroll", None)
    if scroll is not None:
        scroll.setWidgetResizable(bool(expanded_any))
        scroll.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        scroll.setMinimumHeight(0)
        scroll.setMaximumHeight(_WIDGET_SIZE_MAX)
        scroll.updateGeometry()

    page: QtWidgets.QWidget | None = getattr(win, "_connect_panel_page", None)
    host: QtWidgets.QWidget | None = getattr(win, "_connect_panel_host", None)
    if page is not None:
        lay = page.layout()
        host_idx = -1
        if isinstance(lay, QtWidgets.QVBoxLayout) and host is not None:
            lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            try:
                host_idx = int(lay.indexOf(host))
            except (TypeError, ValueError, AttributeError):
                host_idx = -1
        if not expanded_any:
            page_h = max(int(content_h) + 8, _COLLAPSED_STRIP_HEIGHT + 8)
            _pin_compact_scroll_page(scroll, page, page_h=page_h)
            if host_idx >= 0:
                lay.setStretch(host_idx, 0)
        else:
            _release_geometry_lock(page)
            if host is not None:
                _release_geometry_lock(host)
            page.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Minimum,
            )
            if isinstance(lay, QtWidgets.QVBoxLayout) and host_idx >= 0:
                lay.setStretch(host_idx, 0)

    tab: QtWidgets.QWidget | None = getattr(win, "_connect_tab_widget", None)
    if tab is not None:
        _release_height_lock(tab)
        tab.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        tab.updateGeometry()


def _reflow_connect_panel_host(
    win: QtWidgets.QWidget,
    sizes: list[int] | None = None,
    *,
    user_resize: bool = False,
    sole_expanded: bool = False,
) -> None:
    """Legacy entry — panel stack layout is applied in _apply_connect_panel_layout."""
    _ = sizes, user_resize, sole_expanded
    _apply_connect_panel_layout(win)


def _connect_tab_chrome_height(win: QtWidgets.QWidget) -> int:
    """Tool row + margins above the panel scroll area."""
    lay: QtWidgets.QVBoxLayout | None = getattr(win, "_connect_tab_layout", None)
    host: QtWidgets.QWidget | None = getattr(win, "_connect_panel_host", None)
    scroll: QtWidgets.QScrollArea | None = getattr(win, "_connect_panel_scroll", None)
    if lay is None or host is None:
        return 48
    skip = {host, scroll}
    try:
        margins = lay.contentsMargins()
        total = int(margins.top()) + int(margins.bottom())
        spacing = int(lay.spacing())
        count = int(lay.count())
    except (TypeError, ValueError, AttributeError):
        return 48
    for i in range(count):
        item = lay.itemAt(i)
        if item is None:
            continue
        w = item.widget()
        if w is None or w in skip:
            continue
        try:
            total += int(w.sizeHint().height()) + spacing
        except (TypeError, ValueError, AttributeError):
            continue
    return total + 8


def _maybe_restore_connect_window_height(win: QtWidgets.QWidget) -> None:
    """Undo a prior shrink so expanded panels are not trapped in a short window."""
    try:
        min_h = int(win.minimumHeight())
    except (TypeError, ValueError, AttributeError):
        min_h = 380
    comfort = max(_STANDARD_CONNECT_WINDOW_HEIGHT, min_h)
    try:
        current = int(win.height())
    except (TypeError, ValueError, AttributeError):
        return
    if current >= comfort - 32:
        return
    win.resize(win.width(), comfort)


def _fit_window_to_connect_content(win: QtWidgets.QWidget) -> None:
    """Deprecated: window auto-shrink removed (breaks resize after panel toggles)."""
    _ = win


def _schedule_connect_splitter_sizes(win: QtWidgets.QWidget, *, use_defaults: bool = False) -> None:
    """Apply splitter sizes after layout knows the Connect host height."""
    win._connect_splitter_use_defaults = bool(use_defaults)
    win._connect_splitter_apply_pass = 0
    timer: QtCore.QTimer | None = getattr(win, "_connect_splitter_apply_timer", None)
    if timer is None:
        t = QtCore.QTimer(win)
        t.setSingleShot(True)

        def _apply() -> None:
            use_def = bool(getattr(win, "_connect_splitter_use_defaults", False))
            stack: QtWidgets.QWidget | None = getattr(win, "_connect_panel_stack", None)
            _apply_connect_panel_layout(win, use_defaults=use_def)
            if stack is not None and int(stack.height()) < 80:
                pass_n = int(getattr(win, "_connect_splitter_apply_pass", 0))
                if pass_n < 4:
                    win._connect_splitter_apply_pass = pass_n + 1
                    t.start(48)
                    return
            win._connect_splitter_apply_pass = 0

        t.timeout.connect(_apply)
        win._connect_splitter_apply_timer = t
        timer = t
    timer.start(32)


def _clamp_splitter_sizes_to_viewport(
    splitter: QtWidgets.QSplitter,
    order: list[str],
    sizes: list[int],
    disclosures: dict[str, DisclosureRow],
) -> list[int]:
    """Keep collapsed strips fixed; give slack only to expanded rows."""
    if not sizes or len(sizes) != len(order):
        return sizes

    out = [_COLLAPSED_STRIP_HEIGHT] * len(order)
    expanded_idx: list[int] = []
    for i, key in enumerate(order):
        row = disclosures.get(key)
        if _panel_expanded(row):
            expanded_idx.append(i)
            out[i] = max(sizes[i], _COLLAPSED_STRIP_HEIGHT)

    if not expanded_idx:
        return out

    try:
        available = int(splitter.height())
    except (TypeError, ValueError, AttributeError):
        available = 0
    if available < 80:
        return out

    try:
        hw = int(splitter.handleWidth())
    except (TypeError, ValueError, AttributeError):
        hw = 8
    budget = available - max(0, len(sizes) - 1) * hw
    collapsed_fixed = (len(order) - len(expanded_idx)) * _COLLAPSED_STRIP_HEIGHT
    slack = budget - collapsed_fixed
    if slack <= 0:
        return out

    if len(expanded_idx) == 1:
        out[expanded_idx[0]] = max(_COLLAPSED_STRIP_HEIGHT, slack)
        return out

    weights = [max(out[i], _COLLAPSED_STRIP_HEIGHT) for i in expanded_idx]
    total_w = sum(weights)
    if total_w <= 0:
        share = max(_COLLAPSED_STRIP_HEIGHT, slack // len(expanded_idx))
        for i in expanded_idx:
            out[i] = share
        return out

    for idx in expanded_idx:
        out[idx] = max(_COLLAPSED_STRIP_HEIGHT, int(out[idx] * slack / total_w))
    drift = budget - sum(out)
    if drift != 0:
        out[expanded_idx[-1]] = max(_COLLAPSED_STRIP_HEIGHT, out[expanded_idx[-1]] + drift)
    return out


def _release_splitter_height_lock(splitter: QtWidgets.QSplitter) -> None:
    splitter.setMinimumHeight(0)
    splitter.setMaximumHeight(_WIDGET_SIZE_MAX)


def _apply_splitter_height_mode(
    splitter: QtWidgets.QSplitter,
    sizes: list[int],
    *,
    expanded_count: int,
) -> None:
    """Pin splitter height before setSizes when collapsed (avoids Qt stretching strips apart)."""
    content_h = _splitter_content_height(splitter, sizes)
    if expanded_count == 0:
        splitter.setHandleWidth(_CONNECT_SPLITTER_HANDLE_COMPACT)
        splitter.setFixedHeight(content_h)
        return
    splitter.setHandleWidth(_CONNECT_SPLITTER_HANDLE)
    splitter.setMinimumHeight(0)
    splitter.setMaximumHeight(_WIDGET_SIZE_MAX)
    splitter.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Expanding,
    )


def _panel_expanded(row: DisclosureRow | None) -> bool:
    return row is not None and row.tool_button().isChecked()


def _expanded_panel_count(disclosures: dict[str, DisclosureRow], order: list[str]) -> int:
    return sum(1 for key in order if _panel_expanded(disclosures.get(key)))


def _tune_connection_panel_body(row: DisclosureRow) -> None:
    """Connect Serial & network section — forms only (hub is on Diagnostics)."""
    body = row.body_widget()
    _release_geometry_lock(body)
    body.setMinimumWidth(0)
    body.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Minimum,
    )


def _reflow_connection_hub_columns(win: QtWidgets.QWidget) -> None:
    hub: QtWidgets.QWidget | None = getattr(win, "connection_hub", None)
    if hub is None or not hasattr(hub, "reflow_card_columns"):
        return
    hub.reflow_card_columns()  # type: ignore[union-attr]


def _target_row_height(row: DisclosureRow, key: str, saved: dict[str, int]) -> int:
    """Expanded row height that never clips visible controls."""
    row.adjustSize()
    natural = max(row.sizeHint().height(), row.minimumSizeHint().height())
    floor = max(_DEFAULT_PANEL_HEIGHTS.get(key, 56), 48)
    # Keep saved drag-heights bounded, but never shrink below current content size.
    from_prefs = _panel_expanded_size(key, saved)
    return max(natural, from_prefs, floor)


def _apply_row_expand_style(
    row: DisclosureRow,
    expanded: bool,
    *,
    sole_expanded: bool = False,
    stacked: bool = False,
) -> None:
    _ = sole_expanded, stacked
    body = row.body_widget()
    if expanded:
        row.setMaximumHeight(_WIDGET_SIZE_MAX)
        row.setMinimumHeight(_COLLAPSED_STRIP_HEIGHT)
        row.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        body.setMaximumHeight(_WIDGET_SIZE_MAX)
        body.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
    else:
        row.setMinimumHeight(_COLLAPSED_STRIP_HEIGHT)
        row.setMaximumHeight(_COLLAPSED_STRIP_HEIGHT)
        row.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        body.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )


def _capture_expanded_size_from_splitter(win: QtWidgets.QWidget, key: str) -> None:
    """Remember row height for a panel before it is collapsed."""
    disclosures: dict[str, DisclosureRow] = getattr(win, "_connect_panel_disclosures", {})
    row = disclosures.get(key)
    if row is None or not _panel_expanded(row):
        return
    try:
        h = int(row.height())
    except (TypeError, ValueError, AttributeError):
        return
    if h <= _COLLAPSED_STRIP_HEIGHT + 4:
        return
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    expanded_sizes = dict(prefs.get("sizes", {}))
    expanded_sizes[key] = h
    save_connect_panel_prefs(
        ui_mode,
        list(prefs.get("order", [])),
        dict(prefs.get("collapsed", {})),
        sizes=expanded_sizes,
    )


def _on_connect_panel_toggled(win: QtWidgets.QWidget, key: str, expanded: bool) -> None:
    if getattr(win, "_connect_panel_syncing", False):
        return
    if not expanded:
        _capture_expanded_size_from_splitter(win, key)
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    collapsed: dict[str, bool] = dict(prefs.get("collapsed", {}))
    collapsed[key] = not expanded
    save_connect_panel_prefs(
        ui_mode,
        list(prefs.get("order", [])),
        collapsed,
        sizes=dict(prefs.get("sizes", {})),
    )
    row = getattr(win, "_connect_panel_disclosures", {}).get(key)
    if row is not None:
        row.set_expanded(expanded)
    QtCore.QTimer.singleShot(0, lambda w=win: _apply_connect_panel_layout(w))


def _set_all_connect_panels(win: QtWidgets.QWidget, expanded: bool) -> None:
    disclosures: dict[str, DisclosureRow] = getattr(win, "_connect_panel_disclosures", {})
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    if not expanded:
        for key, row in disclosures.items():
            if _panel_expanded(row):
                _capture_expanded_size_from_splitter(win, key)
    collapsed = {k: not expanded for k in disclosures}
    order = getattr(win, "_connect_panel_order", [])
    win._connect_panel_syncing = True
    try:
        for row in disclosures.values():
            row.set_expanded(expanded)
    finally:
        win._connect_panel_syncing = False
    save_connect_panel_prefs(
        ui_mode,
        list(prefs.get("order", [])),
        collapsed,
        sizes=dict(prefs.get("sizes", {})),
    )
    _apply_connect_splitter_sizes(win)


def _reset_connect_splitter_sizes(win: QtWidgets.QWidget) -> None:
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    save_connect_panel_prefs(
        ui_mode,
        list(prefs.get("order", [])),
        dict(prefs.get("collapsed", {})),
        sizes={},
    )
    _apply_connect_splitter_sizes(win, use_defaults=True)
    if hasattr(win, "_log_ui"):
        win._log_ui("[UI] Reset Connect panel sizes to defaults.")  # type: ignore[attr-defined]


def _apply_connect_splitter_sizes(win: QtWidgets.QWidget, *, use_defaults: bool = False) -> None:
    _apply_connect_panel_layout(win, use_defaults=use_defaults)


def _apply_connect_panel_layout(win: QtWidgets.QWidget, *, use_defaults: bool = False) -> None:
    stack: QtWidgets.QWidget | None = getattr(win, "_connect_panel_stack", None)
    stack_lay: QtWidgets.QVBoxLayout | None = getattr(win, "_connect_panel_stack_lay", None)
    host: QtWidgets.QWidget | None = getattr(win, "_connect_panel_host", None)
    order: list[str] = getattr(win, "_connect_panel_order", [])
    disclosures: dict[str, DisclosureRow] = getattr(win, "_connect_panel_disclosures", {})
    if stack is None or stack_lay is None or host is None or not order:
        return

    _ = use_defaults
    expanded_count = _expanded_panel_count(disclosures, order)
    collapsed_heights = [_COLLAPSED_STRIP_HEIGHT] * len(order)
    content_h = _stack_content_height(collapsed_heights)

    _remove_connect_stack_stretch(win)

    for key in order:
        row = disclosures.get(key)
        if row is None:
            continue
        exp = _panel_expanded(row)
        _apply_row_expand_style(row, exp)
        if not exp:
            row.setFixedHeight(_COLLAPSED_STRIP_HEIGHT)
        else:
            _release_geometry_lock(row)
            if key == "connection":
                _tune_connection_panel_body(row)

    host_lay: QtWidgets.QVBoxLayout | None = getattr(win, "_connect_panel_host_lay", None)
    if host_lay is not None:
        try:
            sp_idx = int(host_lay.indexOf(stack))
        except (TypeError, ValueError, AttributeError):
            sp_idx = -1
        if sp_idx >= 0:
            host_lay.setStretch(sp_idx, 0)

    if expanded_count == 0:
        stack.setFixedHeight(content_h)
        host.setFixedHeight(content_h)
        host.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
    else:
        _release_geometry_lock(stack)
        _release_geometry_lock(host)
        stack.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        host.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )

    _set_connect_tab_stretch(win, compact=False)
    _sync_connect_panel_scroll_geometry(
        win,
        content_h=content_h,
        expanded_any=expanded_count > 0,
    )
    stack.updateGeometry()
    host.updateGeometry()
    if expanded_count > 0:
        _ensure_connect_scroll_full_width(win)


def _persist_connect_splitter_sizes(win: QtWidgets.QWidget) -> None:
    """Persist heights for expanded panels only (collapsed strips stay minimal on reopen)."""
    order: list[str] = getattr(win, "_connect_panel_order", [])
    disclosures: dict[str, DisclosureRow] = getattr(win, "_connect_panel_disclosures", {})
    if not order:
        return
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    expanded_sizes = dict(prefs.get("sizes", {}))
    for key in order:
        row = disclosures.get(key)
        if not _panel_expanded(row):
            continue
        try:
            h = int(row.height())
        except (TypeError, ValueError, AttributeError):
            continue
        if h > _COLLAPSED_STRIP_HEIGHT + 4:
            expanded_sizes[key] = h
    save_connect_panel_prefs(
        ui_mode,
        list(prefs.get("order", [])),
        dict(prefs.get("collapsed", {})),
        sizes=expanded_sizes,
    )


def _open_connect_ui_editor(win: QtWidgets.QWidget) -> None:
    from ui.ui_editor import open_connect_panel_editor

    open_connect_panel_editor(win)


def _open_connect_panel_manager(win: QtWidgets.QWidget) -> None:
    """Legacy entry — UI editor Connect tab."""
    _open_connect_ui_editor(win)

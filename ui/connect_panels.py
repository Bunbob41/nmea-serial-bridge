"""Collapsible, reorderable, vertically resizable panels on the Standard Connect tab."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ui.collapsible import DisclosureRow
from ui.ui_prefs import load_connect_panel_prefs, save_connect_panel_prefs

CONNECT_PANEL_KEYS: tuple[str, ...] = (
    "run",
    "hint",
    "quick_log",
    "quick_terminal",
    "connection",
    "ntrip",
)

CONNECT_PANEL_LABELS: dict[str, str] = {
    "run": "Run bridge",
    "hint": "Status hint",
    "quick_log": "Quick log",
    "quick_terminal": "Quick terminal",
    "connection": "Serial & network",
    "ntrip": "NTRIP corrections",
}
CONNECT_PANEL_COLLAPSED_HINTS: dict[str, str] = {
    "run": "Start/Stop",
    "hint": "Current workflow guidance",
    "quick_log": "Recent bridge messages",
    "quick_terminal": "Bench script output",
    "connection": "COM, baud, UDP/TCP",
    "ntrip": "Caster host, mount, credentials",
}

CONNECT_TOOLBAR_KEYS: tuple[str, ...] = (
    "ui_editor",
    "expand_all",
    "collapse_all",
    "reset_sizes",
)
CONNECT_TOOLBAR_LABELS: dict[str, str] = {
    "ui_editor": "UI editor…",
    "expand_all": "Expand all",
    "collapse_all": "Collapse all",
    "reset_sizes": "Reset sizes",
}

# Must stay in the splitter (UI editor shows them as non-toggleable).
REQUIRED_CONNECT_PANELS = frozenset({"run", "connection"})

# Recommended hidden-until-needed sections (UI editor Restore defaults).
DEFAULT_CONNECT_HIDDEN = frozenset({"ntrip"})

_DEFAULT_PANEL_HEIGHTS: dict[str, int] = {
    "run": 84,
    "hint": 48,
    "quick_log": 120,
    "quick_terminal": 120,
    "connection": 360,
    "ntrip": 110,
}

# Cap scaled height for compact sections (avoids giant Start row when alone expanded).
_PANEL_EXPANDED_CAP: dict[str, int] = {
    "run": 120,   # Start + Stop buttons (36px each) + fan-out checkbox + margins
    "hint": 64,
    "quick_log": 220,
    "quick_terminal": 220,
    "connection": 520,
    "ntrip": 200,
}

# Collapsed disclosure strip must fit rounded header padding/text.
_COLLAPSED_STRIP_HEIGHT = 44
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


def sync_connect_panel_layout(win: QtWidgets.QWidget) -> None:
    """Force a fresh Connect reflow (use when tab becomes active)."""
    splitter: QtWidgets.QSplitter | None = getattr(win, "_connect_panel_splitter", None)
    if splitter is None:
        return
    _apply_connect_splitter_sizes(win)
    QtCore.QTimer.singleShot(0, lambda w=win: _flush_connect_scroll_geometry(w))
    # One extra pass after Qt finishes tab/page geometry updates.
    QtCore.QTimer.singleShot(24, lambda w=win: _apply_connect_splitter_sizes(w))


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
    btn_reset = QtWidgets.QPushButton(CONNECT_TOOLBAR_LABELS["reset_sizes"])
    btn_reset.setToolTip("Restore default vertical sizes for Connect panels.")
    btn_reset.clicked.connect(lambda: _reset_connect_splitter_sizes(win))
    toolbar_buttons: dict[str, QtWidgets.QPushButton] = {
        "ui_editor": btn_ui_editor,
        "expand_all": btn_expand,
        "collapse_all": btn_collapse,
        "reset_sizes": btn_reset,
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

    splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
    splitter.setObjectName("connectPanelSplitter")
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(8)
    splitter.setOpaqueResize(True)
    host_lay.addWidget(splitter, 1)

    panel_page = QtWidgets.QWidget()
    panel_page.setObjectName("toolTabScrollHost")
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
    page_lay.addStretch(1)

    panel_scroll = QtWidgets.QScrollArea()
    panel_scroll.setObjectName("toolTabScroll")
    panel_scroll.setWidgetResizable(True)
    panel_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    panel_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    panel_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    panel_scroll.setFocusPolicy(QtCore.Qt.FocusPolicy.WheelFocus)
    panel_scroll.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    panel_scroll.viewport().setObjectName("toolTabScrollViewport")
    panel_scroll.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    # Permanently Expanding — never switched to Fixed; native scrollbar handles overflow.
    panel_scroll.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Expanding,
    )
    panel_scroll.setWidget(panel_page)
    lay.addWidget(panel_scroll, 1)

    win._connect_panel_host = host
    win._connect_panel_host_lay = host_lay
    win._connect_panel_page = panel_page
    win._connect_panel_scroll = panel_scroll
    win._connect_page_in_main_scroll = True
    win._connect_panel_widgets = dict(panels)
    win._connect_panel_splitter = splitter
    win._connect_panel_disclosures: dict[str, DisclosureRow] = {}
    win._connect_panel_order: list[str] = []
    win._connect_panel_syncing = False
    if not hasattr(win, "_connect_splitter_save_timer"):
        t = QtCore.QTimer(win)
        t.setSingleShot(True)
        t.timeout.connect(lambda: _persist_connect_splitter_sizes(win))
        win._connect_splitter_save_timer = t
    if not hasattr(win, "_connect_sync_geom_timer"):
        gt = QtCore.QTimer(win)
        gt.setSingleShot(True)
        gt.timeout.connect(lambda w=win: _flush_connect_scroll_geometry(w))
        win._connect_sync_geom_timer = gt
    win._connect_sync_geom_pending = None
    def _on_splitter_moved(*_a: object, w: QtWidgets.QWidget = win) -> None:
        w._connect_splitter_save_timer.start(250)  # type: ignore[attr-defined]
        _reflow_connect_panel_host(w, list(splitter.sizes()), user_resize=True)

    splitter.splitterMoved.connect(_on_splitter_moved)
    _rebuild_connect_panels(win)


def _rebuild_connect_panels(win: QtWidgets.QWidget) -> None:
    splitter: QtWidgets.QSplitter | None = getattr(win, "_connect_panel_splitter", None)
    widgets: dict[str, QtWidgets.QWidget] = getattr(win, "_connect_panel_widgets", {})
    if splitter is None or not widgets:
        return
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    order = [k for k in prefs.get("order", []) if k in widgets]
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

    while splitter.count():
        w = splitter.widget(0)
        if w is not None:
            w.setParent(None)

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
            fill_vertical=True,
            on_layout_changed=lambda w=win: _apply_connect_splitter_sizes(w),
        )
        row.setObjectName("connectPanelRow")
        row.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        row.setProperty("connectPanelKey", key)
        row.tool_button().toggled.connect(
            lambda on, k=key, w=win: _on_connect_panel_toggled(w, k, on)
        )
        _apply_row_expand_style(row, start_open, sole_expanded=False)
        disclosures[key] = row
        splitter.addWidget(row)
        # Hard floor: prevent corrupted saved sizes from squishing the header to 0px.
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


def _default_collapsed(key: str) -> bool:
    """Compact Connect by default — only Run + Serial/network start expanded."""
    return key in {"hint", "quick_log", "quick_terminal", "ntrip"}


def sanitize_connect_panel_hidden(hidden: list[str] | set[str]) -> list[str]:
    """Required panels cannot be hidden (non-checkable list rows read as unchecked)."""
    return [k for k in hidden if k not in REQUIRED_CONNECT_PANELS]


def default_connect_collapsed(order: list[str]) -> dict[str, bool]:
    return {k: _default_collapsed(k) for k in order}


def restore_connect_panel_layout(win: QtWidgets.QWidget) -> None:
    """Survey-default Connect sections: show all except NTRIP, reset collapse and sizes."""
    widgets: dict = getattr(win, "_connect_panel_widgets", {})
    if not widgets:
        return
    ui_mode = getattr(win, "_ui_mode", "standard")
    order = [k for k in CONNECT_PANEL_KEYS if k in widgets]
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
    return collapsed, sizes, use_defaults


def _splitter_content_height(splitter: QtWidgets.QSplitter, sizes: list[int]) -> int:
    try:
        hw = int(splitter.handleWidth())
    except (TypeError, ValueError, AttributeError):
        hw = 8
    handles = max(0, len(sizes) - 1) * hw
    return sum(int(s) for s in sizes) + handles


def _any_panel_expanded(disclosures: dict[str, DisclosureRow], order: list[str]) -> bool:
    return any(_panel_expanded(disclosures.get(key)) for key in order)


def _release_height_lock(widget: QtWidgets.QWidget) -> None:
    widget.setMinimumHeight(0)
    widget.setMaximumHeight(_WIDGET_SIZE_MAX)
    widget.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Preferred,
    )


def _panel_expanded_size(key: str, saved: dict[str, int]) -> int:
    raw = int(saved.get(key, _DEFAULT_PANEL_HEIGHTS.get(key, 80)))
    cap = _PANEL_EXPANDED_CAP.get(key, raw)
    return max(min(raw, cap), 48)


def _connect_splitter_target_height(
    win: QtWidgets.QWidget,
    order: list[str],
    disclosures: dict[str, DisclosureRow],
    sizes: list[int],
) -> int:
    splitter: QtWidgets.QSplitter | None = getattr(win, "_connect_panel_splitter", None)
    if splitter is None:
        return 220
    natural = _splitter_content_height(splitter, sizes)
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


def embed_connection_hub_on_connect_body(
    win: QtWidgets.QWidget,
    connect_body: QtWidgets.QWidget,
    legacy_widgets: list[QtWidgets.QWidget],
) -> None:
    """Insert Connection Hub above legacy serial/network controls (manual override)."""
    from ui.connection_hub import ConnectionHubWidget

    layout = connect_body.layout()
    if layout is None:
        return
    hub = ConnectionHubWidget(connect_body)
    win.connection_hub = hub
    legacy_host = QtWidgets.QWidget()
    legacy_host.setObjectName("manualOverrideLegacyHost")
    legacy_lay = QtWidgets.QVBoxLayout(legacy_host)
    legacy_lay.setContentsMargins(0, 0, 0, 0)
    legacy_lay.setSpacing(6)
    for widget in legacy_widgets:
        layout.removeWidget(widget)
        legacy_lay.addWidget(widget)
    hub.set_manual_override_panel(legacy_host)
    layout.insertWidget(2, hub, 1)


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
    scroll_idx = lay.indexOf(scroll)
    if scroll_idx >= 0:
        lay.setStretch(scroll_idx, 1)
    host_lay: QtWidgets.QVBoxLayout | None = getattr(win, "_connect_panel_host_lay", None)
    splitter: QtWidgets.QSplitter | None = getattr(win, "_connect_panel_splitter", None)
    if host_lay is not None and splitter is not None:
        try:
            sp_idx = int(host_lay.indexOf(splitter))
        except (TypeError, ValueError, AttributeError):
            sp_idx = -1
        if sp_idx >= 0:
            host_lay.setStretch(sp_idx, 1)


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
) -> None:
    """Release all manual Fixed-height locks; native Qt scrolling owns geometry.

    The old implementation switched the QScrollArea between Fixed (all-collapsed)
    and Expanding (any-expanded) and also pinned the tab widget height.  Those
    transitions caused clipping and broke the scrollbar.  Now this function only
    ensures previously-applied locks are cleared and the permanent Expanding
    policy is (re)applied — content overflow is handled by the scrollbar.
    """
    scroll: QtWidgets.QScrollArea | None = getattr(win, "_connect_panel_scroll", None)
    if scroll is not None:
        scroll.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        scroll.setMinimumHeight(0)
        scroll.setMaximumHeight(_WIDGET_SIZE_MAX)
        scroll.updateGeometry()

    page: QtWidgets.QWidget | None = getattr(win, "_connect_panel_page", None)
    if page is not None:
        _release_height_lock(page)
        lay = page.layout()
        if isinstance(lay, QtWidgets.QVBoxLayout):
            lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

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
    sizes: list[int],
    *,
    user_resize: bool = False,
    sole_expanded: bool = False,
) -> None:
    """Release manual height locks and let Qt's layout engine size everything.

    The old implementation pinned host/splitter/scroll to exact pixel heights
    based on expanded state, which caused clipping and broke native scrolling.
    Now the QScrollArea is always Expanding; the host and splitter use Minimum
    so they shrink to fit their content but never clip it.
    """
    splitter: QtWidgets.QSplitter | None = getattr(win, "_connect_panel_splitter", None)
    host: QtWidgets.QWidget | None = getattr(win, "_connect_panel_host", None)
    if splitter is None or host is None or not sizes:
        return

    # Release any previously-applied Fixed/pin locks so the layout can breathe.
    _release_height_lock(host)
    _release_height_lock(splitter)
    host.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Minimum,
    )
    splitter.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Minimum,
    )

    # Ensure scroll area and tab stretch factors stay at 1 (never 0).
    _set_connect_tab_stretch(win, compact=False)

    # Schedule the scroll-area geometry flush (releases tab/page locks too).
    content_h = _splitter_content_height(splitter, sizes)
    _schedule_connect_scroll_geometry(win, content_h=content_h, expanded_any=True)
    host.updateGeometry()


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
    timer: QtCore.QTimer | None = getattr(win, "_connect_splitter_apply_timer", None)
    if timer is None:
        t = QtCore.QTimer(win)
        t.setSingleShot(True)

        def _apply() -> None:
            use_def = bool(getattr(win, "_connect_splitter_use_defaults", False))
            _apply_connect_splitter_sizes(win, use_defaults=use_def)

        t.timeout.connect(_apply)
        win._connect_splitter_apply_timer = t
        timer = t
    timer.start(32)


def _panel_expanded(row: DisclosureRow | None) -> bool:
    return row is not None and row.tool_button().isChecked()


def _expanded_panel_count(disclosures: dict[str, DisclosureRow], order: list[str]) -> int:
    return sum(1 for key in order if _panel_expanded(disclosures.get(key)))


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
) -> None:
    body = row.body_widget()
    if expanded:
        row.setMaximumHeight(_WIDGET_SIZE_MAX)
        if sole_expanded:
            row.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Maximum,
            )
            body.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Maximum,
            )
        else:
            row.setMinimumHeight(_COLLAPSED_STRIP_HEIGHT)
            row.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Expanding,
            )
            body.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Expanding,
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
    """Remember splitter height for a panel before it is collapsed."""
    splitter: QtWidgets.QSplitter | None = getattr(win, "_connect_panel_splitter", None)
    order: list[str] = getattr(win, "_connect_panel_order", [])
    if splitter is None or key not in order:
        return
    idx = order.index(key)
    sizes_list = splitter.sizes()
    if idx >= len(sizes_list):
        return
    h = int(sizes_list[idx])
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
        disclosures = getattr(win, "_connect_panel_disclosures", {})
        order = getattr(win, "_connect_panel_order", [])
        sole = _expanded_panel_count(disclosures, order) == 1 and expanded
        row.set_expanded(expanded)
        _apply_row_expand_style(row, expanded, sole_expanded=sole)
    QtCore.QTimer.singleShot(0, lambda w=win: _apply_connect_splitter_sizes(w))


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
    expanded_count = len(disclosures) if expanded else 0
    win._connect_panel_syncing = True
    try:
        for key, row in disclosures.items():
            row.set_expanded(expanded)
            sole = expanded_count == 1 and expanded
            _apply_row_expand_style(row, expanded, sole_expanded=sole)
    finally:
        win._connect_panel_syncing = False
    save_connect_panel_prefs(
        ui_mode,
        list(prefs.get("order", [])),
        collapsed,
        sizes=dict(prefs.get("sizes", {})),
    )
    _apply_connect_splitter_sizes(win)
    # Flush scroll geometry so the QScrollArea compacts after all panels collapse.
    QtCore.QTimer.singleShot(0, lambda w=win: _flush_connect_scroll_geometry(w))


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
    splitter: QtWidgets.QSplitter | None = getattr(win, "_connect_panel_splitter", None)
    order: list[str] = getattr(win, "_connect_panel_order", [])
    disclosures: dict[str, DisclosureRow] = getattr(win, "_connect_panel_disclosures", {})
    if splitter is None or not order or splitter.count() != len(order):
        return
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    saved: dict[str, int] = {} if use_defaults else dict(prefs.get("sizes", {}))

    expanded_count = _expanded_panel_count(disclosures, order)
    sole_expanded = expanded_count == 1

    for key in order:
        row = disclosures.get(key)
        if row is None:
            continue
        exp = _panel_expanded(row)
        _apply_row_expand_style(
            row,
            exp,
            sole_expanded=sole_expanded and exp,
        )
        if exp and sole_expanded:
            row.setMinimumHeight(_target_row_height(row, key, saved))

    sizes: list[int] = []
    for key in order:
        row = disclosures.get(key)
        if not _panel_expanded(row):
            sizes.append(_COLLAPSED_STRIP_HEIGHT)
            continue
        sizes.append(_target_row_height(row, key, saved))

    # Hard clamp: splitter.setSizes() can distribute below widget minimumHeight when
    # total available space is tight.  Never let any slot fall below the strip floor,
    # whether collapsed or expanded.
    sizes = [max(s, _COLLAPSED_STRIP_HEIGHT) for s in sizes]

    splitter.blockSignals(True)
    try:
        for i, key in enumerate(order):
            # Only share extra slack when 2+ sections are open (drag handles). One open section
            # must not absorb the whole tab height after Collapse all.
            stretch = (
                1
                if _panel_expanded(disclosures.get(key)) and not sole_expanded
                else 0
            )
            splitter.setStretchFactor(i, stretch)
        splitter.setSizes(sizes)
    finally:
        splitter.blockSignals(False)

    _reflow_connect_panel_host(win, sizes, sole_expanded=sole_expanded)


def _persist_connect_splitter_sizes(win: QtWidgets.QWidget) -> None:
    """Persist heights for expanded panels only (collapsed strips stay minimal on reopen)."""
    splitter: QtWidgets.QSplitter | None = getattr(win, "_connect_panel_splitter", None)
    order: list[str] = getattr(win, "_connect_panel_order", [])
    disclosures: dict[str, DisclosureRow] = getattr(win, "_connect_panel_disclosures", {})
    if splitter is None or not order:
        return
    sizes_list = splitter.sizes()
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    expanded_sizes = dict(prefs.get("sizes", {}))
    for i, key in enumerate(order):
        if i >= len(sizes_list):
            break
        row = disclosures.get(key)
        if not _panel_expanded(row):
            continue
        h = int(sizes_list[i])
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

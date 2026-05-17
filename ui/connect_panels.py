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

_DEFAULT_PANEL_HEIGHTS: dict[str, int] = {
    "run": 56,
    "hint": 40,
    "quick_log": 120,
    "quick_terminal": 120,
    "connection": 260,
    "ntrip": 110,
}

_COLLAPSED_STRIP_HEIGHT = 26


def expand_connect_panel(win: QtWidgets.QWidget, key: str) -> None:
    """Expand one Connect section (e.g. quick terminal for bench setup output)."""
    disclosures: dict[str, DisclosureRow] = getattr(win, "_connect_panel_disclosures", {})
    row = disclosures.get(key)
    if row is None:
        return
    btn = row.tool_button()
    if not btn.isChecked():
        btn.setChecked(True)


def setup_connect_tab_panels(
    win: QtWidgets.QWidget,
    connect_tab: QtWidgets.QWidget,
    panels: dict[str, QtWidgets.QWidget],
) -> None:
    """Mount collapsible panels on Connect tab; call after all panel widgets exist on win."""
    lay = QtWidgets.QVBoxLayout(connect_tab)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)

    tool_row = QtWidgets.QHBoxLayout()
    btn_arrange = QtWidgets.QPushButton("Arrange panels…")
    btn_arrange.setToolTip("Drag to reorder Connect tab sections; check to show when collapsed.")
    btn_arrange.clicked.connect(lambda: _open_connect_panel_manager(win))
    btn_expand = QtWidgets.QPushButton("Expand all")
    btn_expand.clicked.connect(lambda: _set_all_connect_panels(win, True))
    btn_collapse = QtWidgets.QPushButton("Collapse all")
    btn_collapse.clicked.connect(lambda: _set_all_connect_panels(win, False))
    btn_reset = QtWidgets.QPushButton("Reset sizes")
    btn_reset.setToolTip("Restore default vertical sizes for Connect panels.")
    btn_reset.clicked.connect(lambda: _reset_connect_splitter_sizes(win))
    tool_row.addWidget(btn_arrange)
    tool_row.addWidget(btn_expand)
    tool_row.addWidget(btn_collapse)
    tool_row.addWidget(btn_reset)
    tool_row.addStretch(1)
    lay.addLayout(tool_row)

    host = QtWidgets.QWidget()
    host.setObjectName("connectPanelHost")
    host_lay = QtWidgets.QVBoxLayout(host)
    host_lay.setContentsMargins(6, 0, 6, 6)
    host_lay.setSpacing(0)

    splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
    splitter.setObjectName("connectPanelSplitter")
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(6)
    host_lay.addWidget(splitter, 1)
    lay.addWidget(host, 1)

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
    splitter.splitterMoved.connect(lambda *_a, w=win: w._connect_splitter_save_timer.start(250))  # type: ignore[attr-defined]
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
    collapsed, saved_sizes, use_default_sizes = _normalize_connect_launch_prefs(
        collapsed, saved_sizes, order
    )

    while splitter.count():
        w = splitter.widget(0)
        if w is not None:
            w.setParent(None)

    disclosures: dict[str, DisclosureRow] = {}
    for key in order:
        body = widgets.get(key)
        if body is None:
            continue
        start_open = not bool(collapsed.get(key, _default_collapsed(key)))
        row = DisclosureRow(
            CONNECT_PANEL_LABELS.get(key, key),
            body,
            start_open=start_open,
            button_object_name="connectPanelDisclosure",
            fill_vertical=True,
        )
        row.tool_button().toggled.connect(
            lambda on, k=key, w=win: _on_connect_panel_toggled(w, k, on)
        )
        _apply_row_expand_style(row, start_open)
        disclosures[key] = row
        splitter.addWidget(row)

    win._connect_panel_disclosures = disclosures
    win._connect_panel_order = list(order)
    save_connect_panel_prefs(ui_mode, order, collapsed, sizes=saved_sizes)
    _schedule_connect_splitter_sizes(win, use_defaults=use_default_sizes)


def _default_collapsed(_key: str) -> bool:
    return False


def _panel_collapsed_in_prefs(collapsed: dict[str, bool], key: str) -> bool:
    return bool(collapsed.get(key, _default_collapsed(key)))


def _normalize_connect_launch_prefs(
    collapsed: dict[str, bool],
    sizes: dict[str, int],
    order: list[str],
) -> tuple[dict[str, bool], dict[str, int], bool]:
    """Open Connect expanded with sensible splitter sizes unless the user left some panels open."""
    if not order:
        return collapsed, sizes, not bool(sizes)
    if all(_panel_collapsed_in_prefs(collapsed, k) for k in order):
        return {}, {}, True
    use_defaults = not sizes
    if sizes and all(
        sizes.get(k, _DEFAULT_PANEL_HEIGHTS.get(k, 80)) <= _COLLAPSED_STRIP_HEIGHT + 4 for k in order
    ):
        use_defaults = True
        sizes = {}
    return collapsed, sizes, use_defaults


def _schedule_connect_splitter_sizes(win: QtWidgets.QWidget, *, use_defaults: bool = False) -> None:
    """Apply splitter sizes after layout knows the Connect host height."""
    def _apply() -> None:
        _apply_connect_splitter_sizes(win, use_defaults=use_defaults)

    QtCore.QTimer.singleShot(0, _apply)
    QtCore.QTimer.singleShot(80, _apply)


def _panel_expanded(row: DisclosureRow | None) -> bool:
    return row is not None and row.tool_button().isChecked()


def _apply_row_expand_style(row: DisclosureRow, expanded: bool) -> None:
    if expanded:
        row.setMinimumHeight(_COLLAPSED_STRIP_HEIGHT)
        row.setMaximumHeight(16777215)
        row.setSizePolicy(
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
        _apply_row_expand_style(row, expanded)
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
    win._connect_panel_syncing = True
    try:
        for key, row in disclosures.items():
            btn = row.tool_button()
            btn.blockSignals(True)
            btn.setChecked(expanded)
            btn.blockSignals(False)
            _apply_row_expand_style(row, expanded)
    finally:
        win._connect_panel_syncing = False
    save_connect_panel_prefs(
        ui_mode,
        list(prefs.get("order", [])),
        collapsed,
        sizes=dict(prefs.get("sizes", {})),
    )
    QtCore.QTimer.singleShot(0, lambda w=win: _apply_connect_splitter_sizes(w))


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

    sizes: list[int] = []
    for key in order:
        row = disclosures.get(key)
        if not _panel_expanded(row):
            sizes.append(_COLLAPSED_STRIP_HEIGHT)
            continue
        sizes.append(max(int(saved.get(key, _DEFAULT_PANEL_HEIGHTS.get(key, 80))), 48))

    total_target = max(splitter.height(), 320)
    collapsed_count = sum(1 for key in order if not _panel_expanded(disclosures.get(key)))
    collapsed_sum = collapsed_count * _COLLAPSED_STRIP_HEIGHT
    expanded_sum = sum(sizes) - collapsed_sum
    avail = max(total_target - collapsed_sum, 80)
    if expanded_sum > 0 and avail > 0:
        scale = avail / expanded_sum
        scaled: list[int] = []
        for i, key in enumerate(order):
            row = disclosures.get(key)
            if not _panel_expanded(row):
                scaled.append(_COLLAPSED_STRIP_HEIGHT)
            else:
                scaled.append(max(int(sizes[i] * scale), 48))
        sizes = scaled

    splitter.blockSignals(True)
    try:
        splitter.setSizes(sizes)
    finally:
        splitter.blockSignals(False)


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


def _open_connect_panel_manager(win: QtWidgets.QWidget) -> None:
    widgets: dict[str, QtWidgets.QWidget] = getattr(win, "_connect_panel_widgets", {})
    if not widgets:
        return
    ui_mode = getattr(win, "_ui_mode", "standard")
    prefs = load_connect_panel_prefs(ui_mode)
    order = [k for k in prefs.get("order", []) if k in widgets]
    for k in CONNECT_PANEL_KEYS:
        if k in widgets and k not in order:
            order.append(k)
    collapsed: dict[str, bool] = dict(prefs.get("collapsed", {}))

    dlg = QtWidgets.QDialog(win)
    dlg.setWindowTitle("Arrange Connect panels")
    dlg.resize(400, 360)
    v = QtWidgets.QVBoxLayout(dlg)
    v.addWidget(
        QtWidgets.QLabel(
            "Drag to reorder. Uncheck to start collapsed. Resize panels on Connect with the drag handles between sections."
        )
    )
    lst = QtWidgets.QListWidget()
    lst.setDragEnabled(True)
    lst.setAcceptDrops(True)
    lst.setDropIndicatorShown(True)
    lst.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
    lst.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
    for key in order:
        item = QtWidgets.QListWidgetItem(CONNECT_PANEL_LABELS.get(key, key))
        item.setData(QtCore.Qt.ItemDataRole.UserRole, key)
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(
            QtCore.Qt.CheckState.Checked
            if not collapsed.get(key, _default_collapsed(key))
            else QtCore.Qt.CheckState.Unchecked
        )
        lst.addItem(item)
    v.addWidget(lst, 1)
    row = QtWidgets.QHBoxLayout()
    ok = QtWidgets.QPushButton("Apply")
    cancel = QtWidgets.QPushButton("Cancel")
    row.addStretch(1)
    row.addWidget(ok)
    row.addWidget(cancel)
    v.addLayout(row)

    def _apply() -> None:
        new_order: list[str] = []
        new_collapsed: dict[str, bool] = {}
        for i in range(lst.count()):
            item = lst.item(i)
            if item is None:
                continue
            key = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "").strip()
            if not key:
                continue
            new_order.append(key)
            new_collapsed[key] = item.checkState() != QtCore.Qt.CheckState.Checked
        save_connect_panel_prefs(
            ui_mode,
            new_order,
            new_collapsed,
            sizes=dict(prefs.get("sizes", {})),
        )
        _rebuild_connect_panels(win)
        if hasattr(win, "_log_ui"):
            win._log_ui("[UI] Updated Connect panel layout.")  # type: ignore[attr-defined]
        dlg.accept()

    ok.clicked.connect(_apply)
    cancel.clicked.connect(dlg.reject)
    dlg.exec()

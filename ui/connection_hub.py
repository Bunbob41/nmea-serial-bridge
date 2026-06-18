"""Connection Hub — card grid for serial/network endpoint discovery."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

_WIDGET_SIZE_MAX = 16777215

from discovery_service import (
    DiscoverySnapshot,
    NetworkCardInfo,
    SerialDeviceInfo,
)


class EndpointCardWidget(QtWidgets.QFrame):
    """One selectable serial or network endpoint card."""

    clicked = QtCore.Signal(str)
    activated = QtCore.Signal(str)
    MIN_WIDTH = 220

    def __init__(
        self,
        device_id: str,
        title: str,
        subtitle: str,
        status: str,
        *,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.device_id = device_id
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setObjectName("endpointCard")
        self.setProperty("selected", False)
        self.setProperty("cardStatus", status)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)
        top = QtWidgets.QHBoxLayout()
        self._title = QtWidgets.QLabel(title)
        self._title.setObjectName("endpointCardTitle")
        self._title.setMinimumWidth(120)
        self._chip = QtWidgets.QLabel(self._status_label(status))
        self._chip.setObjectName("endpointCardStatus")
        top.addWidget(self._title, 1)
        top.addWidget(self._chip, 0)
        lay.addLayout(top)
        self._subtitle = QtWidgets.QLabel(subtitle)
        self._subtitle.setObjectName("endpointCardSubtitle")
        self._subtitle.setWordWrap(True)
        lay.addWidget(self._subtitle)

    @staticmethod
    def _status_label(status: str) -> str:
        return {
            "available": "Detected",
            "ready": "Free",
            "running": "Active",
            "port_busy": "Port busy",
            "stale": "Stale",
            "in_use": "In use",
            "warn": "Warn",
            "ok": "Live",
            "idle": "Idle",
        }.get(status, status.replace("_", " ").title())

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", bool(selected))
        self.style().unpolish(self)
        self.style().polish(self)

    def update_card(self, title: str, subtitle: str, status: str) -> None:
        self._title.setText(title)
        self._subtitle.setText(subtitle)
        self._chip.setText(self._status_label(status))
        self.setProperty("cardStatus", status)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.device_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.device_id)
            self.activated.emit(self.device_id)
        super().mouseDoubleClickEvent(event)



class ConnectionHubWidget(QtWidgets.QWidget):
    """Grid of endpoint cards driven by ``DiscoverySnapshot``."""

    selection_changed = QtCore.Signal(str)
    card_activated = QtCore.Signal(str)
    manual_override_toggled = QtCore.Signal(bool)
    refresh_requested = QtCore.Signal()
    unlock_requested = QtCore.Signal()

    _CARDS_MIN_H = 120
    _MANUAL_MIN_H = 100
    _DEFAULT_SPLIT = (320, 200)
    _CARD_ROW_HEIGHT = 88
    _CARDS_VISIBLE_ROWS = 2

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        standalone: bool = True,
        show_page_header: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("connectionHub")
        self._standalone = bool(standalone)
        self._show_page_header = bool(show_page_header)
        self._bridge_win: Optional[QtWidgets.QWidget] = None
        self._splitter: QtWidgets.QSplitter | None = None
        self._manual_box: QtWidgets.QGroupBox | None = None
        self._manual_inner: QtWidgets.QVBoxLayout | None = None
        cards_view_h = (
            self._CARD_ROW_HEIGHT * self._CARDS_VISIBLE_ROWS
            + max(0, self._CARDS_VISIBLE_ROWS - 1) * 8
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        if self._standalone:
            extra = 96 if self._show_page_header else 48
            self.setMinimumHeight(cards_view_h + extra)
        else:
            self.setMinimumHeight(300)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        header = QtWidgets.QHBoxLayout()
        if self._show_page_header:
            title = QtWidgets.QLabel("Connection hub")
            title.setObjectName("connectionHubTitle")
            header.addWidget(title)
        self.btn_refresh = QtWidgets.QPushButton("Refresh discovery")
        self.btn_refresh.setToolTip(
            "Re-scan USB serial, probe each COM for Free/Port busy, and scan LAN hosts."
        )
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        self.btn_unlock = QtWidgets.QPushButton("Unlock ports")
        self.btn_unlock.setToolTip("Probe/release COM lock; check UDP listen port availability.")
        self.btn_unlock.clicked.connect(self.unlock_requested.emit)
        header.addWidget(self.btn_refresh)
        header.addWidget(self.btn_unlock)
        header.addStretch(1)
        self._refresh_lbl = QtWidgets.QLabel("")
        self._refresh_lbl.setObjectName("connectionHubRefreshHint")
        header.addWidget(self._refresh_lbl)
        root.addLayout(header)

        if self._show_page_header:
            if self._standalone:
                hint_text = (
                    "Click a serial or network tile to fill Control — blue border = hub pick for Start. "
                    "Changing COM on Control syncs the matching serial tile only. "
                    "Refresh discovery probes COM ports for Free (green) vs Port busy (amber)."
                )
            else:
                hint_text = (
                    "Click a tile to fill Control fields — it does not Start the bridge. "
                    "Drag the splitter to resize cards vs Manual override."
                )
            hint = QtWidgets.QLabel(hint_text)
            hint.setWordWrap(True)
            hint.setObjectName("tabHint")
            root.addWidget(hint)

        if self._standalone:
            root.addLayout(self._build_filter_row())

        cards_wrap = self._build_cards_pane(cards_view_h)
        if self._standalone:
            # Stretch=1 lets the cards area fill all remaining tab space instead
            # of leaving an empty void below the fixed-height scroll region.
            root.addWidget(cards_wrap, 1)
        else:
            self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
            self._splitter.setObjectName("connectionHubSplitter")
            self._splitter.setChildrenCollapsible(False)
            self._splitter.setHandleWidth(8)
            self._splitter.setOpaqueResize(True)
            self._splitter.addWidget(cards_wrap)
            self._manual_box = QtWidgets.QGroupBox("Manual override")
            self._manual_box.setObjectName("manualOverrideBox")
            self._manual_box.setCheckable(True)
            self._manual_box.setChecked(False)
            self._manual_box.setMinimumHeight(self._MANUAL_MIN_H)
            self._manual_box.setToolTip(
                "Show full COM, baud, and advanced network fields. "
                "When expanded and edited, hub card defaults are ignored for Start."
            )
            self._manual_inner = QtWidgets.QVBoxLayout(self._manual_box)
            self._manual_inner.setContentsMargins(8, 12, 8, 8)
            self._splitter.addWidget(self._manual_box)
            root.addWidget(self._splitter, 1)
            self._manual_box.toggled.connect(self._on_manual_box_toggled)
            self._splitter.splitterMoved.connect(
                lambda *_a: self._split_save_timer.start(300)
            )

        self._selected_id: Optional[str] = None
        self._pending_serial_port: str = ""
        self._cards: dict[str, EndpointCardWidget] = {}
        self._snapshot: Optional[DiscoverySnapshot] = None
        self._card_filter: str = "all"
        self._max_cols = 2
        self._quality_state: Optional[str] = None
        self._split_save_timer = QtCore.QTimer(self)
        self._split_save_timer.setSingleShot(True)
        self._split_save_timer.timeout.connect(self._persist_hub_split_sizes)

    def _build_cards_pane(self, cards_view_h: int) -> QtWidgets.QWidget:
        cards_wrap = QtWidgets.QWidget()
        cards_wrap.setObjectName("connectionHubCardsPane")
        cards_wrap.setMinimumHeight(cards_view_h)
        cards_lay = QtWidgets.QVBoxLayout(cards_wrap)
        cards_lay.setContentsMargins(0, 0, 0, 0)
        cards_lay.setSpacing(4)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMinimumHeight(cards_view_h)
        scroll.setMaximumHeight(cards_view_h)
        self._cards_host = QtWidgets.QWidget()
        self._cards_host.setObjectName("connectionHubCards")
        self._cards_layout = QtWidgets.QGridLayout(self._cards_host)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setHorizontalSpacing(8)
        self._cards_layout.setVerticalSpacing(8)
        scroll.setWidget(self._cards_host)
        self._card_scroll = scroll
        cards_lay.addWidget(scroll, 0)

        self._empty_hint = QtWidgets.QLabel("")
        self._empty_hint.setObjectName("connectionHubEmptyHint")
        self._empty_hint.setWordWrap(True)
        self._empty_hint.hide()
        cards_lay.addWidget(self._empty_hint)
        return cards_wrap

    @staticmethod
    def _card_kind(device_id: str) -> str:
        did = (device_id or "").strip()
        if did.startswith("serial:"):
            return "serial"
        if did.startswith("net:preset:"):
            return "preset"
        return "network"

    def _card_matches_filter(self, device_id: str) -> bool:
        if self._card_filter == "all":
            return True
        return self._card_kind(device_id) == self._card_filter

    def _build_filter_row(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        self._filter_group = QtWidgets.QButtonGroup(self)
        self._filter_group.setExclusive(True)
        for key, label in (
            ("all", "All"),
            ("serial", "Hardware COM"),
            ("network", "Network Adapters"),
            ("preset", "Presets"),
        ):
            btn = QtWidgets.QPushButton(label)
            btn.setObjectName("connectionHubFilterBtn")
            btn.setCheckable(True)
            btn.setProperty("filterKey", key)
            btn.setToolTip(f"Show {label.lower()} tiles only")
            if key == "all":
                btn.setChecked(True)
            self._filter_group.addButton(btn)
            row.addWidget(btn)
            btn.clicked.connect(lambda _checked=False, k=key: self._set_card_filter(k))
        row.addStretch(1)
        return row

    def _set_card_filter(self, key: str) -> None:
        self._card_filter = key
        if self._snapshot is not None:
            self.set_snapshot(self._snapshot)

    def _on_manual_box_toggled(self, checked: bool) -> None:
        self.manual_override_toggled.emit(checked)
        if self._splitter is None or self._manual_box is None:
            return
        total = max(int(self._splitter.height()), self._CARDS_MIN_H + self._MANUAL_MIN_H)
        if checked:
            self._apply_hub_split_sizes()
            return
        self._splitter.setSizes([max(total - 48, self._CARDS_MIN_H), 0])

    def attach_bridge_window(self, win: QtWidgets.QWidget) -> None:
        """Load/save hub splitter sizes via connect panel prefs."""
        self._bridge_win = win
        if self._standalone:
            QtCore.QTimer.singleShot(0, self.reflow_card_columns)
            return
        QtCore.QTimer.singleShot(0, self._apply_hub_split_sizes)

    def _apply_hub_split_sizes(self) -> None:
        if self._splitter is None or self._manual_box is None:
            return
        if not self._manual_box.isChecked():
            self._on_manual_box_toggled(False)
            return
        top, bottom = self._DEFAULT_SPLIT
        win = self._bridge_win
        if win is not None:
            from ui.ui_prefs import load_connect_panel_prefs

            ui_mode = getattr(win, "_ui_mode", "standard")
            prefs = load_connect_panel_prefs(ui_mode)
            raw = prefs.get("hub_split_sizes")
            if isinstance(raw, (list, tuple)) and len(raw) >= 2:
                try:
                    top = max(self._CARDS_MIN_H, int(raw[0]))
                    bottom = max(self._MANUAL_MIN_H, int(raw[1]))
                except (TypeError, ValueError):
                    pass
        total = max(int(self._splitter.height()), top + bottom)
        if total > top + bottom:
            top = max(self._CARDS_MIN_H, total - bottom)
        self._splitter.setSizes([top, bottom])

    def _persist_hub_split_sizes(self) -> None:
        if self._splitter is None:
            return
        win = self._bridge_win
        if win is None:
            return
        sizes = self._splitter.sizes()
        if len(sizes) < 2 or sizes[0] < 40:
            return
        from ui.ui_prefs import load_connect_panel_prefs, save_connect_panel_prefs

        ui_mode = getattr(win, "_ui_mode", "standard")
        prefs = load_connect_panel_prefs(ui_mode)
        save_connect_panel_prefs(
            ui_mode,
            list(prefs.get("order", [])),
            dict(prefs.get("collapsed", {})),
            sizes=dict(prefs.get("sizes", {})),
            hidden=list(prefs.get("hidden", [])),
            toolbar_order=list(prefs.get("toolbar_order", [])),
            connect_row_style=str(prefs.get("connect_row_style", "pill")),
            hub_split_sizes=[int(sizes[0]), int(sizes[1])],
        )

    def set_manual_override_panel(self, widget: QtWidgets.QWidget) -> None:
        """Embed legacy connection controls inside the manual override group."""
        if self._manual_inner is None:
            return
        self._manual_inner.addWidget(widget)

    def set_manual_override(self, checked: bool) -> None:
        if self._manual_box is not None:
            self._manual_box.setChecked(bool(checked))

    def selected_device_id(self) -> Optional[str]:
        return self._selected_id

    def clear_selection(self) -> None:
        self._selected_id = None
        self._pending_serial_port = ""
        for card in self._cards.values():
            card.set_selected(False)

    def select_serial_port(self, port: str, *, clear_if_missing: bool = True) -> bool:
        """Highlight the hub tile for this COM port (case-insensitive)."""
        port = (port or "").strip()
        if not port or port.startswith("("):
            if clear_if_missing:
                self.clear_selection()
            return False
        match_id: Optional[str] = None
        snap = self._snapshot
        if snap is not None:
            for dev in snap.serial_devices:
                if dev.port.upper() == port.upper():
                    match_id = dev.device_id
                    break
        if match_id is None:
            for did, card in self._cards.items():
                if did.startswith("serial:") and card._title.text().strip().upper() == port.upper():
                    match_id = did
                    break
        if match_id is None:
            self._pending_serial_port = port
            if clear_if_missing:
                self._selected_id = None
                for card in self._cards.values():
                    card.set_selected(False)
            return False
        self._pending_serial_port = ""
        self._selected_id = match_id
        for did, card in self._cards.items():
            card.set_selected(did == match_id)
        self._apply_quality_to_card(match_id)
        return True

    def select_device_id(self, device_id: str) -> bool:
        """Highlight any hub tile (serial or network) by device_id."""
        device_id = (device_id or "").strip()
        if not device_id or device_id not in self._cards:
            return False
        self._pending_serial_port = ""
        self._selected_id = device_id
        for did, card in self._cards.items():
            card.set_selected(did == device_id)
        self._apply_quality_to_card(device_id)
        return True

    def manual_override_active(self) -> bool:
        if self._manual_box is None:
            return False
        return self._manual_box.isChecked()

    def set_snapshot(self, snapshot: DiscoverySnapshot) -> None:
        self._snapshot = snapshot
        serial_ids = {d.device_id for d in snapshot.serial_devices}
        network_ids = {d.device_id for d in snapshot.network_cards}
        keep = serial_ids | network_ids
        for did in list(self._cards.keys()):
            if did not in keep:
                card = self._cards.pop(did)
                self._cards_layout.removeWidget(card)
                card.deleteLater()

        self._max_cols = self._column_count_for_width()
        row = 0
        col = 0

        def _place(card: EndpointCardWidget) -> None:
            nonlocal row, col
            self._cards_layout.addWidget(card, row, col)
            col += 1
            if col >= self._max_cols:
                col = 0
                row += 1

        for dev in snapshot.serial_devices:
            if not self._card_matches_filter(dev.device_id):
                card = self._cards.get(dev.device_id)
                if card is not None:
                    card.hide()
                continue
            card = self._ensure_card(dev)
            card.show()
            _place(card)

        for net in snapshot.network_cards:
            if not self._card_matches_filter(net.device_id):
                card = self._cards.get(net.device_id)
                if card is not None:
                    card.hide()
                continue
            card = self._ensure_card(net)
            card.show()
            _place(card)

        if self._selected_id and self._selected_id not in self._cards:
            self._mark_stale_selected(self._selected_id)
        elif self._selected_id:
            self._cards[self._selected_id].set_selected(True)
        elif self._pending_serial_port:
            self.select_serial_port(self._pending_serial_port, clear_if_missing=False)

        visible_count = sum(1 for card in self._cards.values() if card.isVisible())
        note = getattr(snapshot, "scan_note", "") or ""
        self._refresh_lbl.setText(
            f"{visible_count} card{'s' if visible_count != 1 else ''}"
            + (f" · filter: {self._card_filter}" if self._card_filter != "all" else "")
            + (f" · {note}" if note else "")
        )
        if visible_count == 0:
            empty_msg = "No endpoints match this filter — try All or Refresh discovery."
            if self._card_filter == "all":
                empty_msg = (
                    "No endpoints detected — plug in GNSS USB or Refresh discovery for LAN hosts."
                )
            self._empty_hint.setText(empty_msg)
            self._empty_hint.show()
        else:
            self._empty_hint.hide()
        if self._selected_id:
            self._apply_quality_to_card(self._selected_id)

    def _mark_stale_selected(self, device_id: str) -> None:
        if device_id in self._cards:
            return
        stale = EndpointCardWidget(
            device_id,
            "Previous selection",
            device_id,
            "stale",
            parent=self._cards_host,
        )
        stale.clicked.connect(self._on_card_clicked)
        stale.set_selected(True)
        self._cards[device_id] = stale
        self._cards_layout.addWidget(stale, 0, 0)

    def _ensure_card(self, dev: SerialDeviceInfo | NetworkCardInfo) -> EndpointCardWidget:
        if isinstance(dev, SerialDeviceInfo):
            title = dev.port
            subtitle = " · ".join(
                x for x in (dev.description, dev.manufacturer, dev.match_keyword) if x
            )
            status = dev.status
        else:
            title = dev.label
            extra = f"{dev.peer_count} peer(s)" if dev.peer_count else "no peers yet"
            if not dev.port_available:
                extra = "port in use"
            subtitle = f"{dev.host}:{dev.port} · {extra}"
            status = dev.status

        card = self._cards.get(dev.device_id)
        if card is None:
            card = EndpointCardWidget(
                dev.device_id, title, subtitle, status, parent=self._cards_host
            )
            card.clicked.connect(self._on_card_clicked)
            card.activated.connect(self.card_activated.emit)
            self._cards[dev.device_id] = card
        else:
            card.update_card(title, subtitle, status)
        card.set_selected(dev.device_id == self._selected_id)
        return card

    def _on_card_clicked(self, device_id: str) -> None:
        self._selected_id = device_id
        for did, card in self._cards.items():
            card.set_selected(did == device_id)
        self.selection_changed.emit(device_id)

    def find_serial_port(self, device_id: str) -> Optional[str]:
        if not self._snapshot:
            return None
        for dev in self._snapshot.serial_devices:
            if dev.device_id == device_id:
                return dev.port
        return None

    def find_network_card(self, device_id: str) -> Optional[NetworkCardInfo]:
        if not self._snapshot:
            return None
        for card in self._snapshot.network_cards:
            if card.device_id == device_id:
                return card
        return None

    def set_scan_busy(self, busy: bool) -> None:
        self.btn_refresh.setEnabled(not busy)
        self.btn_unlock.setEnabled(not busy)
        if busy:
            self._refresh_lbl.setText("Scanning…")

    def set_quality(self, device_id: Optional[str], quality: object | None) -> None:
        from ui.hub_quality import TrafficQualitySnapshot

        if not device_id or quality is None:
            self._quality_state = None
            return
        if not isinstance(quality, TrafficQualitySnapshot):
            return
        self._quality_state = quality.state
        self._apply_quality_to_card(device_id, quality)

    def _apply_quality_to_card(
        self, device_id: str, quality: object | None = None
    ) -> None:
        card = self._cards.get(device_id)
        if card is None:
            return
        if quality is not None and hasattr(quality, "summary"):
            sub = card._subtitle.text().split(" · QoS:")[0]
            qos_state = str(getattr(quality, "state", "idle") or "idle")
            card.update_card(card._title.text(), f"{sub} · QoS: {quality.summary}", qos_state)
            return
        if self._quality_state:
            card.update_card(
                card._title.text(),
                card._subtitle.text(),
                str(self._quality_state),
            )

    def _column_count_for_width(self) -> int:
        w = self.width()
        parent = self.parentWidget()
        while parent is not None and w < 320:
            w = max(w, parent.width())
            parent = parent.parentWidget()
        w = max(
            w,
            self._card_scroll.viewport().width(),
            self._cards_host.width(),
            320,
        )
        return max(1, min(4, w // EndpointCardWidget.MIN_WIDTH))

    def reflow_card_columns(self) -> None:
        """Re-grid cards when the hub receives full width."""
        self._cards_host.setMinimumWidth(0)
        self._cards_host.setMaximumWidth(_WIDGET_SIZE_MAX)
        if self._snapshot is not None:
            cols = self._column_count_for_width()
            if cols != self._max_cols:
                self.set_snapshot(self._snapshot)
        if self._manual_box is not None and not self._manual_box.isChecked():
            self._on_manual_box_toggled(False)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._snapshot is not None:
            cols = self._column_count_for_width()
            if cols != self._max_cols:
                self.set_snapshot(self._snapshot)

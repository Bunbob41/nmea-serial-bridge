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
            "available": "Available",
            "ready": "Ready",
            "running": "Running",
            "port_busy": "Port busy",
            "stale": "Stale",
            "in_use": "In use",
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

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.device_id)
        super().mousePressEvent(event)



class ConnectionHubWidget(QtWidgets.QWidget):
    """Grid of endpoint cards driven by ``DiscoverySnapshot``."""

    selection_changed = QtCore.Signal(str)
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
    ) -> None:
        super().__init__(parent)
        self.setObjectName("connectionHub")
        self._standalone = bool(standalone)
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
            self.setMinimumHeight(cards_view_h + 96)
        else:
            self.setMinimumHeight(300)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Connection hub")
        title.setObjectName("connectionHubTitle")
        header.addWidget(title)
        self.btn_refresh = QtWidgets.QPushButton("Refresh discovery")
        self.btn_refresh.setToolTip("Re-scan USB serial and LAN (ARP + UDP probe).")
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

        if self._standalone:
            hint_text = (
                "Pick a detected GNSS serial port or UDP listen context. "
                "Two rows shown — scroll inside for more. "
                "Manual COM/UDP fields live on Connect → Serial & network."
            )
        else:
            hint_text = (
                "Pick a detected GNSS serial port or UDP listen context. "
                "Drag the splitter handle to resize the card area vs Manual override."
            )
        hint = QtWidgets.QLabel(hint_text)
        hint.setWordWrap(True)
        hint.setObjectName("tabHint")
        root.addWidget(hint)

        cards_wrap = self._build_cards_pane(cards_view_h)
        if self._standalone:
            root.addWidget(cards_wrap, 0)
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
        self._cards: dict[str, EndpointCardWidget] = {}
        self._snapshot: Optional[DiscoverySnapshot] = None
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
            card = self._ensure_card(dev)
            _place(card)

        for net in snapshot.network_cards:
            card = self._ensure_card(net)
            _place(card)

        if self._selected_id and self._selected_id not in self._cards:
            self._mark_stale_selected(self._selected_id)
        elif self._selected_id:
            self._cards[self._selected_id].set_selected(True)

        n = len(snapshot.serial_devices) + len(snapshot.network_cards)
        note = getattr(snapshot, "scan_note", "") or ""
        self._refresh_lbl.setText(
            f"{n} card{'s' if n != 1 else ''}" + (f" · {note}" if note else "")
        )
        if n == 0:
            self._empty_hint.setText(
                "No endpoints detected — plug in GNSS USB or Refresh discovery for LAN hosts."
            )
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
            self._cards[dev.device_id] = card
        else:
            card.update_card(title, subtitle, status)
        card.set_selected(dev.device_id == self._selected_id)
        return card

    def _on_card_clicked(self, device_id: str) -> None:
        if self._selected_id == device_id:
            return
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
            st = str(card.property("cardStatus") or "ready")
            card.update_card(card._title.text(), f"{sub} · QoS: {quality.summary}", st)
            card.setProperty("cardStatus", getattr(quality, "state", "idle"))
            card.style().unpolish(card)
            card.style().polish(card)
            return
        if self._quality_state:
            card.setProperty("cardStatus", self._quality_state)

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

"""Connection Hub — card grid for serial/network endpoint discovery."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

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

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("connectionHub")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
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

        hint = QtWidgets.QLabel(
            "Pick a detected GNSS serial port or UDP listen context. "
            "Use Manual override below for TCP modes and edge cases."
        )
        hint.setWordWrap(True)
        hint.setObjectName("tabHint")
        root.addWidget(hint)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cards_host = QtWidgets.QWidget()
        self._cards_host.setObjectName("connectionHubCards")
        self._cards_layout = QtWidgets.QGridLayout(self._cards_host)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setHorizontalSpacing(8)
        self._cards_layout.setVerticalSpacing(8)
        scroll.setWidget(self._cards_host)
        self._card_scroll = scroll
        root.addWidget(scroll, 1)
        self._empty_hint = QtWidgets.QLabel("")
        self._empty_hint.setObjectName("connectionHubEmptyHint")
        self._empty_hint.setWordWrap(True)
        self._empty_hint.hide()
        root.addWidget(self._empty_hint)

        self._manual_box = QtWidgets.QGroupBox("Manual override")
        self._manual_box.setObjectName("manualOverrideBox")
        self._manual_box.setCheckable(True)
        self._manual_box.setChecked(False)
        self._manual_box.setToolTip(
            "Show full COM, baud, and advanced network fields. "
            "When expanded and edited, hub card defaults are ignored for Start."
        )
        self._manual_inner = QtWidgets.QVBoxLayout(self._manual_box)
        self._manual_inner.setContentsMargins(8, 12, 8, 8)
        root.addWidget(self._manual_box)

        self._selected_id: Optional[str] = None
        self._cards: dict[str, EndpointCardWidget] = {}
        self._snapshot: Optional[DiscoverySnapshot] = None
        self._max_cols = 2
        self._quality_state: Optional[str] = None

        self._manual_box.toggled.connect(self.manual_override_toggled.emit)

    def set_manual_override_panel(self, widget: QtWidgets.QWidget) -> None:
        """Embed legacy connection controls inside the manual override group."""
        self._manual_inner.addWidget(widget)

    def selected_device_id(self) -> Optional[str]:
        return self._selected_id

    def manual_override_active(self) -> bool:
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
        w = max(self._cards_host.width(), self._card_scroll.viewport().width(), 240)
        return max(1, min(3, w // EndpointCardWidget.MIN_WIDTH))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._snapshot is not None:
            self.set_snapshot(self._snapshot)

"""Modern Fleet tab - multi-stream table and controls."""
from __future__ import annotations

from typing import Optional, Set

import serial.tools.list_ports
from PySide6 import QtCore, QtGui, QtWidgets

from bridge_core import NetMode
from core.fleet.config import (
    FleetConfig,
    StreamDefinition,
    mavlink_mp_stream,
    normalize_serial_mirror_ports,
    normalize_udp_listen_host,
    suggest_fleet_udp_port,
    validate_fleet_config,
)
from core.fleet.supervisor import FleetSupervisor
from core.fleet.types import StreamRuntimeState, WorkerState
from ui.connection_fields import (
    BAUD_PRESETS,
    DEFAULT_BAUD,
    coerce_baud,
    read_baud_widget,
    sort_com_devices,
    write_baud_widget,
)
from ui.controls import NoWheelComboBox, NoWheelSpinBox, _style_connect_serial_combo
from ui.nmea_display import nmea_mode_display_label
from ui.serial_mirror_fields import SerialMirrorPortPicker


def net_summary(stream: StreamDefinition) -> str:
    mode = stream.net_mode
    if mode == NetMode.UDP_LISTEN.value:
        return f"Listen {stream.udp_host}:{stream.udp_port}"
    if mode == NetMode.UDP_REMOTE.value:
        return f"UDP -> {stream.udp_remote_host}:{stream.udp_remote_port}"
    if mode == NetMode.TCP_CLIENT.value:
        return f"TCP -> {stream.tcp_client_host}:{stream.tcp_client_port}"
    if mode == NetMode.TCP_SERVER.value:
        return f"TCP listen {stream.tcp_host}:{stream.tcp_port}"
    return mode


def com_summary(stream: StreamDefinition) -> str:
    com = (stream.com or "").strip().upper() or "—"
    return f"{com} @ {stream.baud}"


def com_tooltip(stream: StreamDefinition) -> str:
    lines = [f"Bridge COM: {com_summary(stream)}"]
    mirror = stream_mirror_summary(stream)
    if mirror != "—":
        lines.append(f"Mirror leg(s): {mirror}")
    if stream.primary:
        lines.append("Primary stream for Survey HUD.")
    if not stream.enabled:
        lines.append("Row disabled — enable in Edit to start.")
    return "\n".join(lines)


def stream_mode_summary(stream: StreamDefinition) -> str:
    mode = nmea_mode_display_label(stream.nmea_mode)
    extras: list[str] = []
    if stream.udp_fanout and stream.net_mode == NetMode.UDP_LISTEN.value:
        extras.append("fan-out")
    if stream.local_backup:
        extras.append("backup")
    if extras:
        return f"{mode} · " + " · ".join(extras)
    return mode


def stream_mode_tooltip(stream: StreamDefinition) -> str:
    lines = [
        f"NMEA mode: {stream.nmea_mode} ({nmea_mode_display_label(stream.nmea_mode)})",
        f"UDP fan-out: {'on' if stream.udp_fanout else 'off'}",
        f"Local backup: {'on' if stream.local_backup else 'off'}",
    ]
    if stream.nmea_mode != "raw":
        lines.append(
            "MAVLink, RTCM, and other binary streams usually need Raw mode."
        )
    return "\n".join(lines)


def stream_mirror_summary(stream: StreamDefinition) -> str:
    ports = [p.strip().upper() for p in (stream.serial_mirror_ports or []) if (p or "").strip()]
    if not ports:
        return "—"
    text = ", ".join(ports)
    if stream.serial_mirror_device_tx:
        text += " +TX"
    return text


def stream_mirror_tooltip(stream: StreamDefinition) -> str:
    ports = [p.strip().upper() for p in (stream.serial_mirror_ports or []) if (p or "").strip()]
    if not ports:
        return "No com0com mirror leg — add in Edit for passive sniff."
    lines = [f"Mirror COM(s): {', '.join(ports)}"]
    if stream.serial_mirror_device_tx:
        lines.append("Include device TX: on (required for Cube / MAVLink output).")
    else:
        lines.append(
            "Include device TX: off — enable for raw/MAVLink streams that only emit on TX."
        )
    return "\n".join(lines)


def net_tooltip(stream: StreamDefinition) -> str:
    lines = [f"Network: {net_summary(stream)}"]
    if stream.net_mode == NetMode.UDP_LISTEN.value:
        host = normalize_udp_listen_host(stream.udp_host)
        port = int(stream.udp_port)
        if host == "127.0.0.1":
            lines.append(
                "Listen host is loopback only — remote Mission Planner / Tailscale cannot connect. "
                "Use 0.0.0.0 for LAN or Tailscale."
            )
        else:
            lines.append(
                f"Remote Mission Planner: UDP Client → this PC's LAN or Tailscale IP:{port} "
                "(not 127.0.0.1 from another machine)."
            )
            lines.append("Allow inbound UDP on this port in Windows Firewall.")
        if stream.udp_fanout:
            lines.append("Fan-out on: every UDP peer that sends first gets COM→net replies.")
        else:
            lines.append("Fan-out off: only the most recent sender gets COM→net.")
    return "\n".join(lines)


_COL_LABEL = 0
_COL_COM = 1
_COL_NETWORK = 2
_COL_MODE = 3
_COL_MIRROR = 4
_COL_STATE = 5
_COL_BACKLOG = 6
_COL_ACTIVITY = 7
_COL_ACTIONS = 8
_RUNTIME_REFRESH_MS = 450


class _FleetRowActions(QtWidgets.QWidget):
    """Per-row Start / Stop / Edit controls."""

    def __init__(
        self,
        panel: "FleetPanelWidget",
        stream_id: str,
        *,
        worker_state: WorkerState,
        enabled: bool,
    ) -> None:
        super().__init__(panel)
        self.setObjectName("fleetRowActions")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        style = QtWidgets.QApplication.style()
        icon_sz = QtCore.QSize(14, 14)
        self._btn_start = QtWidgets.QPushButton()
        self._btn_start.setObjectName("fleetRowActionBtn")
        self._btn_stop = QtWidgets.QPushButton()
        self._btn_stop.setObjectName("fleetRowActionBtn")
        self._btn_edit = QtWidgets.QPushButton()
        self._btn_edit.setObjectName("fleetRowActionBtn")
        self._btn_start.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay)
        )
        self._btn_stop.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaStop)
        )
        self._btn_edit.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView)
        )
        for btn in (self._btn_start, self._btn_stop, self._btn_edit):
            btn.setIconSize(icon_sz)
            btn.setFixedSize(28, 22)
            btn.setMinimumHeight(22)
            lay.addWidget(btn)
        running = worker_state in (
            WorkerState.STARTING,
            WorkerState.RUNNING,
            WorkerState.STOPPING,
        )
        self._btn_start.setEnabled(enabled and not running)
        self._btn_stop.setEnabled(running)
        self._btn_start.setToolTip(
            "Start this stream only" if enabled else "Enable the stream in Edit first"
        )
        self._btn_stop.setToolTip("Stop this stream")
        self._btn_edit.setToolTip("Edit stream settings (double-click row also works)")
        self._btn_start.clicked.connect(
            lambda *_: panel._on_row_start(stream_id)
        )
        self._btn_stop.clicked.connect(
            lambda *_: panel._on_row_stop(stream_id)
        )
        self._btn_edit.clicked.connect(
            lambda *_: panel._on_edit_stream_id(stream_id)
        )


def _set_table_text(
    table: QtWidgets.QTableWidget,
    row: int,
    col: int,
    text: str,
    *,
    tooltip: str = "",
    placeholder: bool = False,
) -> None:
    shown = str(text or "").strip()
    if not shown and placeholder:
        shown = "—"
    item = table.item(row, col)
    if item is None:
        item = QtWidgets.QTableWidgetItem(shown)
        table.setItem(row, col, item)
    else:
        if item.text() == shown and item.toolTip() == tooltip:
            return
        item.setText(shown)
    if placeholder and shown == "—":
        item.setForeground(QtGui.QColor("#64748b"))
    if tooltip:
        item.setToolTip(tooltip)
    elif item.toolTip():
        item.setToolTip("")


def _fleet_select_combo(
    parent: QtWidgets.QWidget | None = None,
) -> NoWheelComboBox:
    """Dropdown with visible chevron (matches Connect / Control styling)."""
    combo = NoWheelComboBox(parent)
    combo.setObjectName("fleetStreamSelectCombo")
    combo.setEditable(False)
    _style_connect_serial_combo(combo)
    return combo


def _fleet_port_spin(value: int, *, parent: QtWidgets.QWidget | None = None) -> NoWheelSpinBox:
    """Wide enough for 5-digit ports + clickable step buttons (WebPortSpinBox pattern)."""
    spin = NoWheelSpinBox(parent)
    spin.setObjectName("fleetStreamPortSpin")
    spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.UpDownArrows)
    spin.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    spin.setMinimumWidth(140)
    spin.setRange(1, 65535)
    spin.setValue(int(value))
    return spin


def populate_com_combo(combo: QtWidgets.QComboBox, current: str = "") -> None:
    """Fill COM dropdown from serial.tools.list_ports (same idea as Control refresh)."""
    prev = (current or combo.currentText()).strip().upper()
    combo.blockSignals(True)
    try:
        combo.clear()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            combo.addItem("(no ports — click Refresh)")
            combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
            return
        for device in sort_com_devices(ports):
            combo.addItem(device)
        combo.setMaxVisibleItems(16)
        combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        if prev:
            idx = combo.findText(prev, QtCore.Qt.MatchFlag.MatchFixedString)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.insertItem(0, prev)
                combo.setCurrentIndex(0)
    finally:
        combo.blockSignals(False)


class StreamEditDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        stream: StreamDefinition | None = None,
    ) -> None:
        super().__init__(parent)
        self._stream = stream or StreamDefinition.new("Stream")
        self.setObjectName("fleetStreamEditDialog")
        self.setWindowTitle("Edit stream" if stream else "Add stream")
        self.setMinimumWidth(460)
        self.setMinimumHeight(440)
        lay = QtWidgets.QFormLayout(self)
        lay.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self._label = QtWidgets.QLineEdit(self._stream.label)

        com_row = QtWidgets.QHBoxLayout()
        self._com = NoWheelComboBox()
        self._com.setObjectName("fleetStreamComCombo")
        self._com.setEditable(False)
        self._com.setMinimumWidth(180)
        self._com.setMinimumHeight(34)
        _style_connect_serial_combo(self._com)
        populate_com_combo(self._com, self._stream.com)
        btn_refresh = QtWidgets.QPushButton("Refresh")
        btn_refresh.setObjectName("modernToolsSecondaryBtn")
        btn_refresh.setToolTip("Rescan COM ports on this PC")
        btn_refresh.clicked.connect(self._refresh_stream_com_fields)
        com_row.addWidget(self._com, 1)
        com_row.addWidget(btn_refresh, 0)

        self._baud = NoWheelComboBox()
        self._baud.setObjectName("connectBaudCombo")
        self._baud.setEditable(False)
        _style_connect_serial_combo(self._baud)
        for rate in BAUD_PRESETS:
            self._baud.addItem(str(rate))
        write_baud_widget(self._baud, coerce_baud(self._stream.baud, default=DEFAULT_BAUD))

        self._enabled = QtWidgets.QCheckBox("Enabled")
        self._enabled.setChecked(self._stream.enabled)
        self._primary = QtWidgets.QCheckBox("Primary (HUD)")
        self._primary.setChecked(self._stream.primary)

        self._nmea = _fleet_select_combo()
        for key in ("passthrough", "strict", "raw"):
            self._nmea.addItem(key, key)
        idx = self._nmea.findData(self._stream.nmea_mode)
        if idx >= 0:
            self._nmea.setCurrentIndex(idx)

        self._net = _fleet_select_combo()
        for m in NetMode:
            self._net.addItem(m.value.replace("_", " "), m.value)
        nidx = self._net.findData(self._stream.net_mode)
        if nidx >= 0:
            self._net.setCurrentIndex(nidx)

        self._udp_host = QtWidgets.QLineEdit(normalize_udp_listen_host(self._stream.udp_host))
        self._udp_host.setToolTip(
            "Address this stream binds on this PC.\n"
            "0.0.0.0 = all interfaces (LAN + Tailscale) — required for remote Mission Planner.\n"
            "127.0.0.1 = this PC only (bench). Remote senders cannot reach loopback."
        )
        self._udp_port = _fleet_port_spin(self._stream.udp_port)
        self._udp_remote_host = QtWidgets.QLineEdit(self._stream.udp_remote_host)
        self._udp_remote_port = _fleet_port_spin(self._stream.udp_remote_port)
        self._tcp_host = QtWidgets.QLineEdit(self._stream.tcp_host)
        self._tcp_port = _fleet_port_spin(self._stream.tcp_port)
        self._tcp_client_host = QtWidgets.QLineEdit(self._stream.tcp_client_host)
        self._tcp_client_port = _fleet_port_spin(self._stream.tcp_client_port)

        self._mirror_ports = SerialMirrorPortPicker(self)
        self._mirror_ports.set_ports(self._stream.serial_mirror_ports)
        self._mirror_ports.refresh(primary_com=self._stream.com)
        self._mirror_device_tx = QtWidgets.QCheckBox("Include device TX on serial mirrors")
        self._mirror_device_tx.setChecked(bool(self._stream.serial_mirror_device_tx))
        self._mirror_device_tx.setToolTip(
            "Copies bytes read from the device (COM→network) to mirror ports.\n"
            "Required for MAVLink / raw monitor legs — Cube→Mission Planner is device TX.\n"
            "Mirrors always copy network→COM even when this is off."
        )

        self._listen_host_label = QtWidgets.QLabel("UDP listen host")
        self._listen_port_label = QtWidgets.QLabel("UDP listen port")
        self._remote_host_label = QtWidgets.QLabel("UDP remote host")
        self._remote_port_label = QtWidgets.QLabel("UDP remote port")
        self._tcp_host_label = QtWidgets.QLabel("TCP listen host")
        self._tcp_port_label = QtWidgets.QLabel("TCP listen port")
        self._tcp_client_host_label = QtWidgets.QLabel("TCP remote host")
        self._tcp_client_port_label = QtWidgets.QLabel("TCP remote port")

        lay.addRow("Label", self._label)
        lay.addRow("COM", com_row)
        lay.addRow("Baud", self._baud)
        lay.addRow("", self._enabled)
        lay.addRow("", self._primary)
        lay.addRow("NMEA mode", self._nmea)
        lay.addRow("Network", self._net)
        lay.addRow("Serial mirrors", self._mirror_ports)
        lay.addRow("", self._mirror_device_tx)
        lay.addRow(self._listen_host_label, self._udp_host)
        lay.addRow(self._listen_port_label, self._udp_port)
        lay.addRow(self._remote_host_label, self._udp_remote_host)
        lay.addRow(self._remote_port_label, self._udp_remote_port)
        lay.addRow(self._tcp_host_label, self._tcp_host)
        lay.addRow(self._tcp_port_label, self._tcp_port)
        lay.addRow(self._tcp_client_host_label, self._tcp_client_host)
        lay.addRow(self._tcp_client_port_label, self._tcp_client_port)

        self._net.currentIndexChanged.connect(self._sync_network_fields)
        self._com.currentTextChanged.connect(
            lambda text: self._mirror_ports.refresh(primary_com=text)
        )
        self._nmea.currentIndexChanged.connect(self._sync_mirror_defaults)
        self._mirror_ports._cb1.currentTextChanged.connect(self._sync_mirror_defaults)
        self._mirror_ports._cb2.currentTextChanged.connect(self._sync_mirror_defaults)
        self._sync_network_fields()
        self._sync_mirror_defaults()

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addRow(btns)

    def _refresh_stream_com_fields(self) -> None:
        populate_com_combo(self._com)
        self._mirror_ports.refresh(primary_com=self._com.currentText().strip())

    def _sync_network_fields(self) -> None:
        mode = str(self._net.currentData() or NetMode.UDP_LISTEN.value)
        listen = mode == NetMode.UDP_LISTEN.value
        remote = mode == NetMode.UDP_REMOTE.value
        tcp_srv = mode == NetMode.TCP_SERVER.value
        tcp_cli = mode == NetMode.TCP_CLIENT.value
        self._listen_host_label.setVisible(listen)
        self._udp_host.setVisible(listen)
        self._listen_port_label.setVisible(listen)
        self._udp_port.setVisible(listen)
        self._remote_host_label.setVisible(remote)
        self._udp_remote_host.setVisible(remote)
        self._remote_port_label.setVisible(remote)
        self._udp_remote_port.setVisible(remote)
        self._tcp_host_label.setVisible(tcp_srv)
        self._tcp_host.setVisible(tcp_srv)
        self._tcp_port_label.setVisible(tcp_srv)
        self._tcp_port.setVisible(tcp_srv)
        self._tcp_client_host_label.setVisible(tcp_cli)
        self._tcp_client_host.setVisible(tcp_cli)
        self._tcp_client_port_label.setVisible(tcp_cli)
        self._tcp_client_port.setVisible(tcp_cli)

    def _sync_mirror_defaults(self) -> None:
        """Raw / MAVLink streams need device TX on mirrors to copy Cube output."""
        if str(self._nmea.currentData()) != "raw":
            return
        if not self._mirror_ports.text().strip():
            return
        if not self._mirror_device_tx.isChecked():
            self._mirror_device_tx.setChecked(True)

    def result_stream(self) -> StreamDefinition:
        s = self._stream
        s.label = self._label.text().strip() or "Stream"
        s.com = self._com.currentText().strip().upper()
        if s.com.startswith("("):
            s.com = ""
        s.baud = coerce_baud(int(read_baud_widget(self._baud) or DEFAULT_BAUD))
        s.enabled = self._enabled.isChecked()
        s.primary = self._primary.isChecked()
        s.nmea_mode = str(self._nmea.currentData())
        s.net_mode = str(self._net.currentData())
        s.udp_host = normalize_udp_listen_host(self._udp_host.text())
        s.udp_port = int(self._udp_port.value())
        s.udp_remote_host = self._udp_remote_host.text().strip()
        s.udp_remote_port = int(self._udp_remote_port.value())
        s.tcp_host = self._tcp_host.text().strip() or "0.0.0.0"
        s.tcp_port = int(self._tcp_port.value())
        s.tcp_client_host = self._tcp_client_host.text().strip() or "127.0.0.1"
        s.tcp_client_port = int(self._tcp_client_port.value())
        s.serial_mirror_ports = normalize_serial_mirror_ports(
            self._mirror_ports.text(), primary=s.com
        )
        s.serial_mirror_device_tx = self._mirror_device_tx.isChecked()
        return s


class FleetPanelWidget(QtWidgets.QWidget):
    def __init__(self, host: QtWidgets.QWidget) -> None:
        super().__init__(host)
        self._host = host
        self.setObjectName("modernFleetBody")
        self._supervisor: Optional[FleetSupervisor] = None
        self._stream_row: dict[str, int] = {}
        self._fleet_action_busy = False
        self._runtime_dirty: Set[str] = set()
        self._runtime_refresh_timer = QtCore.QTimer(self)
        self._runtime_refresh_timer.setSingleShot(True)
        self._runtime_refresh_timer.setInterval(_RUNTIME_REFRESH_MS)
        self._runtime_refresh_timer.timeout.connect(self._flush_runtime_rows)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        toolbar = QtWidgets.QHBoxLayout()
        self._btn_add = QtWidgets.QPushButton("Add stream")
        self._btn_add.setObjectName("modernToolsPrimaryBtn")
        self._btn_add_mavlink = QtWidgets.QPushButton("Add MAVLink / MP")
        self._btn_add_mavlink.setObjectName("modernToolsSecondaryBtn")
        self._btn_add_mavlink.setToolTip(
            "Cube + Mission Planner: Raw binary, UDP listen 0.0.0.0:14550, fan-out on. "
            "Pick the Cube MAVLink COM in the dialog, then Start all. "
            "Same PC: MP → UDP Client → 127.0.0.1:14550. "
            "Remote / Tailscale: MP → UDP Client → survey PC Tailscale IP:14550."
        )
        self._btn_start = QtWidgets.QPushButton("Start all")
        self._btn_stop = QtWidgets.QPushButton("Stop all")
        self._btn_delete = QtWidgets.QPushButton("Delete")
        self._btn_delete.setObjectName("modernToolsSecondaryBtn")
        self._auto_start = QtWidgets.QCheckBox("Start fleet on launch")
        self._auto_start.setToolTip("Off by default until you trust this setup.")
        for w in (self._btn_add, self._btn_add_mavlink, self._btn_start, self._btn_stop, self._btn_delete):
            toolbar.addWidget(w)
        toolbar.addStretch(1)
        toolbar.addWidget(self._auto_start)
        lay.addLayout(toolbar)
        self._table = QtWidgets.QTableWidget(0, 9)
        self._table.setObjectName("modernFleetTable")
        self._table.setHorizontalHeaderLabels(
            [
                "Label",
                "COM",
                "Network",
                "Mode",
                "Mirror",
                "State",
                "Backlog",
                "Activity",
                "Actions",
            ]
        )
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self._table.setMinimumHeight(0)
        self._table.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(_COL_LABEL, QtWidgets.QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(_COL_COM, QtWidgets.QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(_COL_NETWORK, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for col in (_COL_MODE, _COL_MIRROR, _COL_STATE, _COL_BACKLOG, _COL_ACTIVITY):
            hdr.setSectionResizeMode(
                col, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
            )
        hdr.setSectionResizeMode(_COL_ACTIONS, QtWidgets.QHeaderView.ResizeMode.Fixed)
        hdr.setDefaultAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        actions_hdr = self._table.horizontalHeaderItem(_COL_ACTIONS)
        if actions_hdr is not None:
            actions_hdr.setTextAlignment(
                QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        self._table.setColumnWidth(_COL_LABEL, 120)
        self._table.setColumnWidth(_COL_COM, 132)
        self._table.setColumnWidth(_COL_ACTIONS, 96)
        vhdr = self._table.verticalHeader()
        vhdr.setVisible(False)
        vhdr.setDefaultSectionSize(26)
        vhdr.setMinimumSectionSize(24)
        hdr.sectionResized.connect(self._elide_fleet_label_cells)
        lay.addWidget(self._table, 1)
        self._status = QtWidgets.QLabel("")
        self._status.setObjectName("modernFleetStatus")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)
        self._btn_add.clicked.connect(self._on_add)
        self._btn_add_mavlink.clicked.connect(self._on_add_mavlink)
        self._btn_start.clicked.connect(self._on_start_all)
        self._btn_stop.clicked.connect(self._on_stop_all)
        self._btn_delete.clicked.connect(self._on_delete)
        self._auto_start.toggled.connect(self._on_auto_start_toggled)
        self._table.cellDoubleClicked.connect(self._on_edit_row)

    def _elide_fleet_label_cells(self, *_args: object) -> None:
        col_w = self._table.columnWidth(_COL_LABEL)
        if col_w <= 24:
            return
        fm = self._table.fontMetrics()
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_LABEL)
            if item is None:
                continue
            full = str(
                item.data(QtCore.Qt.ItemDataRole.UserRole) or item.text() or ""
            ).strip()
            if not full:
                continue
            item.setToolTip(full)
            item.setText(
                fm.elidedText(
                    full,
                    QtCore.Qt.TextElideMode.ElideRight,
                    max(32, col_w - 12),
                )
            )

    def _set_fleet_label_cell(self, row: int, label: str) -> None:
        full = str(label or "").strip()
        item = self._table.item(row, _COL_LABEL)
        if item is None:
            item = QtWidgets.QTableWidgetItem()
            self._table.setItem(row, _COL_LABEL, item)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, full)
        item.setToolTip(full)
        col_w = self._table.columnWidth(_COL_LABEL)
        if col_w > 24:
            item.setText(
                self._table.fontMetrics().elidedText(
                    full,
                    QtCore.Qt.TextElideMode.ElideRight,
                    max(32, col_w - 12),
                )
            )
        else:
            item.setText(full)

    def attach_supervisor(self, supervisor: FleetSupervisor) -> None:
        self._supervisor = supervisor
        supervisor.fleet_changed.connect(self.refresh_table)
        supervisor.stream_state_changed.connect(self._on_stream_state_changed)
        self._auto_start.setChecked(supervisor.config().auto_start_on_launch)
        self.refresh_table()

    def _on_stream_state_changed(self, stream_id: str, state: object) -> None:
        st = state if isinstance(state, StreamRuntimeState) else None
        if st is not None and st.worker_state != WorkerState.RUNNING:
            self._update_runtime_row(stream_id)
            return
        if st is not None and (
            st.drops_n2s
            or st.drops_s2n
            or (st.backlog_line() not in ("", "ok"))
        ):
            self._update_runtime_row(stream_id)
            return
        self._runtime_dirty.add(stream_id)
        if not self._runtime_refresh_timer.isActive():
            self._runtime_refresh_timer.start()

    def _flush_runtime_rows(self) -> None:
        dirty = self._runtime_dirty
        self._runtime_dirty = set()
        for stream_id in dirty:
            self._update_runtime_row(stream_id)

    def _activity_text(
        self, stream: StreamDefinition, st: Optional[StreamRuntimeState]
    ) -> str:
        if st is None:
            return ""
        activity = st.activity_token()
        if (
            st.worker_state == WorkerState.RUNNING
            and st.active_com
            and stream.com.strip().upper() != st.active_com.strip().upper()
        ):
            activity = f"live {st.active_com} (saved {stream.com.strip().upper()})"
        return activity

    def _backlog_tooltip(self, backlog: str) -> str:
        if not backlog or backlog == "ok":
            return ""
        return (
            "Bridge queue/drop pressure — open Activity for detail. "
            "q = net→COM + COM→net chunks waiting."
        )

    def _set_config_cells(self, row: int, stream: StreamDefinition) -> None:
        _set_table_text(
            self._table,
            row,
            _COL_COM,
            com_summary(stream),
            tooltip=com_tooltip(stream),
        )
        _set_table_text(
            self._table,
            row,
            _COL_NETWORK,
            net_summary(stream),
            tooltip=net_tooltip(stream),
        )
        _set_table_text(
            self._table,
            row,
            _COL_MODE,
            stream_mode_summary(stream),
            tooltip=stream_mode_tooltip(stream),
        )
        _set_table_text(
            self._table,
            row,
            _COL_MIRROR,
            stream_mirror_summary(stream),
            tooltip=stream_mirror_tooltip(stream),
            placeholder=True,
        )

    def _set_runtime_cells(
        self,
        row: int,
        stream: StreamDefinition,
        st: Optional[StreamRuntimeState],
    ) -> None:
        state_txt = st.worker_state.value if st else WorkerState.IDLE.value
        backlog = st.backlog_line() if st else ""
        activity = self._activity_text(stream, st)
        _set_table_text(self._table, row, _COL_STATE, state_txt, placeholder=True)
        _set_table_text(
            self._table,
            row,
            _COL_BACKLOG,
            backlog,
            tooltip=self._backlog_tooltip(backlog),
            placeholder=True,
        )
        _set_table_text(self._table, row, _COL_ACTIVITY, activity, placeholder=True)

    def _set_row_actions(
        self,
        row: int,
        stream: StreamDefinition,
        st: Optional[StreamRuntimeState],
    ) -> None:
        ws = st.worker_state if st else WorkerState.IDLE
        self._table.setCellWidget(
            row,
            _COL_ACTIONS,
            _FleetRowActions(
                self,
                stream.id,
                worker_state=ws,
                enabled=stream.enabled,
            ),
        )

    def _set_fleet_action_busy(self, busy: bool) -> None:
        self._fleet_action_busy = busy
        self._btn_start.setEnabled(not busy)
        self._btn_stop.setEnabled(not busy)

    def _update_all_runtime_rows(self) -> None:
        sup = self._supervisor
        if sup is None:
            return
        for stream in sup.config().streams:
            self._update_runtime_row(stream.id)

    def _update_runtime_row(self, stream_id: str) -> None:
        sup = self._supervisor
        if sup is None:
            return
        row = self._stream_row.get(stream_id)
        if row is None:
            self.refresh_table()
            return
        stream = sup.config().stream_by_id(stream_id)
        if stream is None:
            return
        st = sup.runtime_states().get(stream_id)
        self._set_runtime_cells(row, stream, st)
        self._set_row_actions(row, stream, st)
        self._refresh_status_line(sup.config(), sup.runtime_states())

    def _refresh_status_line(
        self, cfg: FleetConfig, states: dict[str, StreamRuntimeState]
    ) -> None:
        error_rows = [
            s.label
            for s in cfg.streams
            if (st := states.get(s.id))
            and st.worker_state == WorkerState.ERROR
            and st.error_message
        ]
        mirror_hints = [
            s.label
            for s in cfg.streams
            if s.nmea_mode == "raw"
            and s.serial_mirror_ports
            and not s.serial_mirror_device_tx
            and (st := states.get(s.id))
            and st.worker_state == WorkerState.RUNNING
        ]
        if error_rows:
            self._status.setText(
                "Fleet error: " + "; ".join(error_rows[:2])
                + ("..." if len(error_rows) > 2 else "")
            )
        elif mirror_hints:
            self._status.setText(
                f"Mirror hint: enable Include device TX on "
                f"{mirror_hints[0]} (raw/MAVLink needs it for Cube output)."
            )
        elif not cfg.streams:
            self._status.setText(
                "Add a stream for each wired sensor COM. One row = one pipe to the network."
            )
        else:
            self._status.setText(f"{len(cfg.streams)} stream(s) configured.")

    def refresh_table(self) -> None:
        self._runtime_refresh_timer.stop()
        self._runtime_dirty.clear()
        sup = self._supervisor
        if sup is None:
            return
        cfg = sup.config()
        states = sup.runtime_states()
        self._stream_row = {s.id: i for i, s in enumerate(cfg.streams)}
        self._table.setUpdatesEnabled(False)
        try:
            self._table.setRowCount(len(cfg.streams))
            for row, stream in enumerate(cfg.streams):
                st = states.get(stream.id)
                label = stream.label + ("  [Primary]" if stream.primary else "")
                if not stream.enabled:
                    label += "  (off)"
                self._set_fleet_label_cell(row, label)
                self._set_config_cells(row, stream)
                self._set_runtime_cells(row, stream, st)
                self._set_row_actions(row, stream, st)
            self._refresh_status_line(cfg, states)
        finally:
            self._table.setUpdatesEnabled(True)

    def _selected_stream_id(self) -> Optional[str]:
        row = self._table.currentRow()
        sup = self._supervisor
        if sup is None or row < 0:
            return None
        streams = sup.config().streams
        if row >= len(streams):
            return None
        return streams[row].id

    def _save_config(self, cfg: FleetConfig) -> bool:
        sup = self._supervisor
        if sup is None:
            return False
        errors = sup.replace_config(cfg)
        if errors:
            QtWidgets.QMessageBox.warning(self, "Fleet config", "\n".join(errors))
            return False
        return True

    def _on_add(self) -> None:
        sup = self._supervisor
        if sup is None:
            return
        cfg = sup.config()
        label = f"Stream {len(cfg.streams) + 1}"
        suggested = suggest_fleet_udp_port(cfg)
        dlg = StreamEditDialog(self, StreamDefinition.new(label, udp_port=suggested))
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        new_stream = dlg.result_stream()
        if new_stream.primary:
            cfg.set_primary(new_stream.id)
        cfg.streams.append(new_stream)
        self._save_config(cfg)

    def _on_add_mavlink(self) -> None:
        sup = self._supervisor
        if sup is None:
            return
        cfg = sup.config()
        if len(cfg.streams) >= 8:
            QtWidgets.QMessageBox.warning(
                self,
                "Fleet config",
                "Fleet supports at most 8 streams. Delete a row before adding MAVLink / MP.",
            )
            return
        from core.fleet.config import FLEET_MAVLINK_MP_UDP_PORT

        for stream in cfg.streams:
            if (
                stream.net_mode == NetMode.UDP_LISTEN.value
                and int(stream.udp_port) == FLEET_MAVLINK_MP_UDP_PORT
            ):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Fleet config",
                    f"UDP listen port {FLEET_MAVLINK_MP_UDP_PORT} is already used by "
                    f"stream «{stream.label}». Edit that row or pick another port.",
                )
                return
        dlg = StreamEditDialog(self, mavlink_mp_stream())
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        new_stream = dlg.result_stream()
        new_stream.udp_fanout = True
        new_stream.nmea_mode = "raw"
        if new_stream.primary:
            cfg.set_primary(new_stream.id)
        cfg.streams.append(new_stream)
        self._save_config(cfg)

    def _on_edit_stream_id(self, stream_id: str) -> None:
        sup = self._supervisor
        if sup is None:
            return
        streams = sup.config().streams
        row = self._stream_row.get(stream_id)
        if row is None or row < 0 or row >= len(streams):
            return
        dlg = StreamEditDialog(self, streams[row])
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        cfg = sup.config()
        updated = dlg.result_stream()
        if updated.primary:
            cfg.set_primary(updated.id)
        cfg.streams[row] = updated
        self._save_config(cfg)

    def _on_edit_row(self, row: int, _col: int) -> None:
        sup = self._supervisor
        if sup is None:
            return
        streams = sup.config().streams
        if row < 0 or row >= len(streams):
            return
        self._on_edit_stream_id(streams[row].id)

    def _on_row_start(self, stream_id: str) -> None:
        if self._fleet_action_busy:
            return
        self._set_fleet_action_busy(True)
        QtCore.QTimer.singleShot(0, lambda sid=stream_id: self._run_row_start(sid))

    def _run_row_start(self, stream_id: str) -> None:
        try:
            sup = self._supervisor
            if sup is None:
                return
            errors = sup.start_stream(stream_id)
            if errors:
                self._status.setText("; ".join(errors[:3]))
            self._update_runtime_row(stream_id)
        finally:
            self._set_fleet_action_busy(False)

    def _on_row_stop(self, stream_id: str) -> None:
        if self._fleet_action_busy:
            return
        self._set_fleet_action_busy(True)
        QtCore.QTimer.singleShot(0, lambda sid=stream_id: self._run_row_stop(sid))

    def _run_row_stop(self, stream_id: str) -> None:
        try:
            sup = self._supervisor
            if sup is None:
                return
            errors = sup.stop_stream(stream_id)
            if errors:
                self._status.setText("; ".join(errors[:3]))
            self._update_runtime_row(stream_id)
        finally:
            self._set_fleet_action_busy(False)

    def _on_delete(self) -> None:
        sid = self._selected_stream_id()
        sup = self._supervisor
        if sid is None or sup is None:
            return
        sup.stop_stream(sid)
        cfg = sup.config()
        cfg.streams = [s for s in cfg.streams if s.id != sid]
        self._save_config(cfg)

    def _on_start_all(self) -> None:
        if self._fleet_action_busy:
            return
        self._set_fleet_action_busy(True)
        QtCore.QTimer.singleShot(0, self._run_start_all)

    def _run_start_all(self) -> None:
        try:
            sup = self._supervisor
            if sup is None:
                return
            errors = sup.start_all()
            if errors:
                self._status.setText("; ".join(errors[:3]))
            else:
                running = sum(
                    1
                    for st in sup.runtime_states().values()
                    if st.worker_state == WorkerState.RUNNING
                )
                self._status.setText(
                    f"Fleet running ({running} stream(s))."
                    if running
                    else "No enabled streams to start."
                )
            self._update_all_runtime_rows()
        finally:
            self._set_fleet_action_busy(False)

    def _on_stop_all(self) -> None:
        if self._fleet_action_busy:
            return
        self._set_fleet_action_busy(True)
        QtCore.QTimer.singleShot(0, self._run_stop_all)

    def _run_stop_all(self) -> None:
        try:
            sup = self._supervisor
            if sup is None:
                return
            errors = sup.stop_all()
            if errors:
                self._status.setText("Stop issues: " + "; ".join(errors[:3]))
            else:
                self._status.setText("Fleet stopped.")
            self._update_all_runtime_rows()
        finally:
            self._set_fleet_action_busy(False)

    def _on_auto_start_toggled(self, checked: bool) -> None:
        sup = self._supervisor
        if sup is None:
            return
        cfg = sup.config()
        cfg.auto_start_on_launch = checked
        sup.replace_config(cfg)


def build_fleet_panel(host: QtWidgets.QWidget) -> FleetPanelWidget:
    panel = FleetPanelWidget(host)
    host._fleet_panel = panel
    return panel
"""Shared Qt controls used by every UI variant."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from bridge_core import (
    DEFAULT_TCP_RECONNECT_S,
    TCP_RECONNECT_MAX_S,
    TCP_RECONNECT_MIN_S,
    UI_VIEW_MAX_BLOCK_COUNT,
)
from nmea_codec import NMEA_SENTENCE_TYPES
from ui.connection_fields import BAUD_PRESETS, DEFAULT_BAUD
from ui.styles import THEME_LABELS
from ui.theme_choice import (
    THEME_FOREST,
    THEME_MAROON,
    THEME_MIDNIGHT,
    THEME_OCEAN,
    THEME_RANDOM_CURRENT,
    THEME_RANDOM_FAVORITE,
    THEME_SLATE,
    THEME_SUNSET,
    load_random_seed_lock,
    load_theme_zone_order,
)

_STATUS_CHIP_MAX_H = 32
_CONNECT_COMBO_MIN_H = 30


def _style_connect_serial_combo(combo: QtWidgets.QComboBox) -> None:
    """Enough vertical room for the drop-down arrow (apple-round QSS clips otherwise)."""
    combo.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
    combo.setMinimumHeight(_CONNECT_COMBO_MIN_H)
    combo.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )


class NoWheelComboBox(QtWidgets.QComboBox):
    """Block mouse-wheel value changes (scroll the page instead)."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        event.ignore()  # never change value; let the scroll area handle it


class NoWheelDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """Block mouse-wheel value changes."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        event.ignore()  # never change value; let the scroll area handle it


class NoWheelSpinBox(QtWidgets.QSpinBox):
    """Block mouse-wheel value changes (scroll the Tools page instead)."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        event.ignore()


class WebPortSpinBox(QtWidgets.QSpinBox):
    """Phone dashboard Web API port — compact, no wheel, step buttons honor port unlock control."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("webPortSpin")
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        # Wide enough for 5-digit ports + native step buttons (avoid arrow/text overlap).
        self.setFixedWidth(152)

    def _unlock_checked(self) -> bool:
        win = self.window()
        chk = getattr(win, "chk_web_port_unlock", None)
        return chk is not None and chk.isChecked()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        event.ignore()

    def stepEnabled(self) -> QtWidgets.QAbstractSpinBox.StepEnabled:
        if not self._unlock_checked():
            return QtWidgets.QAbstractSpinBox.StepEnabled.StepNone
        return super().stepEnabled()

    def stepBy(self, steps: int) -> None:
        if not self._unlock_checked():
            return
        super().stepBy(steps)
_STATUS_BAR_H = 32


def _status_bar_for_label(lbl: QtWidgets.QLabel) -> QtWidgets.QStatusBar | None:
    w: QtWidgets.QWidget | None = lbl
    for _ in range(8):
        if w is None:
            return None
        if isinstance(w, QtWidgets.QStatusBar):
            return w
        w = w.parentWidget()
    return None


def wire_status_bar(win: QtWidgets.QWidget) -> None:
    """Keep status chips single-line; full text on hover."""
    bar = getattr(win, "statusBar", None)
    if bar is not None:
        bar.setSizeGripEnabled(False)
        bar.setFixedHeight(_STATUS_BAR_H)
    for name in ("status_serial", "status_network", "status_nmea", "status_gnss", "lbl_stats"):
        lbl = getattr(win, name, None)
        if lbl is None:
            continue
        lbl.setWordWrap(False)
        lbl.setMinimumWidth(0)
        lbl.setMaximumHeight(_STATUS_CHIP_MAX_H)
        lbl.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
    stats = getattr(win, "lbl_stats", None)
    if stats is not None:
        stats.setObjectName("lblStats")
        stats.setMinimumWidth(200)


def refresh_status_bar_labels(win: QtWidgets.QWidget) -> None:
    """Re-apply elision after resize (stats line uses remaining bar width)."""
    for name in ("status_serial", "status_network", "status_nmea", "status_gnss", "lbl_stats"):
        lbl = getattr(win, name, None)
        if lbl is None:
            continue
        tip = lbl.toolTip()
        text = tip if tip else lbl.text()
        if text:
            elide_status_label(lbl, text)


def apply_compact_intent_hint(lbl: QtWidgets.QLabel, full_text: str) -> None:
    """Single-line intent hint with full text on hover (Field / compact layouts)."""
    full = (full_text or "").strip()
    lbl.setToolTip(full)
    if not full:
        lbl.clear()
        lbl.setVisible(False)
        return
    lbl.setVisible(True)
    parent = lbl.parentWidget()
    slot_w = max(200, (parent.width() - 24) if parent and parent.width() > 80 else 480)
    elided = lbl.fontMetrics().elidedText(full, QtCore.Qt.TextElideMode.ElideRight, slot_w)
    lbl.setText(elided)


def _status_label_slot_width(lbl: QtWidgets.QLabel) -> int:
    """Pixels available for one status-bar label (stats uses the remainder)."""
    bar = _status_bar_for_label(lbl)
    if bar is None or bar.width() <= 80:
        return max(120, lbl.width() - 6)
    stats = lbl
    if lbl.objectName() != "lblStats":
        stats = bar.findChild(QtWidgets.QLabel, "lblStats")
    if stats is not None and lbl is stats:
        used = 0
        for child in bar.findChildren(QtWidgets.QLabel):
            if child is stats or not child.isVisible():
                continue
            used += child.sizeHint().width() + 8
        return max(200, bar.width() - used - 16)
    return max(88, (bar.width() - 24) // 4)


def elide_status_label(lbl: QtWidgets.QLabel, text: str) -> None:
    """Show one line in the status bar; keep full string in the tooltip."""
    full = (text or "").strip()
    slot_w = _status_label_slot_width(lbl)
    elided = lbl.fontMetrics().elidedText(full, QtCore.Qt.TextElideMode.ElideRight, slot_w)
    if lbl.toolTip() == full and lbl.text() == elided:
        return
    lbl.setToolTip(full)
    lbl.setText(elided)


def wire_connection_controls(win: QtWidgets.QWidget) -> None:
    """Connect signals shared by all layouts (after controls exist on win)."""
    win.refresh_btn.clicked.connect(win.refresh_ports)
    win.start_btn.clicked.connect(win.start_bridge)
    win.stop_btn.clicked.connect(win.stop_bridge)
    win.chk_advanced_net.toggled.connect(win._on_advanced_net_toggle)
    for rb in (win.rb_udp_listen, win.rb_udp_remote, win.rb_tcp_server, win.rb_tcp_client):
        rb.toggled.connect(win._mode_toggle)
    for w in (win.udp_host, win.udp_port):
        w.textChanged.connect(win._refresh_intent_hint)
    win.btn_insert_sample.clicked.connect(win._insert_send_sample)
    win.btn_send_ser.clicked.connect(lambda: win._send_manual("serial"))
    win.btn_send_net.clicked.connect(lambda: win._send_manual("net"))
    win.btn_send_both.clicked.connect(lambda: win._send_manual("both"))
    win.btn_browse.clicked.connect(win._browse_log)
    win.btn_clear_ui.clicked.connect(win.log_view.clear)
    if hasattr(win, "btn_save_live_log"):
        win.btn_save_live_log.clicked.connect(win._save_live_log)
    if hasattr(win, "chk_log_hex"):
        for rb in (win.rb_nmea_passthrough, win.rb_nmea_strict, win.rb_nmea_raw):
            rb.toggled.connect(win._sync_log_hex_toggle)
        win.chk_log_hex.toggled.connect(win._on_log_hex_toggled)
    if hasattr(win, "cmb_log_preset"):
        win.cmb_log_preset.currentIndexChanged.connect(win._on_log_preset_combo_changed)
    if hasattr(win, "btn_log_view"):
        win.btn_log_view.clicked.connect(win._open_log_view_dialog)
    if hasattr(win, "chk_verbose_log"):
        win.chk_verbose_log.toggled.connect(win._on_log_verbose_toggled)
    for rb in (
        getattr(win, "rb_nmea_passthrough", None),
        getattr(win, "rb_nmea_strict", None),
        getattr(win, "rb_nmea_raw", None),
    ):
        if rb is not None:
            rb.toggled.connect(win._sync_nmea_mode_ui)
    wire_status_bar(win)


def create_connection_controls(parent: QtWidgets.QWidget) -> None:
    """Attach serial + network + path widgets to parent (stored on parent window)."""
    p = parent

    p.com_cb = NoWheelComboBox()
    p.com_cb.setObjectName("connectComCombo")
    _style_connect_serial_combo(p.com_cb)
    p.refresh_btn = QtWidgets.QPushButton("Refresh")
    p.baud_edit = NoWheelComboBox()
    p.baud_edit.setObjectName("connectBaudCombo")
    _style_connect_serial_combo(p.baud_edit)
    p.baud_edit.setEditable(False)
    p.baud_edit.setToolTip(
        "Serial baud — must match the GNSS/INS port. Standard survey rates only."
    )
    for rate in BAUD_PRESETS:
        p.baud_edit.addItem(str(rate))
    p.baud_edit.setCurrentText(str(DEFAULT_BAUD))

    p.chk_serial_auto_reconnect = QtWidgets.QCheckBox("Auto-reconnect COM if link drops")
    p.chk_serial_auto_reconnect.setChecked(True)
    p.chk_serial_auto_reconnect.setToolTip(
        "While the bridge is Running, retry opening the COM port every few seconds "
        "after a disconnect (USB glitch, cable bump). Network forwarding stays up."
    )

    p.chk_auto_discover = QtWidgets.QCheckBox("Auto-connect on GNSS device detected")
    p.chk_auto_discover.setChecked(False)
    p.chk_auto_discover.setToolTip(
        "Watch for USB-serial GNSS devices (Trimble, U-blox, NovAtel, …) in the "
        "background.  When a matching device appears, its COM port is selected "
        "automatically.  If the bridge is stopped and a preset is loaded, it also "
        "starts the bridge.\n\n"
        "Leave unchecked for full manual control."
    )

    p.udp_host = QtWidgets.QLineEdit("0.0.0.0")
    p.udp_host.setToolTip(
        "UDP listen bind address on this PC (0.0.0.0 = all interfaces). "
        "Senders must target this host/port; the bridge does not connect outbound."
    )
    p.udp_port = QtWidgets.QLineEdit("10110")
    p.udp_port.setToolTip(
        "UDP listen port. Bench simulators and INS outputs send datagrams here "
        "(e.g. 127.0.0.1:10110 on one PC)."
    )
    p.chk_tcp_sink_enable = QtWidgets.QCheckBox("Extra TCP output")
    p.chk_tcp_sink_enable.setChecked(False)
    p.chk_tcp_sink_enable.setToolTip(
        "While Running, opens a TCP server on this PC so other programs can connect "
        "and receive the same COM→network stream as your main path (e.g. UDP on 10110). "
        "Does not replace UDP listen or fan-out."
    )
    p.tcp_sink_port = QtWidgets.QLineEdit("10111")
    p.tcp_sink_port.setToolTip(
        "TCP port for Extra TCP output (default 10111). Clients connect here to listen."
    )

    p.chk_udp_fanout = QtWidgets.QCheckBox("Fan-out  —  send serial data to all UDP peers")
    p.chk_udp_fanout.setChecked(True)
    p.chk_udp_fanout.setToolTip(
        "UDP listen mode only.\n\n"
        "Checked (Fan-out): serial→network data is broadcast to every UDP sender that has\n"
        "contacted the bridge during this session.\n\n"
        "Unchecked (Single-link): only the most recent sender receives the serial stream\n"
        "(legacy one-to-one behaviour)."
    )
    p.chk_advanced_net = QtWidgets.QCheckBox("Advanced network (TCP / UDP remote / all modes)")
    p.chk_advanced_net.setToolTip(
        "Show full network mode picker (UDP listen, UDP remote, TCP server, TCP client) "
        "and extra fields — similar to ncat/com2tcp-style endpoint control."
    )

    p.mode_group = QtWidgets.QButtonGroup(parent)
    p.rb_udp_listen = QtWidgets.QRadioButton("UDP listen")
    p.rb_udp_remote = QtWidgets.QRadioButton("UDP remote")
    p.rb_tcp_server = QtWidgets.QRadioButton("TCP server")
    p.rb_tcp_client = QtWidgets.QRadioButton("TCP client")
    p.rb_udp_listen.setChecked(True)
    for rb in (p.rb_udp_listen, p.rb_udp_remote, p.rb_tcp_server, p.rb_tcp_client):
        p.mode_group.addButton(rb)

    p._advanced_net = QtWidgets.QWidget()
    p._advanced_net.setObjectName("advancedNetPanel")
    adv = QtWidgets.QVBoxLayout(p._advanced_net)
    adv.setContentsMargins(0, 0, 0, 0)
    adv.setSpacing(10)

    def _stack_group(box: QtWidgets.QGroupBox) -> None:
        box.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )

    p._mode_box = QtWidgets.QGroupBox("Mode")
    _stack_group(p._mode_box)
    mv = QtWidgets.QVBoxLayout(p._mode_box)
    mv.setContentsMargins(8, 12, 8, 8)
    mv.setSpacing(6)
    mv.addWidget(p.rb_udp_listen)
    mv.addWidget(p.rb_udp_remote)
    mv.addWidget(p.rb_tcp_server)
    mv.addWidget(p.rb_tcp_client)
    adv.addWidget(p._mode_box)

    p._udp_box = QtWidgets.QGroupBox("UDP remote (fixed peer)")
    _stack_group(p._udp_box)
    uf = QtWidgets.QFormLayout(p._udp_box)
    p.remote_host = QtWidgets.QLineEdit("192.168.1.100")
    p.remote_port = QtWidgets.QLineEdit("10110")
    uf.addRow("Host:", p.remote_host)
    uf.addRow("Port:", p.remote_port)
    adv.addWidget(p._udp_box)

    p._tcp_srv_box = QtWidgets.QGroupBox("TCP server")
    _stack_group(p._tcp_srv_box)
    tsf = QtWidgets.QFormLayout(p._tcp_srv_box)
    p.tcp_srv_host = QtWidgets.QLineEdit("0.0.0.0")
    p.tcp_srv_port = QtWidgets.QLineEdit("4001")
    tsf.addRow("Bind:", p.tcp_srv_host)
    tsf.addRow("Port:", p.tcp_srv_port)
    adv.addWidget(p._tcp_srv_box)

    p._tcp_cli_box = QtWidgets.QGroupBox("TCP client")
    _stack_group(p._tcp_cli_box)
    tcf = QtWidgets.QFormLayout(p._tcp_cli_box)
    p.tcp_cli_host = QtWidgets.QLineEdit("127.0.0.1")
    p.tcp_cli_port = QtWidgets.QLineEdit("4001")
    tcf.addRow("Host:", p.tcp_cli_host)
    tcf.addRow("Port:", p.tcp_cli_port)
    adv.addWidget(p._tcp_cli_box)

    p.tcp_reconnect_spin = NoWheelDoubleSpinBox()
    p.tcp_reconnect_spin.setRange(TCP_RECONNECT_MIN_S, TCP_RECONNECT_MAX_S)
    p.tcp_reconnect_spin.setSingleStep(0.5)
    p.tcp_reconnect_spin.setDecimals(1)
    p.tcp_reconnect_spin.setSuffix(" s")
    p.tcp_reconnect_spin.setValue(DEFAULT_TCP_RECONNECT_S)
    p.tcp_reconnect_spin.setToolTip(
        "TCP client mode only: seconds to wait before each reconnect attempt when the server drops."
    )
    recon_row = QtWidgets.QHBoxLayout()
    recon_lbl = QtWidgets.QLabel("TCP reconnect delay")
    recon_lbl.setToolTip(
        "Used when Advanced → TCP client is selected. Ignored for UDP and TCP server."
    )
    recon_row.addWidget(recon_lbl)
    recon_row.addWidget(p.tcp_reconnect_spin)
    recon_row.addStretch(1)
    adv.addLayout(recon_row)
    p._advanced_net.setVisible(False)
    p._advanced_net.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.MinimumExpanding,
    )

    p.start_btn = QtWidgets.QPushButton("Start")
    p.start_btn.setObjectName("btnStart")
    p.stop_btn = QtWidgets.QPushButton("Stop")
    p.stop_btn.setObjectName("btnStop")
    p.stop_btn.setEnabled(False)

    p._connection_widgets = [
        p.com_cb,
        p.refresh_btn,
        p.baud_edit,
        p.chk_serial_auto_reconnect,
        p.chk_advanced_net,
        p.rb_udp_listen,
        p.rb_udp_remote,
        p.rb_tcp_server,
        p.rb_tcp_client,
        p.udp_host,
        p.udp_port,
        p.remote_host,
        p.remote_port,
        p.tcp_srv_host,
        p.tcp_srv_port,
        p.tcp_cli_host,
        p.tcp_cli_port,
        p.tcp_reconnect_spin,
        p.tcp_sink_port,
    ]


def create_presets_tab(
    parent: QtWidgets.QWidget,
    *,
    include_advanced_net: bool = True,
) -> QtWidgets.QWidget:
    from ui.presets_panel import create_presets_tab as _build

    return _build(parent, include_advanced_net=include_advanced_net)


def create_net_tab_scroll(parent: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
    """Scrollable Net tab for compact layouts (log-first drawer, minimal tools)."""
    from ui.tool_tabs import _scrollable

    host = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(8, 6, 8, 8)
    lay.setSpacing(8)
    lay.addWidget(parent.chk_advanced_net)
    lay.addWidget(parent._advanced_net)
    lay.addWidget(parent.chk_serial_auto_reconnect)
    lay.addWidget(parent.chk_auto_discover)
    lay.addStretch(1)
    scroll = _scrollable(host)
    scroll.setMinimumHeight(220)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return scroll


def create_nmea_controls(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tool_tabs import _scrollable

    w = QtWidgets.QWidget()
    w.setObjectName("toolTabScrollHost")
    v = QtWidgets.QVBoxLayout(w)
    v.setContentsMargins(14, 14, 14, 14)
    hint = QtWidgets.QLabel(
        "Mode is stored in Tools → Presets when you Save or Save as…. "
        "Loading a preset restores these radios (and strict sentence types)."
    )
    hint.setWordWrap(True)
    hint.setObjectName("tabHint")
    v.addWidget(hint)
    parent.nmea_mode_group = QtWidgets.QButtonGroup(parent)
    parent.rb_nmea_passthrough = QtWidgets.QRadioButton("Passthrough (recommended)")
    parent.rb_nmea_strict = QtWidgets.QRadioButton("Strict + sentence filter")
    parent.rb_nmea_raw = QtWidgets.QRadioButton("Raw binary (RTCM / other)")
    parent.rb_nmea_passthrough.setChecked(True)
    parent.rb_nmea_passthrough.setToolTip(
        "Default for Trimble R10 NMEA and bench simulators — lines forwarded with minimal changes."
    )
    parent.rb_nmea_strict.setToolTip(
        "Verify NMEA checksums and only forward checked sentence types (bench QA)."
    )
    parent.nmea_mode_group.addButton(parent.rb_nmea_passthrough)
    parent.nmea_mode_group.addButton(parent.rb_nmea_strict)
    parent.nmea_mode_group.addButton(parent.rb_nmea_raw)
    v.addWidget(parent.rb_nmea_passthrough)
    v.addWidget(parent.rb_nmea_strict)
    v.addWidget(parent.rb_nmea_raw)
    parent.rb_nmea_raw.setToolTip(
        "Forward bytes without NMEA line assembly or checksum checks. "
        "Use when the receiver outputs RTCM or other binary streams (not NMEA text)."
    )
    types_box = QtWidgets.QGroupBox("Strict: allowed types (NMEA text only)")
    parent._nmea_strict_types_box = types_box
    grid = QtWidgets.QGridLayout(types_box)
    parent._nmea_type_checks = {}
    for i, st in enumerate(NMEA_SENTENCE_TYPES):
        cb = QtWidgets.QCheckBox(st)
        cb.setChecked(st in {"GGA", "RMC", "ZDA"})
        parent._nmea_type_checks[st] = cb
        grid.addWidget(cb, i // 3, i % 3)
    v.addWidget(types_box)
    v.addStretch(1)
    parent._nmea_widgets = [
        parent.rb_nmea_passthrough,
        parent.rb_nmea_strict,
        parent.rb_nmea_raw,
        *parent._nmea_type_checks.values(),
    ]
    return _scrollable(w)


def create_theme_controls(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tool_tabs import _scrollable

    host = QtWidgets.QWidget()
    host.setObjectName("toolTabScrollHost")
    host.setProperty("themeStudio", True)
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(14, 14, 14, 14)
    lay.setSpacing(10)

    hint = QtWidgets.QLabel(
        "Optional colors for bench or training setups. "
        "Defaults are fine — most operators connect, start the bridge, then minimize."
    )
    hint.setWordWrap(True)
    hint.setObjectName("themeStudioHint")
    lay.addWidget(hint)

    grp = QtWidgets.QGroupBox("Theme")
    grp.setObjectName("themeStudioCard")
    gf = QtWidgets.QFormLayout(grp)
    parent.cmb_theme_choice = QtWidgets.QComboBox()
    parent.cmb_theme_choice.setObjectName("themeStudioCombo")
    theme_order = (
        THEME_MAROON,
        THEME_OCEAN,
        THEME_SLATE,
        THEME_FOREST,
        THEME_SUNSET,
        THEME_MIDNIGHT,
    THEME_RANDOM_CURRENT,
        THEME_RANDOM_FAVORITE,
    )
    for tid in theme_order:
        parent.cmb_theme_choice.addItem(THEME_LABELS.get(tid, tid), tid)
    parent.cmb_theme_choice.currentIndexChanged.connect(parent._on_theme_choice_changed)
    gf.addRow("Theme:", parent.cmb_theme_choice)

    parent.chk_theme_seed_lock = QtWidgets.QCheckBox("Lock random seed (same vibe)")
    parent.chk_theme_seed_lock.setObjectName("themeStudioSeedLock")
    parent.chk_theme_seed_lock.setToolTip(
        "When enabled, each Randomize click produces the next deterministic variation from one style family."
    )
    parent.chk_theme_seed_lock.setChecked(load_random_seed_lock())
    parent.chk_theme_seed_lock.toggled.connect(parent._set_random_seed_lock)
    gf.addRow("", parent.chk_theme_seed_lock)
    parent._theme_zone_buttons = {}
    parent.theme_zone_list = QtWidgets.QListWidget()
    parent.theme_zone_list.setObjectName("presetList")
    parent.theme_zone_list.setMinimumHeight(160)
    parent.theme_zone_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    parent.theme_zone_list.setDragEnabled(True)
    parent.theme_zone_list.setAcceptDrops(True)
    parent.theme_zone_list.setDropIndicatorShown(True)
    parent.theme_zone_list.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
    parent.theme_zone_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
    parent.theme_zone_list.model().rowsMoved.connect(parent._on_theme_zone_rows_moved)
    zone_labels = {
        "background": "Background",
        "topbar": "Top bar",
        "tabs": "Tabs",
        "buttons": "Buttons",
        "inputs": "Inputs",
        "logs": "Log panel",
        "accent": "Accent",
    }
    for zone_id in load_theme_zone_order():
        label = zone_labels.get(zone_id, zone_id.title())
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QtWidgets.QLabel(label))
        swatch = QtWidgets.QPushButton("#000000")
        swatch.setObjectName("themeStudioZoneSwatch")
        swatch.setMinimumWidth(128)
        swatch.clicked.connect(lambda checked=False, z=zone_id: parent._pick_theme_zone_color(z))
        row.addWidget(swatch)
        reset_btn = QtWidgets.QPushButton("Reset")
        reset_btn.setObjectName("themeStudioZoneReset")
        reset_btn.setMaximumWidth(62)
        reset_btn.clicked.connect(lambda checked=False, z=zone_id: parent._reset_theme_zone_color(z))
        row.addWidget(reset_btn)
        row.addStretch(1)
        wrap = QtWidgets.QWidget()
        wrap.setLayout(row)
        item = QtWidgets.QListWidgetItem()
        item.setData(QtCore.Qt.ItemDataRole.UserRole, zone_id)
        item.setSizeHint(wrap.sizeHint())
        parent.theme_zone_list.addItem(item)
        parent.theme_zone_list.setItemWidget(item, wrap)
        parent._theme_zone_buttons[zone_id] = swatch
    gf.addRow("Zone order:", parent.theme_zone_list)
    lay.addWidget(grp)

    row = QtWidgets.QHBoxLayout()
    parent.btn_theme_randomize = QtWidgets.QPushButton("Randomize")
    parent.btn_theme_randomize.setObjectName("themeStudioRandomBtn")
    parent.btn_theme_randomize.setToolTip(
        "New randomized palette (Ctrl+R). Double-click within ~0.3 s for a variant in the same family."
    )
    parent.btn_theme_randomize.clicked.connect(parent._randomize_theme_now)
    parent.btn_theme_standardize = QtWidgets.QPushButton("Standardize")
    parent.btn_theme_standardize.setObjectName("themeStudioFavBtn")
    parent.btn_theme_standardize.setToolTip(
        "Cohesive Field Slate–style palette (Ctrl+Shift+R). "
        "Double-click quickly for a subtle variant."
    )
    parent.btn_theme_standardize.clicked.connect(parent._standardize_theme_now)
    parent.btn_theme_save_favorite = QtWidgets.QPushButton("Save current random as favorite")
    parent.btn_theme_save_favorite.setObjectName("themeStudioFavBtn")
    parent.btn_theme_save_favorite.clicked.connect(parent._save_current_random_theme_as_favorite)
    row.addWidget(parent.btn_theme_randomize)
    row.addWidget(parent.btn_theme_standardize)
    row.addWidget(parent.btn_theme_save_favorite)
    row.addStretch(1)
    lay.addLayout(row)

    io_row = QtWidgets.QHBoxLayout()
    parent.btn_theme_export_pack = QtWidgets.QPushButton("Export theme pack…")
    parent.btn_theme_export_pack.setObjectName("themeStudioIOBtn")
    parent.btn_theme_export_pack.clicked.connect(parent._export_theme_pack)
    parent.btn_theme_import_pack = QtWidgets.QPushButton("Import theme pack…")
    parent.btn_theme_import_pack.setObjectName("themeStudioIOBtn")
    parent.btn_theme_import_pack.clicked.connect(parent._import_theme_pack)
    io_row.addWidget(parent.btn_theme_export_pack)
    io_row.addWidget(parent.btn_theme_import_pack)
    io_row.addStretch(1)
    lay.addLayout(io_row)

    presets_grp = QtWidgets.QGroupBox("Saved theme presets")
    presets_grp.setObjectName("themeStudioCard")
    pv = QtWidgets.QVBoxLayout(presets_grp)
    parent.theme_preset_list = QtWidgets.QListWidget()
    parent.theme_preset_list.setObjectName("presetList")
    parent.theme_preset_list.setMinimumHeight(120)
    parent.theme_preset_list.setSelectionMode(
        QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
    )
    parent.theme_preset_list.setDragEnabled(True)
    parent.theme_preset_list.setAcceptDrops(True)
    parent.theme_preset_list.setDropIndicatorShown(True)
    parent.theme_preset_list.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
    parent.theme_preset_list.setDragDropMode(
        QtWidgets.QAbstractItemView.DragDropMode.InternalMove
    )
    parent.theme_preset_list.model().rowsMoved.connect(parent._on_theme_preset_rows_moved)
    parent.theme_preset_list.itemClicked.connect(parent._on_theme_preset_item_clicked)
    pv.addWidget(parent.theme_preset_list)
    pr = QtWidgets.QHBoxLayout()
    parent.btn_theme_preset_save = QtWidgets.QPushButton("Save as preset…")
    parent.btn_theme_preset_save.setObjectName("themeStudioIOBtn")
    parent.btn_theme_preset_save.clicked.connect(parent._save_theme_preset_prompt)
    parent.btn_theme_preset_load = QtWidgets.QPushButton("Load")
    parent.btn_theme_preset_load.setObjectName("themeStudioIOBtn")
    parent.btn_theme_preset_load.clicked.connect(parent._load_selected_theme_preset)
    parent.btn_theme_preset_delete = QtWidgets.QPushButton("Delete")
    parent.btn_theme_preset_delete.setObjectName("themeStudioIOBtn")
    parent.btn_theme_preset_delete.clicked.connect(parent._delete_selected_theme_preset)
    pr.addWidget(parent.btn_theme_preset_save)
    pr.addWidget(parent.btn_theme_preset_load)
    pr.addWidget(parent.btn_theme_preset_delete)
    pr.addStretch(1)
    pv.addLayout(pr)
    lay.addWidget(presets_grp)

    note = QtWidgets.QLabel(
        "Tip: choose Favorite random to reuse your saved palette across sessions. "
        "Export/import packs to share looks."
    )
    note.setObjectName("themeStudioTip")
    note.setWordWrap(True)
    lay.addWidget(note)
    lay.addStretch(1)
    return _scrollable(host)


def create_send_controls(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tool_tabs import build_send_tab

    return build_send_tab(parent)


def create_system_terminal_tab(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.system_terminal import build_system_terminal_tab

    return build_system_terminal_tab(parent)


def create_diagnostics_controls(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tool_tabs import build_diagnostics_tab

    return build_diagnostics_tab(parent)


def create_guide_tab(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tool_tabs import build_guide_tab

    return build_guide_tab(parent)


def create_phone_dashboard_tab(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tool_tabs import build_phone_dashboard_tab

    return build_phone_dashboard_tab(parent)


def create_log_panel(
    parent: QtWidgets.QWidget,
    *,
    show_toggle: bool = False,
    show_header: bool = True,
) -> QtWidgets.QWidget:
    panel = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 0)
    hdr = QtWidgets.QHBoxLayout()
    parent.chk_show_log = QtWidgets.QCheckBox("Show log")
    parent.chk_log_pause = QtWidgets.QCheckBox("Pause")
    parent.chk_log_pause.setToolTip("Freeze the live log display (bridge keeps running).")
    parent.chk_verbose_log = QtWidgets.QCheckBox("Every NMEA line")
    parent.chk_verbose_log.setToolTip(
        "When checked, each accepted NMEA sentence is copied into the live log. "
        "When off, only status, drops, rejects, and other events appear (less noise at high rates)."
    )
    parent.chk_log_hex = QtWidgets.QCheckBox("Hex (raw)")
    parent.chk_log_hex.setToolTip(
        "Raw binary mode only: show hex bytes in the live log instead of decoded text. "
        "Use for RTCM or other binary bench checks."
    )
    parent.chk_log_hex.setEnabled(False)
    from ui.log_view import PRESET_LABELS, TOOLBAR_PRESETS

    parent.cmb_log_preset = QtWidgets.QComboBox()
    parent.cmb_log_preset.setMinimumWidth(148)
    for key in TOOLBAR_PRESETS:
        parent.cmb_log_preset.addItem(PRESET_LABELS[key], key)
    parent.cmb_log_preset.setToolTip(
        "Quick live-log presets. Use View… for RX/TX/warnings, NMEA types, and hex display."
    )
    parent.btn_log_view = QtWidgets.QPushButton("View…")
    parent.btn_log_view.setToolTip(
        "Open live log filters: traffic direction, NMEA verbosity, sentence types, and hex preview."
    )
    parent.chk_show_log.setChecked(True)
    parent.chk_verbose_log.setChecked(True)
    parent.btn_clear_log = QtWidgets.QPushButton("Clear")
    parent.btn_save_live_log = QtWidgets.QPushButton("Save…")
    parent.btn_save_live_log.setToolTip("Export the on-screen live log to a text file.")
    if show_toggle:
        hdr.addWidget(parent.chk_show_log)
    else:
        parent.chk_show_log.hide()
    hdr.addWidget(parent.chk_log_pause)
    hdr.addWidget(parent.chk_verbose_log)
    hdr.addWidget(parent.chk_log_hex)
    hdr.addWidget(parent.cmb_log_preset)
    hdr.addWidget(parent.btn_log_view)
    hdr.addStretch(1)
    hdr.addWidget(parent.btn_save_live_log)
    hdr.addWidget(parent.btn_clear_log)
    if show_header:
        lay.addLayout(hdr)
    else:
        for w in (
            parent.chk_log_pause,
            parent.chk_verbose_log,
            parent.chk_log_hex,
            parent.cmb_log_preset,
            parent.btn_log_view,
            parent.btn_save_live_log,
            parent.btn_clear_log,
        ):
            w.hide()
    parent.log_view = QtWidgets.QPlainTextEdit()
    parent.log_view.setObjectName("logView")
    parent.log_view.setReadOnly(True)
    parent.log_view.setMaximumBlockCount(UI_VIEW_MAX_BLOCK_COUNT)
    lay.addWidget(parent.log_view, 1)
    if show_toggle:
        parent.chk_show_log.toggled.connect(parent._toggle_log_panel)
    parent.chk_log_pause.toggled.connect(parent._set_log_pause)
    parent.btn_clear_log.clicked.connect(parent.log_view.clear)
    return panel


CONNECT_MINI_LOG_MAX_BLOCKS = 100


CONNECT_TERMINAL_MAX_BLOCKS = 120


def create_connect_mini_log(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Compact log strip body for the Connect tab (wrap in collapsible panel)."""
    body = QtWidgets.QWidget()
    body.setObjectName("connectMiniLogBox")
    lay = QtWidgets.QVBoxLayout(body)
    lay.setContentsMargins(0, 0, 0, 0)
    hint = QtWidgets.QLabel(
        "Mirrors key bridge lines. Full filters on the Log tab; auto-switch after 20 s when Running."
    )
    hint.setWordWrap(True)
    hint.setObjectName("tabHint")
    lay.addWidget(hint)
    parent.connect_mini_log = QtWidgets.QPlainTextEdit()
    parent.connect_mini_log.setObjectName("connectMiniLog")
    parent.connect_mini_log.setReadOnly(True)
    parent.connect_mini_log.setMaximumBlockCount(CONNECT_MINI_LOG_MAX_BLOCKS)
    parent.connect_mini_log.setMinimumHeight(48)
    parent.connect_mini_log.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Expanding,
    )
    parent.connect_mini_log.setPlaceholderText("Start the bridge to see connection events here…")
    from ui.fonts import monospace_ui_font

    parent.connect_mini_log.setFont(monospace_ui_font())
    lay.addWidget(parent.connect_mini_log, 1)
    return body


def create_connect_quick_terminal(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Command mini-terminal: script output + quick NMEA inject to serial."""
    body = QtWidgets.QWidget()
    body.setObjectName("connectQuickTerminal")
    lay = QtWidgets.QVBoxLayout(body)
    lay.setContentsMargins(0, 0, 0, 0)
    hint = QtWidgets.QLabel(
        "Preflight/diagnostic output and one-line Send→COM (bridge must be Running). "
        "Multi-line inject: Tools → Inject."
    )
    hint.setWordWrap(True)
    hint.setObjectName("tabHint")
    lay.addWidget(hint)
    parent.connect_terminal_out = QtWidgets.QPlainTextEdit()
    parent.connect_terminal_out.setObjectName("connectTerminalOut")
    parent.connect_terminal_out.setReadOnly(True)
    parent.connect_terminal_out.setMaximumBlockCount(CONNECT_TERMINAL_MAX_BLOCKS)
    parent.connect_terminal_out.setMinimumHeight(48)
    parent.connect_terminal_out.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Expanding,
    )
    parent.connect_terminal_out.setPlaceholderText("Bench pair setup and checks appear here…")
    from ui.fonts import monospace_ui_font

    parent.connect_terminal_out.setFont(monospace_ui_font())
    lay.addWidget(parent.connect_terminal_out, 1)
    row = QtWidgets.QHBoxLayout()
    parent.connect_terminal_input = QtWidgets.QLineEdit()
    parent.connect_terminal_input.setPlaceholderText("$GPGGA,...  Enter sends to COM")
    parent.connect_terminal_input.returnPressed.connect(parent._connect_terminal_send_line)
    parent.btn_connect_terminal_send = QtWidgets.QPushButton("Send→COM")
    parent.btn_connect_terminal_send.setToolTip(
        "Inject one NMEA line to serial (same as Tools → Inject)."
    )
    parent.btn_connect_terminal_send.clicked.connect(parent._connect_terminal_send_line)
    parent.btn_connect_terminal_clear = QtWidgets.QPushButton("Clear")
    parent.btn_connect_terminal_clear.clicked.connect(parent.connect_terminal_out.clear)
    row.addWidget(parent.connect_terminal_input, 1)
    row.addWidget(parent.btn_connect_terminal_send)
    row.addWidget(parent.btn_connect_terminal_clear)
    lay.addLayout(row)
    return body

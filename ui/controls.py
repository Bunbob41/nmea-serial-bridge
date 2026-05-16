"""Shared Qt controls used by every UI variant."""
from __future__ import annotations

from PySide6 import QtWidgets

from bridge_core import (
    DEFAULT_TCP_RECONNECT_S,
    TCP_RECONNECT_MAX_S,
    TCP_RECONNECT_MIN_S,
    UI_VIEW_MAX_BLOCK_COUNT,
)
from nmea_codec import NMEA_SENTENCE_TYPES


def wire_connection_controls(win: QtWidgets.QWidget) -> None:
    """Connect signals shared by all layouts (after controls exist on win)."""
    win.btn_bench_preset.clicked.connect(win._apply_bench_preset)
    win.btn_production_preset.clicked.connect(win._apply_production_preset)
    win.refresh_btn.clicked.connect(win.refresh_ports)
    win.start_btn.clicked.connect(win.start_bridge)
    win.stop_btn.clicked.connect(win.stop_bridge)
    win.chk_advanced_net.toggled.connect(win._on_advanced_net_toggle)
    for rb in (win.rb_udp_listen, win.rb_udp_remote, win.rb_tcp_server, win.rb_tcp_client):
        rb.toggled.connect(win._mode_toggle)
    win.btn_insert_sample.clicked.connect(win._insert_send_sample)
    win.btn_send_ser.clicked.connect(lambda: win._send_manual("serial"))
    win.btn_send_net.clicked.connect(lambda: win._send_manual("net"))
    win.btn_send_both.clicked.connect(lambda: win._send_manual("both"))
    win.btn_browse.clicked.connect(win._browse_log)
    win.btn_clear_ui.clicked.connect(win.log_view.clear)


def create_connection_controls(parent: QtWidgets.QWidget) -> None:
    """Attach serial + network + path widgets to parent (stored on parent window)."""
    p = parent

    p.btn_bench_preset = QtWidgets.QPushButton("Desk test")
    p.btn_bench_preset.setObjectName("pathBench")
    p.btn_production_preset = QtWidgets.QPushButton("Boat / INS")
    p.btn_production_preset.setObjectName("pathProduction")

    p.com_cb = QtWidgets.QComboBox()
    p.refresh_btn = QtWidgets.QPushButton("Refresh")
    p.baud_edit = QtWidgets.QLineEdit("115200")

    p.udp_host = QtWidgets.QLineEdit("0.0.0.0")
    p.udp_port = QtWidgets.QLineEdit("10110")
    p.chk_advanced_net = QtWidgets.QCheckBox("Advanced (TCP / UDP remote)")

    p.mode_group = QtWidgets.QButtonGroup(parent)
    p.rb_udp_listen = QtWidgets.QRadioButton("UDP listen")
    p.rb_udp_remote = QtWidgets.QRadioButton("UDP remote")
    p.rb_tcp_server = QtWidgets.QRadioButton("TCP server")
    p.rb_tcp_client = QtWidgets.QRadioButton("TCP client")
    p.rb_udp_listen.setChecked(True)
    for rb in (p.rb_udp_listen, p.rb_udp_remote, p.rb_tcp_server, p.rb_tcp_client):
        p.mode_group.addButton(rb)

    p._advanced_net = QtWidgets.QWidget()
    adv = QtWidgets.QVBoxLayout(p._advanced_net)
    p._mode_box = QtWidgets.QGroupBox("Mode")
    mv = QtWidgets.QVBoxLayout(p._mode_box)
    mv.setContentsMargins(8, 8, 8, 8)
    mv.setSpacing(4)
    mv.addWidget(p.rb_udp_listen)
    mv.addWidget(p.rb_udp_remote)
    mv.addWidget(p.rb_tcp_server)
    mv.addWidget(p.rb_tcp_client)
    adv.addWidget(p._mode_box)

    p._udp_box = QtWidgets.QGroupBox("UDP remote")
    uf = QtWidgets.QFormLayout(p._udp_box)
    p.remote_host = QtWidgets.QLineEdit("192.168.1.100")
    p.remote_port = QtWidgets.QLineEdit("10110")
    uf.addRow("Host:", p.remote_host)
    uf.addRow("Port:", p.remote_port)
    adv.addWidget(p._udp_box)

    p._tcp_srv_box = QtWidgets.QGroupBox("TCP server")
    tsf = QtWidgets.QFormLayout(p._tcp_srv_box)
    p.tcp_srv_host = QtWidgets.QLineEdit("0.0.0.0")
    p.tcp_srv_port = QtWidgets.QLineEdit("4001")
    tsf.addRow("Bind:", p.tcp_srv_host)
    tsf.addRow("Port:", p.tcp_srv_port)
    adv.addWidget(p._tcp_srv_box)

    p._tcp_cli_box = QtWidgets.QGroupBox("TCP client")
    tcf = QtWidgets.QFormLayout(p._tcp_cli_box)
    p.tcp_cli_host = QtWidgets.QLineEdit("127.0.0.1")
    p.tcp_cli_port = QtWidgets.QLineEdit("4001")
    tcf.addRow("Host:", p.tcp_cli_host)
    tcf.addRow("Port:", p.tcp_cli_port)
    adv.addWidget(p._tcp_cli_box)

    p.tcp_reconnect_spin = QtWidgets.QDoubleSpinBox()
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

    p.start_btn = QtWidgets.QPushButton("Start")
    p.start_btn.setObjectName("btnStart")
    p.stop_btn = QtWidgets.QPushButton("Stop")
    p.stop_btn.setObjectName("btnStop")
    p.stop_btn.setEnabled(False)

    p._connection_widgets = [
        p.btn_bench_preset,
        p.btn_production_preset,
        p.com_cb,
        p.refresh_btn,
        p.baud_edit,
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
    ]


def create_nmea_controls(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tool_tabs import _scrollable

    w = QtWidgets.QWidget()
    w.setObjectName("toolTabScrollHost")
    v = QtWidgets.QVBoxLayout(w)
    v.setContentsMargins(14, 14, 14, 14)
    parent.nmea_mode_group = QtWidgets.QButtonGroup(parent)
    parent.rb_nmea_passthrough = QtWidgets.QRadioButton("Passthrough (recommended)")
    parent.rb_nmea_strict = QtWidgets.QRadioButton("Strict + sentence filter")
    parent.rb_nmea_passthrough.setChecked(True)
    parent.nmea_mode_group.addButton(parent.rb_nmea_passthrough)
    parent.nmea_mode_group.addButton(parent.rb_nmea_strict)
    v.addWidget(parent.rb_nmea_passthrough)
    v.addWidget(parent.rb_nmea_strict)
    types_box = QtWidgets.QGroupBox("Strict: allowed types")
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
        *parent._nmea_type_checks.values(),
    ]
    return _scrollable(w)


def create_send_controls(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tool_tabs import build_send_tab

    return build_send_tab(parent)


def create_diagnostics_controls(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tool_tabs import build_diagnostics_tab

    return build_diagnostics_tab(parent)


def create_log_panel(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    panel = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 0)
    hdr = QtWidgets.QHBoxLayout()
    parent.chk_show_log = QtWidgets.QCheckBox("Show log")
    parent.chk_verbose_log = QtWidgets.QCheckBox("Verbose sentences")
    parent.chk_show_log.setChecked(True)
    parent.chk_verbose_log.setChecked(True)
    parent.btn_clear_log = QtWidgets.QPushButton("Clear")
    hdr.addWidget(parent.chk_show_log)
    hdr.addWidget(parent.chk_verbose_log)
    hdr.addStretch(1)
    hdr.addWidget(parent.btn_clear_log)
    lay.addLayout(hdr)
    parent.log_view = QtWidgets.QPlainTextEdit()
    parent.log_view.setObjectName("logView")
    parent.log_view.setReadOnly(True)
    parent.log_view.setMaximumBlockCount(UI_VIEW_MAX_BLOCK_COUNT)
    lay.addWidget(parent.log_view, 1)
    parent.chk_show_log.toggled.connect(parent._toggle_log_panel)
    parent.btn_clear_log.clicked.connect(parent.log_view.clear)
    return panel

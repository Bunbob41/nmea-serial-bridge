"""Send and Diagnostics tab content (shared by all UI variants)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from bridge_core import file_log_retention_hint
from nmea_static_sample import SAMPLE_ALT_M, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, build_gga


def _scrollable(inner: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
    """Scroll wrapper that inherits app theme (avoids Windows default white viewport)."""
    inner.setObjectName("toolTabScrollHost")
    inner.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

    scroll = QtWidgets.QScrollArea()
    scroll.setObjectName("toolTabScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFocusPolicy(QtCore.Qt.FocusPolicy.WheelFocus)
    scroll.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    scroll.viewport().setObjectName("toolTabScrollViewport")
    scroll.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    scroll.setWidget(inner)
    return scroll


def _add_collapsible_card(
    host_layout: QtWidgets.QVBoxLayout,
    title: str,
    *,
    start_open: bool = False,
    on_toggled=None,
) -> QtWidgets.QVBoxLayout:
    """Create an iOS-style collapsible card and return its body layout."""
    card = QtWidgets.QFrame()
    card.setObjectName("iosCard")
    outer = QtWidgets.QVBoxLayout(card)
    outer.setContentsMargins(8, 8, 8, 8)
    outer.setSpacing(6)

    toggle = QtWidgets.QToolButton()
    toggle.setObjectName("iosCardToggle")
    toggle.setText(title)
    toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    toggle.setCheckable(True)
    toggle.setChecked(start_open)

    body = QtWidgets.QWidget()
    body.setObjectName("iosCardBody")
    body_lay = QtWidgets.QVBoxLayout(body)
    body_lay.setContentsMargins(4, 2, 4, 4)
    body_lay.setSpacing(8)

    def _on_toggle(on: bool) -> None:
        toggle.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if on else QtCore.Qt.ArrowType.RightArrow
        )
        if on:
            outer.setContentsMargins(8, 8, 8, 8)
            card.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
            card.setMaximumHeight(16777215)
            body.setMinimumHeight(0)
            body.setMaximumHeight(16777215)
            body.setVisible(True)
        else:
            outer.setContentsMargins(8, 4, 8, 4)
            card.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            strip_h = toggle.sizeHint().height() + 8
            card.setMaximumHeight(strip_h)
            body.setMaximumHeight(0)
            body.setVisible(False)
        card.updateGeometry()
        if callable(on_toggled):
            on_toggled(on)

    toggle.toggled.connect(_on_toggle)
    _on_toggle(start_open)
    outer.addWidget(toggle)
    outer.addWidget(body)
    host_layout.addWidget(card)
    return body_lay


def build_send_tab(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Manual NMEA inject tab."""
    host = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(14, 14, 14, 14)
    lay.setSpacing(10)

    hint = QtWidgets.QLabel(
        "Inject test sentences while the bridge is Running. "
        "Use Send → serial for bench (COM7 → com0com → watch COM12). "
        "Gray placeholder text is not sent."
    )
    hint.setWordWrap(True)
    hint.setObjectName("tabHint")
    lay.addWidget(hint)

    parent.send_edit = QtWidgets.QPlainTextEdit()
    parent.send_edit.setObjectName("sendEdit")
    parent.send_edit.setPlaceholderText("$GPGGA,...  one or more lines")
    parent.send_edit.setMinimumHeight(120)
    sample = build_gga(datetime.now(timezone.utc), SAMPLE_LAT_DEG, SAMPLE_LON_DEG, SAMPLE_ALT_M)
    parent.send_edit.setPlainText(sample)
    lay.addWidget(parent.send_edit, 1)

    parent.btn_insert_sample = QtWidgets.QPushButton("Insert sample GGA")
    lay.addWidget(parent.btn_insert_sample)

    row = QtWidgets.QHBoxLayout()
    row.setSpacing(8)
    parent.btn_send_ser = QtWidgets.QPushButton("Send → serial")
    parent.btn_send_net = QtWidgets.QPushButton("Send → network")
    parent.btn_send_both = QtWidgets.QPushButton("Send → both")
    parent.btn_send_ser.setMinimumWidth(110)
    parent.btn_send_net.setMinimumWidth(110)
    parent.btn_send_both.setMinimumWidth(110)
    row.addWidget(parent.btn_send_ser)
    row.addWidget(parent.btn_send_net)
    row.addWidget(parent.btn_send_both)
    row.addStretch(1)
    lay.addLayout(row)

    note = QtWidgets.QLabel(
        "If nothing moves: confirm the status bar shows COM open and the network line matches your mode. "
        "While running, the right end shows sentence rates (↓ ↑ Hz), plain-language transport health "
        "(no fake 0/0 pairs), and session totals — enable verbose log to see each line."
    )
    note.setWordWrap(True)
    note.setObjectName("tabNote")
    lay.addWidget(note)

    return _scrollable(host)


def build_diagnostics_tab(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """File log + on-screen log options."""
    host = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(14, 14, 14, 14)
    lay.setSpacing(12)

    card_states = {}
    if hasattr(parent, "_load_diag_card_states"):
        try:
            loaded = parent._load_diag_card_states()
            if isinstance(loaded, dict):
                card_states = loaded
        except Exception:
            card_states = {}

    def _card_open(key: str, default: bool) -> bool:
        return bool(card_states.get(key, default))

    def _persist_card(key: str, on: bool) -> None:
        if hasattr(parent, "_save_diag_card_state"):
            try:
                parent._save_diag_card_state(key, on)
            except Exception:
                pass

    hint = QtWidgets.QLabel(
        "Optional rotating file log for survey records. "
        "The main live log (Log tab in Standard, or above the strip in Field) is separate — "
        "use On-screen log below to clear it."
    )
    hint.setWordWrap(True)
    hint.setObjectName("tabHint")
    hint_row = QtWidgets.QHBoxLayout()
    hint_row.addWidget(hint, 1)
    parent.btn_diag_reorder_cards = QtWidgets.QPushButton("Reorder cards…")
    parent.btn_diag_reorder_cards.setToolTip(
        "Drag diagnostics cards into your preferred order."
    )
    parent.btn_diag_reorder_cards.clicked.connect(parent._open_diag_card_order_manager)
    hint_row.addWidget(parent.btn_diag_reorder_cards, 0)
    lay.addLayout(hint_row)

    card_widgets: dict[str, QtWidgets.QWidget] = {}

    def _register_card(key: str) -> None:
        item = lay.itemAt(lay.count() - 1)
        widget = item.widget() if item is not None else None
        if widget is not None:
            widget.setProperty("diagCardKey", key)
            card_widgets[key] = widget

    quick = _add_collapsible_card(
        lay,
        "Quick UI switch",
        start_open=_card_open("quick_ui_switch", False),
        on_toggled=lambda on: _persist_card("quick_ui_switch", on),
    )
    _register_card("quick_ui_switch")
    quick_note = QtWidgets.QLabel(
        "Jump between layouts quickly. Choice is remembered for next launch."
    )
    quick_note.setWordWrap(True)
    quick_note.setObjectName("tabHint")
    quick.addWidget(quick_note)
    ui_grid = QtWidgets.QGridLayout()
    ui_grid.setHorizontalSpacing(8)
    ui_grid.setVerticalSpacing(6)
    parent.btn_ui_standard = QtWidgets.QPushButton("Open Standard UI")
    parent.btn_ui_standard.setToolTip("Switch to the Standard workspace layout.")
    parent.btn_ui_field = QtWidgets.QPushButton("Open Field UI")
    parent.btn_ui_field.setToolTip("Switch to the Field layout (large log, compact connect).")
    for b in (parent.btn_ui_standard, parent.btn_ui_field):
        b.setMinimumHeight(30)
        b.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
    ui_grid.addWidget(parent.btn_ui_standard, 0, 0)
    ui_grid.addWidget(parent.btn_ui_field, 0, 1)
    ui_grid.setColumnStretch(0, 1)
    ui_grid.setColumnStretch(1, 1)
    quick.addLayout(ui_grid)

    fv = _add_collapsible_card(
        lay,
        "Rotating file log",
        start_open=_card_open("file_log", False),
        on_toggled=lambda on: _persist_card("file_log", on),
    )
    _register_card("file_log")
    parent.chk_file_log = QtWidgets.QCheckBox("Write NMEA traffic to file while bridge runs")
    fv.addWidget(parent.chk_file_log)
    path_row = QtWidgets.QHBoxLayout()
    parent.file_log_path = QtWidgets.QLineEdit(str(Path.home() / "bridge_survey.log"))
    parent.file_log_path.setPlaceholderText("Path to .log file")
    parent.btn_browse = QtWidgets.QPushButton("Browse…")
    path_row.addWidget(parent.file_log_path, 1)
    path_row.addWidget(parent.btn_browse)
    fv.addLayout(path_row)
    size_row = QtWidgets.QHBoxLayout()
    size_row.addWidget(QtWidgets.QLabel("Per-file size:"))
    parent.cmb_file_log_mb = QtWidgets.QComboBox()
    for mb in (10, 25, 50, 100):
        parent.cmb_file_log_mb.addItem(f"{mb} MB", mb)
    parent.cmb_file_log_mb.setToolTip(
        "Rotating log size before rollover. Duration depends on sentence rate and payload size."
    )
    size_row.addWidget(parent.cmb_file_log_mb, 1)
    size_row.addWidget(QtWidgets.QLabel("Backups:"))
    parent.cmb_file_log_backups = QtWidgets.QComboBox()
    for n in (3, 5, 10):
        parent.cmb_file_log_backups.addItem(str(n), n)
    size_row.addWidget(parent.cmb_file_log_backups, 0)
    fv.addLayout(size_row)
    parent.lbl_file_log_retention = QtWidgets.QLabel(file_log_retention_hint(10, 5))
    parent.lbl_file_log_retention.setWordWrap(True)
    parent.lbl_file_log_retention.setObjectName("tabNote")
    fv.addWidget(parent.lbl_file_log_retention)
    if hasattr(parent, "_refresh_file_log_retention_hint"):
        parent.cmb_file_log_mb.currentIndexChanged.connect(parent._refresh_file_log_retention_hint)
        parent.cmb_file_log_backups.currentIndexChanged.connect(parent._refresh_file_log_retention_hint)
    file_note = QtWidgets.QLabel(
        "Format: PC time | GPS UTC | direction | sentence. "
        "Use size/backups for POSPAC/post-processing retention on this PC."
    )
    file_note.setWordWrap(True)
    file_note.setObjectName("tabNote")
    fv.addWidget(file_note)

    sv = _add_collapsible_card(
        lay,
        "On-screen log",
        start_open=_card_open("screen_log", False),
        on_toggled=lambda on: _persist_card("screen_log", on),
    )
    _register_card("screen_log")
    parent.btn_clear_ui = QtWidgets.QPushButton("Clear live log panel")
    parent.btn_clear_ui.setToolTip("Clears the main log view — does not delete the file above.")
    sv.addWidget(parent.btn_clear_ui)

    qv = _add_collapsible_card(
        lay,
        "Traffic & data quality (honest counters)",
        start_open=_card_open("traffic_quality", False),
        on_toggled=lambda on: _persist_card("traffic_quality", on),
    )
    _register_card("traffic_quality")
    qa = QtWidgets.QLabel(
        "Bottom status bar while Running:\n\n"
        "• ↓ / ↑ Hz — Rolling ~1 s rate of complete NMEA sentences: remote (UDP/TCP) toward COM, "
        "and COM toward the network.\n"
        "• Send→COM …/s — Appears only while the Send tab is injecting fast enough to register on that window.\n"
        "• transport OK — No drops or rejects; shallow queue depth (a few chunks) while data moves is normal. "
        "Backlog is reported around depth 12+ per side (same idea as the capacity probe).\n"
        "• session: … — Lifetime sentence counts this session (remote →COM and COM→net).\n"
        "• GNSS — From the latest GGA: fix type (RTK fixed best), satellite count "
        f"(≥5 mission min, {7}+ preferred with low HDOP), HDOP (ideal <2.5, acceptable <4; POSPac Ch.16).\n"
        "• GNSS status chip — Same assessment on the status bar; stale if no GGA for ~3 s.\n"
        "• Live log — Repeating “Serial … timed out (open/write).” lines are collapsed to one per ~2.5 s "
        "(same as the bridge; mirrored Diagnostics output uses the same path when “Mirror” is on).\n\n"
        "Hover the status bar any time for the same legend."
    )
    qa.setWordWrap(True)
    qa.setObjectName("tabNote")
    qa.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    qv.addWidget(qa)

    bv = _add_collapsible_card(
        lay,
        "Automated checks (runs on this PC)",
        start_open=_card_open("automated_checks", False),
        on_toggled=lambda on: _persist_card("automated_checks", on),
    )
    _register_card("automated_checks")
    intro = QtWidgets.QLabel(
        "Runs the same Python helpers as the command line. Output streams below; the window stays responsive. "
        "Start the bridge first for the UDP burst if you want to see traffic on the wire."
    )
    intro.setWordWrap(True)
    intro.setObjectName("tabNote")
    bv.addWidget(intro)

    btn_row1 = QtWidgets.QHBoxLayout()
    parent.btn_bench_pair_setup = QtWidgets.QPushButton("Bench pair setup…")
    parent.btn_bench_pair_setup.setToolTip(
        "Opens docs/OPERATOR_GUIDE.md (bench §5) and runs com_free then check_setup — "
        "same checks as preflight_bench.bat. Install com0com from the guide first."
    )
    parent.btn_bench_pair_setup.clicked.connect(parent._open_bench_pair_setup)
    btn_row1.addWidget(parent.btn_bench_pair_setup)
    parent.btn_diag_verify = QtWidgets.QPushButton("Full verify")
    parent.btn_diag_verify.setObjectName("btnDiagVerify")
    parent.btn_diag_verify.setToolTip(
        "Runs verify_all.py (~15 s): unit tests, COM check, GUI smoke, headless bridge, stress. "
        "If the bridge was started with pythonw.exe, child steps use python.exe so unittest is reliable."
    )
    parent.btn_diag_setup = QtWidgets.QPushButton("Bench checklist")
    parent.btn_diag_setup.setToolTip(
        "Runs check_setup.py using the first bench-style named preset in path_presets.json."
    )
    parent.btn_diag_setup_prod = QtWidgets.QPushButton("Boat checklist")
    parent.btn_diag_setup_prod.setObjectName("btnDiagBoatChecklist")
    parent.btn_diag_setup_prod.setToolTip(
        "Runs check_setup.py --production using the first boat-style named preset."
    )
    for b in (
        parent.btn_diag_verify,
        parent.btn_diag_setup,
        parent.btn_diag_setup_prod,
    ):
        btn_row1.addWidget(b)
    btn_row1.addStretch(1)
    bv.addLayout(btn_row1)

    btn_row2 = QtWidgets.QHBoxLayout()
    parent.btn_diag_udp = QtWidgets.QPushButton("UDP sample burst (2.5 s)")
    parent.btn_diag_udp.setObjectName("btnDiagUdpBurst")
    parent.btn_diag_udp.setToolTip(
        "Runs nmea_static_sample.py toward the bench preset UDP target. "
        "Bridge should be Running (UDP listen) to see lines in the log."
    )
    parent.btn_diag_tcp_stress = QtWidgets.QPushButton("TCP stress (LA->Sac)")
    parent.btn_diag_tcp_demo = QtWidgets.QPushButton("TCP demo (~4 min)")
    parent.btn_diag_tcp_demo.setToolTip(
        "Presenter TCP feed: fast LA->Sac legs (~100 m/s) for visible chart motion; "
        "auto-stops after ~4 minutes. Bridge TCP server must be Running."
    )
    parent.btn_diag_tcp_stress.setToolTip(
        "Runs bench_tcp_stress.py: 5 NMEA sentences @ 5 Hz toward the TCP server bind port "
        "(127.0.0.1 when bind is 0.0.0.0). Bridge must be Running in TCP server mode. "
        "Reconnects automatically; each session restarts at Los Angeles (~5 m/s along route). "
        "Drains TCP replies so COM->net queues do not fill (avoids Transport Warn). Use Stop to end."
    )
    parent.btn_diag_stop = QtWidgets.QPushButton("Stop")
    parent.btn_diag_stop.setEnabled(False)
    parent.btn_diag_stop.setToolTip("Kill the running helper process.")
    parent.btn_diag_clear = QtWidgets.QPushButton("Clear output")
    btn_row2.addWidget(parent.btn_diag_udp)
    btn_row2.addWidget(parent.btn_diag_tcp_stress)
    btn_row2.addWidget(parent.btn_diag_tcp_demo)
    btn_row2.addWidget(parent.btn_diag_stop)
    btn_row2.addWidget(parent.btn_diag_clear)
    btn_row2.addStretch(1)
    bv.addLayout(btn_row2)

    cap_row = QtWidgets.QHBoxLayout()
    cap_row.addWidget(QtWidgets.QLabel("Capacity probe"))
    parent.cmb_diag_capacity = QtWidgets.QComboBox()
    parent.cmb_diag_capacity.addItem(
        "Quick: 5→20 Hz (8 lines, 3 s)",
        {"name": "quick", "start": 5, "stop": 20, "step": 5, "sent": 8, "sec": 3.0},
    )
    parent.cmb_diag_capacity.addItem(
        "Field: 10→30 Hz (10 lines, 6 s)",
        {"name": "field", "start": 10, "stop": 30, "step": 5, "sent": 10, "sec": 6.0},
    )
    parent.cmb_diag_capacity.addItem(
        "Stress: 10→45 Hz (10 lines, 6 s)",
        {"name": "stress", "start": 10, "stop": 45, "step": 5, "sent": 10, "sec": 6.0},
    )
    parent.cmb_diag_capacity.addItem(
        "Safe overload: 20→70 Hz (12 lines, 3 s)",
        {"name": "overload", "start": 20, "stop": 70, "step": 5, "sent": 12, "sec": 3.0},
    )
    parent.chk_diag_capacity_strict = QtWidgets.QCheckBox("Strict parser")
    parent.btn_diag_capacity = QtWidgets.QPushButton("Run capacity probe")
    parent.btn_diag_capacity.setToolTip(
        "Runs bench_capacity_probe.py with the selected ramp profile "
        "(bench preset COM/baud/UDP; stop bridge first)."
    )
    cap_row.addWidget(parent.cmb_diag_capacity, 1)
    cap_row.addWidget(parent.chk_diag_capacity_strict)
    cap_row.addWidget(parent.btn_diag_capacity)
    cap_row.addStretch(1)
    bv.addLayout(cap_row)

    parent.chk_diag_mirror_log = QtWidgets.QCheckBox("Mirror output lines to the main live log")
    parent.chk_diag_mirror_log.setToolTip("When checked, each non-empty output line is also appended to the big log panel.")
    bv.addWidget(parent.chk_diag_mirror_log)

    parent.diag_status_label = QtWidgets.QLabel("Idle — pick a check above.")
    parent.diag_status_label.setWordWrap(True)
    parent.diag_status_label.setObjectName("tabHint")
    bv.addWidget(parent.diag_status_label)

    parent.diag_output = QtWidgets.QPlainTextEdit()
    parent.diag_output.setReadOnly(True)
    parent.diag_output.setObjectName("diagOutput")
    parent.diag_output.setMinimumHeight(72)
    parent.diag_output.setMaximumHeight(120)
    parent.diag_output.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    parent.diag_output.setMaximumBlockCount(12_000)
    mono = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
    parent.diag_output.setFont(mono)
    bv.addWidget(parent.diag_output)

    parent._diag_run_buttons = [
        parent.btn_diag_verify,
        parent.btn_diag_setup,
        parent.btn_diag_setup_prod,
        parent.btn_diag_udp,
        parent.btn_diag_tcp_stress,
        parent.btn_diag_tcp_demo,
        parent.btn_diag_capacity,
    ]
    parent.btn_diag_verify.clicked.connect(parent._diag_run_verify_all)
    parent.btn_diag_setup.clicked.connect(parent._diag_run_check_setup)
    parent.btn_diag_setup_prod.clicked.connect(parent._diag_run_check_setup_production)
    parent.btn_diag_udp.clicked.connect(parent._diag_run_udp_sample)
    parent.btn_diag_tcp_stress.clicked.connect(parent._diag_run_tcp_stress)
    parent.btn_diag_tcp_demo.clicked.connect(parent._diag_run_tcp_demo)
    parent.btn_diag_capacity.clicked.connect(parent._diag_run_capacity_probe)
    parent.btn_diag_stop.clicked.connect(parent._diag_stop)
    parent.btn_diag_clear.clicked.connect(parent.diag_output.clear)
    parent.btn_ui_standard.clicked.connect(lambda: parent._switch_ui_layout("standard"))
    parent.btn_ui_field.clicked.connect(lambda: parent._switch_ui_layout("field"))
    parent._diag_card_widgets = card_widgets
    parent._diag_cards_layout = lay
    lay.addStretch(1)
    if hasattr(parent, "_apply_diag_card_order"):
        parent._apply_diag_card_order()

    return _scrollable(host)

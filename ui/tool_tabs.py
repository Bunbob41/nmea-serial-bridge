"""Send and Diagnostics tab content (shared by all UI variants)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from nmea_static_edh import EDH_ALT_M, EDH_LAT_DEG, EDH_LON_DEG, build_gga


def _scrollable(inner: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
    """Scroll wrapper that inherits app theme (avoids Windows default white viewport)."""
    inner.setObjectName("toolTabScrollHost")
    inner.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

    scroll = QtWidgets.QScrollArea()
    scroll.setObjectName("toolTabScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    scroll.viewport().setObjectName("toolTabScrollViewport")
    scroll.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    scroll.setWidget(inner)
    return scroll


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
    sample = build_gga(datetime.now(timezone.utc), EDH_LAT_DEG, EDH_LON_DEG, EDH_ALT_M)
    parent.send_edit.setPlainText(sample)
    lay.addWidget(parent.send_edit, 1)

    parent.btn_insert_sample = QtWidgets.QPushButton("Insert EDH sample (GGA + RMC)")
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
        "If nothing moves: confirm status bar shows COM open and UDP listening. "
        "While running, ↓ / inj↓ / ↑ Hz on the bottom bar are sentence rates (rolling 1 s) — "
        "enable verbose log to see each line."
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

    hint = QtWidgets.QLabel(
        "Optional rotating file log for survey records. "
        "The live log panel (right side or top) is separate — use controls below to clear it."
    )
    hint.setWordWrap(True)
    hint.setObjectName("tabHint")
    lay.addWidget(hint)

    file_box = QtWidgets.QGroupBox("Rotating file log")
    fv = QtWidgets.QVBoxLayout(file_box)
    parent.chk_file_log = QtWidgets.QCheckBox("Write NMEA traffic to file while bridge runs")
    fv.addWidget(parent.chk_file_log)
    path_row = QtWidgets.QHBoxLayout()
    parent.file_log_path = QtWidgets.QLineEdit(str(Path.home() / "bridge_survey.log"))
    parent.file_log_path.setPlaceholderText("Path to .log file")
    parent.btn_browse = QtWidgets.QPushButton("Browse…")
    path_row.addWidget(parent.file_log_path, 1)
    path_row.addWidget(parent.btn_browse)
    fv.addLayout(path_row)
    file_note = QtWidgets.QLabel(
        "Format: PC time | GPS UTC | direction | sentence. "
        "10 MB max per file, 5 backups."
    )
    file_note.setWordWrap(True)
    file_note.setObjectName("tabNote")
    fv.addWidget(file_note)
    lay.addWidget(file_box)

    screen_box = QtWidgets.QGroupBox("On-screen log")
    sv = QtWidgets.QVBoxLayout(screen_box)
    parent.btn_clear_ui = QtWidgets.QPushButton("Clear live log panel")
    parent.btn_clear_ui.setToolTip("Clears the main log view — does not delete the file above.")
    sv.addWidget(parent.btn_clear_ui)
    lay.addWidget(screen_box)

    qa_box = QtWidgets.QGroupBox("Traffic & data quality (honest counters)")
    qv = QtWidgets.QVBoxLayout(qa_box)
    qa = QtWidgets.QLabel(
        "Bottom status bar while Running:\n\n"
        "• ↓ Hz — Complete NMEA sentences per second from UDP/TCP toward COM (simulator/INS). "
        "Rolling 1 second — compare to your source (e.g. 1 Hz vs 5 Hz).\n"
        "• inj↓ Hz — Send-tab inject toward COM only (separate from ↓).\n"
        "• ↑ Hz — Sentences per second from COM back toward the network.\n"
        "• dr — Drops when internal queues are full (overload); should stay 0 in normal use.\n"
        "• rj — Assembler / Strict-mode rejects. In Passthrough, rj usually stays 0 unless data is corrupt.\n"
        "• Q — Pending chunks in queues before write.\n"
        "• k↓ / ↑ — Lifetime sentence counts this session (UDP/TCP→COM vs COM→net).\n\n"
        "Hover the status bar any time for the same legend."
    )
    qa.setWordWrap(True)
    qa.setObjectName("tabNote")
    qa.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    qv.addWidget(qa)
    lay.addWidget(qa_box)

    bench_box = QtWidgets.QGroupBox("Quick checks")
    bv = QtWidgets.QVBoxLayout(bench_box)
    tips = QtWidgets.QLabel(
        "• Bench: python com_free.py  then  python check_setup.py\n"
        "• Full auto: python verify_all.py\n"
        "• Traffic test: python nmea_static_edh.py  (bridge must be Running)"
    )
    tips.setWordWrap(True)
    tips.setObjectName("tabNote")
    tips.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    bv.addWidget(tips)
    lay.addWidget(bench_box)

    lay.addStretch(1)
    return _scrollable(host)

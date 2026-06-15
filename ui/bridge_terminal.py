"""Bridge Terminal — live wire-tap panel for the Modern UI.

Shows every assembled NMEA sentence (or raw binary block) flowing through the
bridge with timestamp, direction, and NMEA syntax colouring.  Filters, hex
toggle, pause, and save are all non-blocking and purely UI-side.

Wire-tap data is fed from bridge_core via BridgeLogicMixin._on_bridge_wire_tap,
which calls BridgeTerminalPanel.feed() through a QTimer.singleShot so the
asyncio bridge thread never touches Qt directly.

Directions emitted by bridge_core:
    "net→com"   — assembled sentence forwarded to the serial port
    "com→net"   — assembled sentence forwarded to the network
    "reject"    — sentence rejected by the NMEA filter (shown in amber)
"""
from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

# ── palette (matches Modern fixed theme) ─────────────────────────────────────
_BG            = "#050a12"
_TEXT          = "#e2f0ff"
_MUTED         = "#64748b"
_ACCENT_BLUE   = "#38bdf8"
_ACCENT_GREEN  = "#34d399"
_ACCENT_AMBER  = "#fbbf24"
_ACCENT_RED    = "#f87171"
_SURFACE       = "#111827"
_BORDER        = "#334155"

# Direction label colours
_DIR_COLOURS = {
    "net→com": _ACCENT_BLUE,
    "com→net": _ACCENT_GREEN,
    "reject":  _ACCENT_AMBER,
}

_MAX_LINES = 12_000          # QPlainTextEdit block cap
_FLUSH_INTERVAL_MS = 40      # batch-write timer period
_SENTENCE_RE = re.compile(
    rb"\$([A-Z]{2})([A-Z]{3})",   # talker + sentence type
)
_HEX_COLS = 16               # bytes per hex row


def _ts() -> str:
    """HH:MM:SS.mmm wall-clock timestamp."""
    t = time.time()
    dt = datetime.fromtimestamp(t)
    return dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


def _sentence_type(data: bytes) -> str:
    """Extract 'GGA', 'RMC', … or '' for raw/unknown."""
    m = _SENTENCE_RE.search(data)
    return m.group(2).decode("ascii", errors="replace") if m else ""


def _hex_format(data: bytes) -> str:
    """Multi-line hex dump with printable ASCII side-car."""
    lines: list[str] = []
    for i in range(0, len(data), _HEX_COLS):
        chunk = data[i : i + _HEX_COLS]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        asc_part = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        lines.append(f"  {hex_part:<{_HEX_COLS * 3}}  {asc_part}")
    return "\n".join(lines)


# ── NMEA syntax highlighter ───────────────────────────────────────────────────

class _NmeaHighlighter(QtGui.QSyntaxHighlighter):
    """Colour NMEA sentences inside QPlainTextEdit.

    Pattern per text line:
      HH:MM:SS.mmm  DIR_LABEL  $GPGGA,...*checksum
      ^timestamp^   ^dir^      ^sentence^
    """

    def __init__(self, doc: QtGui.QTextDocument) -> None:
        super().__init__(doc)
        def _fmt(color: str, bold: bool = False) -> QtGui.QTextCharFormat:
            f = QtGui.QTextCharFormat()
            f.setForeground(QtGui.QColor(color))
            if bold:
                f.setFontWeight(QtGui.QFont.Weight.Bold)
            return f

        self._f_ts        = _fmt(_MUTED)
        self._f_net_com   = _fmt(_ACCENT_BLUE,  bold=True)
        self._f_com_net   = _fmt(_ACCENT_GREEN, bold=True)
        self._f_reject    = _fmt(_ACCENT_AMBER, bold=True)
        self._f_talker    = _fmt(_ACCENT_BLUE)
        self._f_type      = _fmt(_TEXT, bold=True)
        self._f_field     = _fmt(_TEXT)
        self._f_checksum  = _fmt(_MUTED)
        self._f_hex_byte  = _fmt(_ACCENT_BLUE)
        self._f_raw_label = _fmt(_ACCENT_AMBER, bold=True)

        # pre-compiled patterns
        self._re_ts    = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}")
        self._re_dir   = re.compile(r"\b(NET→COM|COM→NET|REJECT|RAW)\b")
        self._re_start = re.compile(r"\$([A-Z]{2})([A-Z]{3})")
        self._re_cksum = re.compile(r"\*[0-9A-Fa-f]{2}")
        self._re_hex   = re.compile(r"\b[0-9a-f]{2}\b")

    def highlightBlock(self, text: str) -> None:
        # timestamp
        m = self._re_ts.match(text)
        if m:
            self.setFormat(0, m.end(), self._f_ts)

        # direction label
        for m in self._re_dir.finditer(text):
            label = m.group(0)
            if label == "NET→COM":
                fmt = self._f_net_com
            elif label == "COM→NET":
                fmt = self._f_com_net
            elif label == "REJECT":
                fmt = self._f_reject
            else:
                fmt = self._f_raw_label
            self.setFormat(m.start(), m.end() - m.start(), fmt)

        # NMEA sentence body
        m = self._re_start.search(text)
        if m:
            # talker
            self.setFormat(m.start() + 1, 2, self._f_talker)
            # sentence type
            self.setFormat(m.start() + 3, 3, self._f_type)

        # checksum
        for m in self._re_cksum.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._f_checksum)

        # hex bytes (lines starting with two spaces — hex dump rows)
        stripped = text.lstrip()
        if text.startswith("  ") and not stripped.startswith("$"):
            for m in self._re_hex.finditer(text):
                self.setFormat(m.start(), 2, self._f_hex_byte)


# ── Main panel ────────────────────────────────────────────────────────────────

class BridgeTerminalPanel(QtWidgets.QWidget):
    """Live wire-tap view of bridge data flow.

    Thread-safety: feed() may be called from the bridge callback thread.
    All Qt mutations are deferred to the GUI thread via QMetaObject.invokeMethod.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("bridgeTerminalPanel")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        self._paused = False
        self._hex_mode = False
        self._dir_filter: Optional[str] = None    # None = all; "net→com"/"com→net"/"reject"
        self._type_filter: Optional[str] = None   # None = all; "GGA", "RMC", …
        self._seen_types: set[str] = set()
        self._pending: list[str] = []             # batched line strings
        self._is_raw_mode = False

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── toolbar ───────────────────────────────────────────────────────────
        toolbar = QtWidgets.QFrame()
        toolbar.setObjectName("wireTerminalToolbar")
        tb = QtWidgets.QHBoxLayout(toolbar)
        tb.setContentsMargins(10, 6, 10, 6)
        tb.setSpacing(6)

        # direction filter chips
        self._btn_all = self._chip("All",     None,      checked=True)
        self._btn_n2c = self._chip("NET→COM", "net→com")
        self._btn_c2n = self._chip("COM→NET", "com→net")
        self._btn_rej = self._chip("Reject",  "reject")
        tb.addWidget(self._btn_all)
        tb.addWidget(self._btn_n2c)
        tb.addWidget(self._btn_c2n)
        tb.addWidget(self._btn_rej)

        tb.addWidget(_vline())

        # sentence type filter
        type_lbl = QtWidgets.QLabel("Type:")
        type_lbl.setObjectName("wireToolbarLabel")
        self._type_combo = QtWidgets.QComboBox()
        self._type_combo.setObjectName("wireTypeCombo")
        self._type_combo.setFixedWidth(86)
        self._type_combo.addItem("All types", None)
        self._type_combo.setToolTip("Filter by NMEA sentence type (GGA, RMC, …)")
        self._type_combo.currentIndexChanged.connect(self._on_type_filter_changed)
        tb.addWidget(type_lbl)
        tb.addWidget(self._type_combo)

        tb.addWidget(_vline())

        # hex toggle (visible only in RAW mode)
        self._chk_hex = QtWidgets.QCheckBox("Hex")
        self._chk_hex.setObjectName("wireHexCheck")
        self._chk_hex.setToolTip("Show raw bytes as hex dump (RAW mode only)")
        self._chk_hex.setVisible(False)
        self._chk_hex.stateChanged.connect(self._on_hex_toggled)
        tb.addWidget(self._chk_hex)

        tb.addStretch(1)

        # right-side action buttons
        self._btn_pause = QtWidgets.QPushButton("⏸  Pause")
        self._btn_pause.setObjectName("wireActionBtn")
        self._btn_pause.setFixedHeight(26)
        self._btn_pause.setCheckable(True)
        self._btn_pause.setToolTip("Pause/resume the live display (bridge keeps running)")
        self._btn_pause.toggled.connect(self._on_pause_toggled)

        btn_clear = QtWidgets.QPushButton("Clear")
        btn_clear.setObjectName("wireActionBtn")
        btn_clear.setFixedHeight(26)
        btn_clear.setToolTip("Clear the display (no data is lost from the bridge)")
        btn_clear.clicked.connect(self._view.clear if hasattr(self, "_view") else lambda: None)

        self._btn_save = QtWidgets.QPushButton("Save…")
        self._btn_save.setObjectName("wireActionBtn")
        self._btn_save.setFixedHeight(26)
        self._btn_save.setToolTip("Save visible traffic to a .txt file")
        self._btn_save.clicked.connect(self._on_save)

        tb.addWidget(self._btn_pause)
        tb.addWidget(btn_clear)
        tb.addWidget(self._btn_save)

        root.addWidget(toolbar)

        # ── text view ─────────────────────────────────────────────────────────
        self._view = QtWidgets.QPlainTextEdit()
        self._view.setObjectName("wireTerminalView")
        self._view.setReadOnly(True)
        self._view.setMaximumBlockCount(_MAX_LINES)
        self._view.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self._view.setUndoRedoEnabled(False)
        from ui.fonts import monospace_ui_font
        self._view.setFont(monospace_ui_font())
        root.addWidget(self._view, 1)

        # hook up deferred clear now that _view exists
        btn_clear.clicked.disconnect()
        btn_clear.clicked.connect(self._on_clear)

        # NMEA syntax highlighter
        self._highlighter = _NmeaHighlighter(self._view.document())

        # ── idle placeholder ──────────────────────────────────────────────────
        self._view.setPlaceholderText(
            "Bridge traffic will appear here when the bridge is running.\n"
            "Start the bridge to see live NET→COM and COM→NET sentences."
        )

        # ── flush timer ───────────────────────────────────────────────────────
        self._flush_timer = QtCore.QTimer(self)
        self._flush_timer.setInterval(_FLUSH_INTERVAL_MS)
        self._flush_timer.timeout.connect(self._flush)
        self._flush_timer.start()

    # ── chip helper ───────────────────────────────────────────────────────────

    def _chip(
        self, label: str, direction: Optional[str], checked: bool = False
    ) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(label)
        btn.setObjectName("wireDirChip")
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setFixedHeight(24)
        btn.setToolTip(f"Show {label} traffic only" if direction else "Show all traffic")
        btn.clicked.connect(lambda: self._set_dir_filter(direction))
        return btn

    # ── public API ────────────────────────────────────────────────────────────

    def set_raw_mode(self, raw: bool) -> None:
        """Called by the mixin when bridge NMEA mode changes."""
        self._is_raw_mode = raw
        self._chk_hex.setVisible(raw)
        if not raw:
            self._chk_hex.setChecked(False)

    def feed(self, direction: str, data: bytes) -> None:
        """Called from bridge callback thread — deferred to GUI thread."""
        QtCore.QMetaObject.invokeMethod(
            self,
            "_feed_gui",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, direction),
            QtCore.Q_ARG(bytes, data),
        )

    @QtCore.Slot(str, bytes)
    def _feed_gui(self, direction: str, data: bytes) -> None:
        """All display logic runs on the GUI thread."""
        if self._paused:
            return

        # direction filter
        if self._dir_filter is not None and direction != self._dir_filter:
            return

        # sentence type filter and type-combo population
        stype = _sentence_type(data)
        if stype and stype not in self._seen_types:
            self._seen_types.add(stype)
            self._type_combo.addItem(stype, stype)

        if self._type_filter is not None and stype != self._type_filter:
            return

        # format line
        dir_label = {
            "net→com": "NET→COM",
            "com→net": "COM→NET",
            "reject":  "REJECT ",
        }.get(direction, direction.upper())

        if self._hex_mode and self._is_raw_mode:
            body = f"[RAW {len(data)} bytes]\n{_hex_format(data)}"
        else:
            try:
                body = data.decode("utf-8", errors="replace").rstrip("\r\n")
            except Exception:
                body = repr(data)

        line = f"{_ts()}  {dir_label}  {body}"
        self._pending.append(line)

    # ── flush ─────────────────────────────────────────────────────────────────

    def _flush(self) -> None:
        if not self._pending:
            return
        blob = "\n".join(self._pending)
        self._pending.clear()
        at_bottom = self._at_bottom()
        cursor = self._view.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.insertText(("\n" if self._view.document().blockCount() > 1 else "") + blob)
        if at_bottom:
            self._view.verticalScrollBar().setValue(
                self._view.verticalScrollBar().maximum()
            )

    def _at_bottom(self) -> bool:
        bar = self._view.verticalScrollBar()
        return bar.value() >= bar.maximum() - 4

    # ── filter handlers ───────────────────────────────────────────────────────

    def _set_dir_filter(self, direction: Optional[str]) -> None:
        self._dir_filter = direction
        for btn, d in (
            (self._btn_all, None),
            (self._btn_n2c, "net→com"),
            (self._btn_c2n, "com→net"),
            (self._btn_rej, "reject"),
        ):
            btn.setChecked(d == direction)

    def _on_type_filter_changed(self, index: int) -> None:
        self._type_filter = self._type_combo.itemData(index)

    def _on_hex_toggled(self, state: int) -> None:
        self._hex_mode = bool(state)

    def _on_pause_toggled(self, checked: bool) -> None:
        self._paused = checked
        self._btn_pause.setText("▶  Resume" if checked else "⏸  Pause")

    def _on_clear(self) -> None:
        self._view.clear()
        self._pending.clear()
        self._seen_types.clear()
        # preserve "All types" entry
        self._type_combo.blockSignals(True)
        while self._type_combo.count() > 1:
            self._type_combo.removeItem(1)
        self._type_combo.setCurrentIndex(0)
        self._type_combo.blockSignals(False)
        self._type_filter = None

    def _on_save(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save bridge traffic",
            f"bridge_traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text files (*.txt);;All files (*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._view.toPlainText())
            QtWidgets.QMessageBox.information(
                self, "Saved", f"Traffic saved to:\n{path}"
            )
        except OSError as exc:
            QtWidgets.QMessageBox.warning(
                self, "Save failed", f"Could not write file:\n{exc}"
            )


# ── helper ────────────────────────────────────────────────────────────────────

def _vline() -> QtWidgets.QFrame:
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    f.setObjectName("wireToolbarSep")
    return f


def create_bridge_terminal_tab(parent: QtWidgets.QWidget) -> BridgeTerminalPanel:
    """Build and return a BridgeTerminalPanel; stores reference on parent."""
    panel = BridgeTerminalPanel()
    parent.bridge_terminal = panel  # type: ignore[attr-defined]
    return panel

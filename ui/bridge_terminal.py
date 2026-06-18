"""Bridge Terminal — live wire-tap panel for the Modern UI.

Shows every assembled NMEA sentence (or raw binary block) flowing through the
bridge with timestamp, direction, and NMEA syntax colouring.  Filters, hex
toggle, pause, and save are all non-blocking and purely UI-side.

Wire-tap data is fed from bridge_core via BridgeLogicMixin._on_bridge_wire_tap,
which calls BridgeTerminalPanel.feed(); a Qt Signal queues delivery to the GUI
thread (QMetaObject.invokeMethod with bytes is unreliable in PySide6).

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
        self._f_event     = _fmt(_MUTED, bold=True)

        # pre-compiled patterns
        self._re_ts    = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}")
        self._re_dir   = re.compile(r"\b(NET→COM|COM→NET|REJECT|RAW|EVENT)\b")
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
            elif label == "EVENT":
                fmt = self._f_event
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
    All Qt mutations are queued to the GUI thread via _wire_feed Signal.
    """

    _wire_feed = QtCore.Signal(str, object)

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
        # Full session buffer for filter replay: (direction, sentence_type, line)
        self._history: list[tuple[str, str, str]] = []
        self._is_raw_mode = False
        # Binary auto-detection state — resets on each new session
        self._bin_sample_nonprint = 0   # non-printable bytes seen so far
        self._bin_sample_total = 0      # total bytes sampled
        self._bin_auto_triggered = False

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── toolbar ───────────────────────────────────────────────────────────
        toolbar = QtWidgets.QFrame()
        toolbar.setObjectName("wireTerminalToolbar")
        tb = QtWidgets.QHBoxLayout(toolbar)
        tb.setContentsMargins(10, 5, 10, 5)
        tb.setSpacing(8)

        # direction filter — segmented control
        seg = QtWidgets.QFrame()
        seg.setObjectName("wireSegmentBar")
        seg_lay = QtWidgets.QHBoxLayout(seg)
        seg_lay.setContentsMargins(2, 2, 2, 2)
        seg_lay.setSpacing(0)

        self._dir_group = QtWidgets.QButtonGroup(self)
        self._dir_group.setExclusive(True)
        self._btn_all = self._seg_btn("All", None, edge="left", checked=True)
        self._btn_n2c = self._seg_btn("NET→COM", "net→com", edge="mid")
        self._btn_c2n = self._seg_btn("COM→NET", "com→net", edge="mid")
        self._btn_rej = self._seg_btn("Reject", "reject", edge="right")
        for btn in (self._btn_all, self._btn_n2c, self._btn_c2n, self._btn_rej):
            self._dir_group.addButton(btn)
            seg_lay.addWidget(btn)
        self._dir_group.buttonClicked.connect(self._on_dir_segment_clicked)
        tb.addWidget(seg)

        # sentence type filter — popup until types appear on the wire
        self._type_menu = QtWidgets.QMenu(self)
        self._type_menu.aboutToShow.connect(self._populate_type_menu)
        self._btn_type = QtWidgets.QToolButton()
        self._btn_type.setObjectName("wireTypeBtn")
        self._btn_type.setText("Type")
        self._btn_type.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self._btn_type.setMenu(self._type_menu)
        self._btn_type.setToolTip("Filter by NMEA sentence type (GGA, RMC, …)")
        self._btn_type.setVisible(False)
        tb.addWidget(self._btn_type)

        # hidden combo keeps mixin/tests compat for type enumeration
        self._type_combo = QtWidgets.QComboBox()
        self._type_combo.setObjectName("wireTypeCombo")
        self._type_combo.addItem("All types", None)
        self._type_combo.hide()
        self._type_combo.currentIndexChanged.connect(self._on_type_filter_changed)

        # hex toggle (visible only in RAW mode)
        self._btn_hex = QtWidgets.QToolButton()
        self._btn_hex.setObjectName("wireHexBtn")
        self._btn_hex.setText("Hex")
        self._btn_hex.setCheckable(True)
        self._btn_hex.setToolTip("Show raw bytes as hex dump (RAW mode only)")
        self._btn_hex.setVisible(False)
        self._btn_hex.toggled.connect(self._on_hex_toggled)
        tb.addWidget(self._btn_hex)

        tb.addStretch(1)

        # right-side icon actions
        self._btn_wrap = self._icon_btn(
            "⏎", "Toggle line wrap (long lines vs. horizontal scroll)", checkable=True
        )
        self._btn_wrap.setToolTip("Wrap long lines  (click to toggle)")
        self._btn_wrap.toggled.connect(self._on_wrap_toggled)
        self._btn_pause = self._icon_btn("⏸", "Pause live display (bridge keeps running)", checkable=True)
        self._btn_pause.toggled.connect(self._on_pause_toggled)
        btn_clear = self._icon_btn("⌫", "Clear display")
        self._btn_save = self._icon_btn("💾", "Save visible traffic to file")
        btn_clear.clicked.connect(self._on_clear)
        self._btn_save.clicked.connect(self._on_save)

        actions = QtWidgets.QWidget()
        actions.setObjectName("wireToolbarActions")
        act_lay = QtWidgets.QHBoxLayout(actions)
        act_lay.setContentsMargins(0, 0, 0, 0)
        act_lay.setSpacing(4)
        act_lay.addWidget(self._btn_wrap)
        act_lay.addWidget(self._btn_pause)
        act_lay.addWidget(btn_clear)
        act_lay.addWidget(self._btn_save)
        tb.addWidget(actions)

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

        self._wire_feed.connect(self._feed_gui, QtCore.Qt.ConnectionType.QueuedConnection)

    # ── toolbar helpers ───────────────────────────────────────────────────────

    def _seg_btn(
        self,
        label: str,
        direction: Optional[str],
        *,
        edge: str = "mid",
        checked: bool = False,
    ) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(label)
        btn.setObjectName("wireSegBtn")
        btn.setProperty("segmentEdge", edge)
        btn.setProperty("directionKey", "" if direction is None else direction)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setFixedHeight(26)
        btn.setToolTip(f"Show {label} traffic only" if direction else "Show all traffic")
        return btn

    def _icon_btn(
        self, glyph: str, tooltip: str, *, checkable: bool = False
    ) -> QtWidgets.QToolButton:
        btn = QtWidgets.QToolButton()
        btn.setObjectName("wireIconBtn")
        btn.setText(glyph)
        btn.setToolTip(tooltip)
        btn.setFixedSize(28, 28)
        if checkable:
            btn.setCheckable(True)
        return btn

    def _on_dir_segment_clicked(self, btn: QtWidgets.QAbstractButton) -> None:
        key = btn.property("directionKey")
        direction = None if not key else str(key)
        self._set_dir_filter(direction)

    def _populate_type_menu(self) -> None:
        self._type_menu.clear()
        all_act = self._type_menu.addAction("All types")
        all_act.triggered.connect(lambda: self._set_type_filter(None))
        for stype in sorted(self._seen_types):
            act = self._type_menu.addAction(stype)
            act.triggered.connect(lambda _checked=False, s=stype: self._set_type_filter(s))

    def _set_type_filter(self, stype: Optional[str]) -> None:
        self._type_filter = stype
        if stype:
            self._btn_type.setText(stype)
            self._btn_type.setProperty("filterActive", "true")
        else:
            self._btn_type.setText("Type")
            self._btn_type.setProperty("filterActive", "false")
        self._btn_type.style().unpolish(self._btn_type)
        self._btn_type.style().polish(self._btn_type)
        idx = 0
        if stype:
            for i in range(self._type_combo.count()):
                if self._type_combo.itemData(i) == stype:
                    idx = i
                    break
        self._type_combo.blockSignals(True)
        self._type_combo.setCurrentIndex(idx)
        self._type_combo.blockSignals(False)
        self._rebuild_view()

    # ── public API ────────────────────────────────────────────────────────────

    def set_raw_mode(self, raw: bool) -> None:
        """Called by the mixin when bridge NMEA mode changes.

        Auto-enables hex display when entering raw/binary mode so binary
        streams (MAVLink, RTCM, etc.) are immediately readable.  Also resets
        the binary auto-detection state so it can re-sample the new session.
        """
        # Reset detection so the new session is sampled fresh
        self._bin_sample_nonprint = 0
        self._bin_sample_total = 0
        self._bin_auto_triggered = False

        self._is_raw_mode = raw
        self._btn_hex.setVisible(raw)
        if raw:
            self._btn_hex.setChecked(True)
        else:
            self._btn_hex.setChecked(False)

    def feed(self, direction: str, data: bytes) -> None:
        """Called from bridge callback thread — queued to GUI thread via Signal."""
        if not data:
            return
        self._wire_feed.emit(direction, bytes(data))

    def append_ops_line(self, text: str) -> None:
        """Bridge status / bench messages (GUI thread only)."""
        if self._paused:
            return
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if not line:
                continue
            formatted = f"{_ts()}  EVENT  {line}"
            self._history.append(("event", "", formatted))
            if len(self._history) > _MAX_LINES:
                self._history = self._history[-_MAX_LINES:]
            if self._matches_filters("event", ""):
                self._pending.append(formatted)

    def clear_display(self) -> None:
        """Clear the visible traffic view and session buffer."""
        self._on_clear()

    @QtCore.Slot(str, object)
    def _feed_gui(self, direction: str, data: object) -> None:
        """All display logic runs on the GUI thread."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            return
        raw = bytes(data)
        if self._paused:
            return

        stype = _sentence_type(raw)
        if stype and stype not in self._seen_types:
            self._seen_types.add(stype)
            self._type_combo.addItem(stype, stype)
            self._btn_type.setVisible(True)

        # ── Binary auto-detection ─────────────────────────────────────────────
        # Sample the first ~512 bytes of actual data; if >25% are non-printable
        # (outside tab/LF/CR/space-tilde range), treat as binary and auto-enable hex.
        if not self._bin_auto_triggered and self._bin_sample_total < 512:
            _PRINT = frozenset(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}
            self._bin_sample_nonprint += sum(1 for b in raw if b not in _PRINT)
            self._bin_sample_total += len(raw)
            if (
                self._bin_sample_total >= 32
                and self._bin_sample_nonprint / self._bin_sample_total > 0.25
            ):
                self._bin_auto_triggered = True
                self._is_raw_mode = True
                self._btn_hex.setVisible(True)
                self._btn_hex.setChecked(True)  # triggers _on_hex_toggled → _hex_mode = True
                # Inject a notice line so the operator knows why the view changed
                ts = _ts()
                notice = (
                    f"{ts}  EVENT  "
                    f"[Terminal] Binary stream detected "
                    f"({self._bin_sample_nonprint}/{self._bin_sample_total} non-printable bytes) "
                    f"— hex display enabled automatically."
                )
                self._history.append(("event", "", notice))
                self._pending.append(notice)

        # ── format line ───────────────────────────────────────────────────────
        dir_label = {
            "net→com": "NET→COM",
            "com→net": "COM→NET",
            "reject":  "REJECT ",
        }.get(direction, direction.upper())

        # Hex display works whenever _hex_mode is on, regardless of _is_raw_mode.
        # _is_raw_mode still controls whether the Hex button is visible.
        if self._hex_mode:
            body = f"[RAW {len(raw)} bytes]\n{_hex_format(raw)}"
        else:
            try:
                body = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            except Exception:
                body = repr(raw)

        line = f"{_ts()}  {dir_label}  {body}"
        self._history.append((direction, stype, line))
        if len(self._history) > _MAX_LINES:
            self._history = self._history[-_MAX_LINES:]

        if self._matches_filters(direction, stype):
            self._pending.append(line)

    def _matches_filters(self, direction: str, stype: str) -> bool:
        if direction == "event":
            return self._dir_filter is None and self._type_filter is None
        if self._dir_filter is not None and direction != self._dir_filter:
            return False
        if self._type_filter is not None and stype != self._type_filter:
            return False
        return True

    def _rebuild_view(self) -> None:
        """Re-render the text view from session history using active filters."""
        self._pending.clear()
        lines = [
            line
            for direction, stype, line in self._history
            if self._matches_filters(direction, stype)
        ]
        self._view.setPlainText("\n".join(lines))
        if lines:
            bar = self._view.verticalScrollBar()
            bar.setValue(bar.maximum())

    # ── flush ─────────────────────────────────────────────────────────────────

    def _flush(self) -> None:
        if not self._pending:
            return
        blob = "\n".join(self._pending) + "\n"
        self._pending.clear()
        at_bottom = self._at_bottom()
        cursor = self._view.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.insertText(blob)
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
        self._rebuild_view()

    def _on_type_filter_changed(self, index: int) -> None:
        self._type_filter = self._type_combo.itemData(index)
        self._rebuild_view()

    def _on_hex_toggled(self, checked: bool) -> None:
        self._hex_mode = bool(checked)

    def _on_wrap_toggled(self, checked: bool) -> None:
        mode = (
            QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth
            if checked
            else QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap
        )
        self._view.setLineWrapMode(mode)
        self._btn_wrap.setToolTip(
            "Line wrap ON — click to disable" if checked else "Wrap long lines  (click to toggle)"
        )

    def _on_pause_toggled(self, checked: bool) -> None:
        self._paused = checked
        self._btn_pause.setText("▶" if checked else "⏸")
        self._btn_pause.setToolTip(
            "Resume live display" if checked else "Pause live display (bridge keeps running)"
        )

    def _on_clear(self) -> None:
        self._view.clear()
        self._pending.clear()
        self._history.clear()
        self._seen_types.clear()
        # Reset binary auto-detection so the next session samples fresh
        self._bin_sample_nonprint = 0
        self._bin_sample_total = 0
        self._bin_auto_triggered = False
        # preserve "All types" entry
        self._type_combo.blockSignals(True)
        while self._type_combo.count() > 1:
            self._type_combo.removeItem(1)
        self._type_combo.setCurrentIndex(0)
        self._type_combo.blockSignals(False)
        self._type_filter = None
        self._btn_type.setText("Type")
        self._btn_type.setProperty("filterActive", "false")
        self._btn_type.setVisible(False)
        self._btn_type.style().unpolish(self._btn_type)
        self._btn_type.style().polish(self._btn_type)

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


def create_modern_activity_tab(parent: QtWidgets.QWidget) -> BridgeTerminalPanel:
    """Activity tab: wire-tap traffic plus hidden log_view for mixin compat."""
    from ui.controls import create_log_panel

    hidden = create_log_panel(parent, show_header=False)
    hidden.setParent(parent)
    hidden.hide()
    panel = BridgeTerminalPanel()
    parent.bridge_terminal = panel  # type: ignore[attr-defined]
    return panel


def create_bridge_terminal_tab(parent: QtWidgets.QWidget) -> BridgeTerminalPanel:
    """Legacy alias — prefer create_modern_activity_tab for Modern layout."""
    panel = BridgeTerminalPanel()
    parent.bridge_terminal = panel  # type: ignore[attr-defined]
    return panel

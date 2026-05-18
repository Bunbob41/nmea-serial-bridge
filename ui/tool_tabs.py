"""Send and Diagnostics tab content (shared by all UI variants)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from bridge_core import file_log_retention_hint
from nmea_static_sample import SAMPLE_ALT_M, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, build_gga

_WIDGET_SIZE_MAX = 16777215
_DIAG_COLLAPSED_STRIP_MIN = 40

_DEFAULT_DIAG_CARD_ORDER = [
    "file_log",
    "screen_log",
    "traffic_quality",
    "automated_checks",
]

_DEFAULT_DIAG_CARD_HEIGHTS: dict[str, int] = {
    "file_log": 200,
    "screen_log": 64,
    "traffic_quality": 200,
    "automated_checks": 280,
}

_DIAG_CARD_EXPANDED_CAP: dict[str, int] = {
    "file_log": 360,
    "screen_log": 120,
    "traffic_quality": 480,
    "automated_checks": 520,
}


def _diag_collapsed_strip_height(toggle: QtWidgets.QToolButton, margins: QtCore.QMargins) -> int:
    """Header strip height when collapsed — safe before first show/layout."""
    toggle.ensurePolished()
    btn_h = max(
        toggle.sizeHint().height(),
        toggle.minimumSizeHint().height(),
        toggle.fontMetrics().height() + 16,
    )
    return max(btn_h + margins.top() + margins.bottom(), _DIAG_COLLAPSED_STRIP_MIN)


def _diag_card_expanded(card: _IosCollapsibleCard) -> bool:
    return card.toggle_button().isChecked()


def _diag_card_natural_height(card: _IosCollapsibleCard, key: str) -> int:
    if not _diag_card_expanded(card):
        lay = card.layout()
        assert lay is not None
        return _diag_collapsed_strip_height(card.toggle_button(), lay.contentsMargins())
    card.apply_splitter_expand_style(True, sole_expanded=False)
    card.adjustSize()
    natural = max(card.sizeHint().height(), card.minimumSizeHint().height())
    floor = max(_DEFAULT_DIAG_CARD_HEIGHTS.get(key, 56), _DIAG_COLLAPSED_STRIP_MIN + 8)
    cap = _DIAG_CARD_EXPANDED_CAP.get(key, natural + 80)
    return max(min(natural, cap), floor)


def _target_diag_card_height(card: _IosCollapsibleCard, key: str, saved: dict[str, int]) -> int:
    if not _diag_card_expanded(card):
        lay = card.layout()
        assert lay is not None
        return _diag_collapsed_strip_height(card.toggle_button(), lay.contentsMargins())
    natural = _diag_card_natural_height(card, key)
    from_prefs = int(saved.get(key, 0))
    cap = _DIAG_CARD_EXPANDED_CAP.get(key, natural + 80)
    if from_prefs > _DIAG_COLLAPSED_STRIP_MIN + 4:
        return max(min(from_prefs, cap), natural)
    return natural


def _diag_expanded_count(widgets: dict[str, _IosCollapsibleCard], order: list[str]) -> int:
    return sum(1 for key in order if _diag_card_expanded(widgets[key]))


def _apply_diag_splitter_sizes(win: QtWidgets.QWidget, *, use_defaults: bool = False) -> None:
    splitter: QtWidgets.QSplitter | None = getattr(win, "_diag_cards_splitter", None)
    widgets = getattr(win, "_diag_card_widgets", None)
    if splitter is None or not isinstance(widgets, dict) or splitter.count() == 0:
        return
    order_fn = getattr(win, "_load_diag_card_order", None)
    order = list(order_fn()) if callable(order_fn) else list(_DEFAULT_DIAG_CARD_ORDER)
    order = [k for k in order if k in widgets] + [k for k in widgets if k not in order]
    ui_mode = getattr(win, "_ui_mode", "standard")
    from ui.ui_prefs import load_diag_card_sizes

    saved: dict[str, int] = {} if use_defaults else dict(load_diag_card_sizes(ui_mode))
    expanded_count = _diag_expanded_count(widgets, order)
    sole_expanded = expanded_count == 1

    sizes: list[int] = []
    for key in order:
        card = widgets[key]
        card.apply_splitter_expand_style(
            _diag_card_expanded(card),
            sole_expanded=sole_expanded and _diag_card_expanded(card),
        )
        sizes.append(_target_diag_card_height(card, key, saved))

    splitter.blockSignals(True)
    try:
        for i, key in enumerate(order):
            stretch = (
                1
                if _diag_card_expanded(widgets[key]) and not sole_expanded
                else 0
            )
            splitter.setStretchFactor(i, stretch)
        splitter.setSizes(sizes)
    finally:
        splitter.blockSignals(False)

    host = splitter.parentWidget()
    if host is not None:
        host.updateGeometry()


def _capture_diag_card_size(win: QtWidgets.QWidget, key: str) -> None:
    splitter: QtWidgets.QSplitter | None = getattr(win, "_diag_cards_splitter", None)
    widgets = getattr(win, "_diag_card_widgets", None)
    if splitter is None or not isinstance(widgets, dict) or key not in widgets:
        return
    order_fn = getattr(win, "_load_diag_card_order", None)
    order = list(order_fn()) if callable(order_fn) else list(_DEFAULT_DIAG_CARD_ORDER)
    if key not in order:
        return
    idx = order.index(key)
    sizes_list = splitter.sizes()
    if idx >= len(sizes_list):
        return
    h = int(sizes_list[idx])
    if h <= _DIAG_COLLAPSED_STRIP_MIN + 4:
        return
    from ui.ui_prefs import load_diag_card_sizes, save_diag_card_sizes

    ui_mode = getattr(win, "_ui_mode", "standard")
    saved = dict(load_diag_card_sizes(ui_mode))
    saved[key] = h
    save_diag_card_sizes(ui_mode, saved)


def _persist_diag_splitter_sizes(win: QtWidgets.QWidget) -> None:
    splitter: QtWidgets.QSplitter | None = getattr(win, "_diag_cards_splitter", None)
    widgets = getattr(win, "_diag_card_widgets", None)
    if splitter is None or not isinstance(widgets, dict):
        return
    order_fn = getattr(win, "_load_diag_card_order", None)
    order = list(order_fn()) if callable(order_fn) else list(_DEFAULT_DIAG_CARD_ORDER)
    order = [k for k in order if k in widgets]
    from ui.ui_prefs import load_diag_card_sizes, save_diag_card_sizes

    ui_mode = getattr(win, "_ui_mode", "standard")
    saved = dict(load_diag_card_sizes(ui_mode))
    sizes_list = splitter.sizes()
    for i, key in enumerate(order):
        if i >= len(sizes_list):
            break
        card = widgets.get(key)
        if card is None or not _diag_card_expanded(card):
            continue
        h = int(sizes_list[i])
        if h > _DIAG_COLLAPSED_STRIP_MIN + 4:
            saved[key] = h
    save_diag_card_sizes(ui_mode, saved)


def refresh_diag_cards(win: QtWidgets.QWidget) -> None:
    """Re-apply each diagnostics card size (fixes 0px strips after tab switch)."""
    widgets = getattr(win, "_diag_card_widgets", None)
    if not isinstance(widgets, dict):
        return
    for card in widgets.values():
        if isinstance(card, _IosCollapsibleCard):
            card.set_expanded(card.toggle_button().isChecked(), notify=False)
    _apply_diag_splitter_sizes(win)


class _IosCollapsibleCard(QtWidgets.QFrame):
    """Diagnostics-style card: header toggle + body; body height only (never cap whole card)."""

    def __init__(
        self,
        title: str,
        *,
        start_open: bool = False,
        on_toggled=None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("iosCard")
        self._on_toggled = on_toggled
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        self._toggle = QtWidgets.QToolButton()
        self._toggle.setObjectName("iosCardToggle")
        self._toggle.setText(title)
        self._toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setCheckable(True)

        self._body = QtWidgets.QWidget()
        self._body.setObjectName("iosCardBody")
        self._body_lay = QtWidgets.QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(4, 2, 4, 4)
        self._body_lay.setSpacing(8)

        self._toggle.toggled.connect(self._apply_expanded)
        outer.addWidget(self._toggle)
        outer.addWidget(self._body)
        self.set_expanded(start_open, notify=False)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        expanded = self._toggle.isChecked()
        self._apply_expanded(expanded, notify=False)

    def body_layout(self) -> QtWidgets.QVBoxLayout:
        return self._body_lay

    def toggle_button(self) -> QtWidgets.QToolButton:
        return self._toggle

    def set_expanded(self, expanded: bool, *, notify: bool = True) -> None:
        """Sync header, body, and layout (safe when signals are blocked)."""
        if self._toggle.isChecked() != expanded:
            self._toggle.blockSignals(True)
            self._toggle.setChecked(expanded)
            self._toggle.blockSignals(False)
        self._apply_expanded(expanded, notify=notify)

    def apply_splitter_expand_style(
        self, expanded: bool, *, sole_expanded: bool = False
    ) -> None:
        """Size policy for splitter rows — sole open card stays content-tight."""
        if expanded:
            self.setMaximumHeight(_WIDGET_SIZE_MAX)
            self.setMinimumHeight(_DIAG_COLLAPSED_STRIP_MIN)
            if sole_expanded:
                self.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Preferred,
                    QtWidgets.QSizePolicy.Policy.Maximum,
                )
                self._body.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Preferred,
                    QtWidgets.QSizePolicy.Policy.Maximum,
                )
            else:
                self.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Preferred,
                    QtWidgets.QSizePolicy.Policy.Expanding,
                )
                self._body.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Preferred,
                    QtWidgets.QSizePolicy.Policy.Expanding,
                )
        else:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            self._body.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Ignored,
                QtWidgets.QSizePolicy.Policy.Ignored,
            )

    def _apply_expanded(self, expanded: bool, *, notify: bool = True) -> None:
        self._toggle.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow
        )
        if expanded:
            self.apply_splitter_expand_style(expanded, sole_expanded=False)
            self._body.setMaximumHeight(_WIDGET_SIZE_MAX)
            self._body.setMinimumHeight(0)
            self._body.setVisible(True)
            lay = self.layout()
            assert lay is not None
            lay.setContentsMargins(8, 8, 8, 8)
        else:
            self.apply_splitter_expand_style(False)
            self._body.setMaximumHeight(0)
            self._body.setMinimumHeight(0)
            self._body.setVisible(False)
            lay = self.layout()
            assert lay is not None
            lay.setContentsMargins(8, 4, 8, 4)
            m = lay.contentsMargins()
            strip_h = _diag_collapsed_strip_height(self._toggle, m)
            self.setMinimumHeight(strip_h)
            self.setMaximumHeight(strip_h)
        self.updateGeometry()
        self.adjustSize()
        parent = self.parentWidget()
        while parent is not None:
            parent.updateGeometry()
            if isinstance(parent, QtWidgets.QScrollArea):
                break
            parent = parent.parentWidget()
        if notify and callable(self._on_toggled):
            self._on_toggled(expanded)


def _add_collapsible_card(
    host: QtWidgets.QVBoxLayout | QtWidgets.QSplitter,
    title: str,
    *,
    start_open: bool = False,
    on_toggled=None,
) -> QtWidgets.QVBoxLayout:
    """Create an iOS-style collapsible card and return its body layout."""
    card = _IosCollapsibleCard(title, start_open=start_open, on_toggled=on_toggled)
    if isinstance(host, QtWidgets.QSplitter):
        host.addWidget(card)
    else:
        host.setSpacing(max(host.spacing(), 10))
        host.addWidget(card)
    return card.body_layout()


def _scrollable(inner: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
    """Scroll wrapper that inherits app theme (avoids Windows default white viewport)."""
    inner.setObjectName("toolTabScrollHost")
    inner.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    inner.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Minimum,
    )

    scroll = QtWidgets.QScrollArea()
    scroll.setObjectName("toolTabScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFocusPolicy(QtCore.Qt.FocusPolicy.WheelFocus)
    scroll.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    scroll.viewport().setObjectName("toolTabScrollViewport")
    scroll.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    scroll.setWidget(inner)
    return scroll


def wrap_main_tab_scroll(inner: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
    """Scroll wrapper for Standard main tabs (Connect, etc.) when content exceeds viewport."""
    return _scrollable(inner)


def build_guide_tab(_parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Transparent quick guide: what works well, limits, and current focus."""
    host = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(14, 14, 14, 14)
    lay.setSpacing(10)

    title = QtWidgets.QLabel("Project guide — honest status")
    title.setObjectName("tabHint")
    lay.addWidget(title)

    body = QtWidgets.QLabel(
        "What this bridge does well:\n"
        "• Reliable UDP/TCP ↔ COM forwarding for survey INS/GNSS.\n"
        "• Preset-driven startup with quick field workflows.\n"
        "• Clear run-state chips, logs, and bench diagnostics.\n\n"
        "Known limits / trade-offs:\n"
        "• No kernel virtual COM driver (user-space only).\n"
        "• Layout polish is active work; first-paint edge cases can still appear.\n"
        "• Diagnostics are practical but not a full terminal/packet suite.\n\n"
        "Current focus:\n"
        "• Connect tab stability (no clipping / no stale layout states).\n"
        "• Readability and field ergonomics (chips, cards, quick controls).\n"
        "• Truthful operator guidance and safer defaults."
    )
    body.setWordWrap(True)
    body.setObjectName("tabNote")
    body.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    lay.addWidget(body)

    note = QtWidgets.QLabel(
        "Use Product Demo for live walkthrough actions. "
        "Use this Guide tab for static operation/evaluation notes."
    )
    note.setWordWrap(True)
    note.setObjectName("tabHint")
    lay.addWidget(note)
    lay.addStretch(1)
    return _scrollable(host)


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
        if not on:
            _capture_diag_card_size(parent, key)
        if hasattr(parent, "_save_diag_card_state"):
            try:
                parent._save_diag_card_state(key, on)
            except Exception:
                pass
        QtCore.QTimer.singleShot(0, lambda: _apply_diag_splitter_sizes(parent))

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

    splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
    splitter.setObjectName("diagCardsSplitter")
    splitter.setChildrenCollapsible(False)
    lay.addWidget(splitter, 1)
    parent._diag_cards_splitter = splitter
    splitter.splitterMoved.connect(lambda *_args: _persist_diag_splitter_sizes(parent))

    card_widgets: dict[str, QtWidgets.QWidget] = {}

    def _register_card(key: str) -> None:
        idx = splitter.count() - 1
        widget = splitter.widget(idx) if idx >= 0 else None
        if widget is not None:
            widget.setProperty("diagCardKey", key)
            card_widgets[key] = widget

    fv = _add_collapsible_card(
        splitter,
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
        splitter,
        "On-screen log",
        start_open=_card_open("screen_log", False),
        on_toggled=lambda on: _persist_card("screen_log", on),
    )
    _register_card("screen_log")
    parent.btn_clear_ui = QtWidgets.QPushButton("Clear live log panel")
    parent.btn_clear_ui.setToolTip("Clears the main log view — does not delete the file above.")
    sv.addWidget(parent.btn_clear_ui)

    qv = _add_collapsible_card(
        splitter,
        "Traffic & data quality (honest counters)",
        start_open=_card_open("traffic_quality", False),
        on_toggled=lambda on: _persist_card("traffic_quality", on),
    )
    _register_card("traffic_quality")
    qa = QtWidgets.QLabel(
        "Quick health read while Running:\n\n"
        "• ↓ / ↑ Hz — Current sentence rate net→COM and COM→net.\n"
        "• transport OK / warn — Queue pressure, drops, or rejects.\n"
        "• session totals — Lifetime counts this run.\n"
        "• GNSS chip — fix quality, sats, HDOP, stale detection.\n\n"
        "This card is a fast operator legend (not a protocol deep dive).\n"
        "For transparent scope, strengths, and current limitations, open the Guide tab."
    )
    qa.setWordWrap(True)
    qa.setObjectName("tabNote")
    qa.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    qv.addWidget(qa)

    bv = _add_collapsible_card(
        splitter,
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
    parent.btn_bench_pair_setup.setObjectName("btnBenchPairSetupDiag")
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
    parent._diag_card_widgets = card_widgets
    parent._diag_cards_layout = lay
    if hasattr(parent, "_apply_diag_card_order"):
        parent._apply_diag_card_order()
    else:
        _apply_diag_splitter_sizes(parent)

    return _scrollable(host)

"""Send and Diagnostics tab content (shared by all UI variants)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from bridge_core import file_log_retention_hint
from nmea_static_sample import SAMPLE_ALT_M, SAMPLE_LAT_DEG, SAMPLE_LON_DEG, build_gga
from ui.doc_viewer import show_bundled_doc

_WIDGET_SIZE_MAX = 16777215
_DIAG_COLLAPSED_STRIP_MIN = 40

_DEFAULT_DIAG_CARD_ORDER = [
    "automated_checks",
    "local_backup",
    "file_log",
    "screen_log",
]

_DEFAULT_DIAG_CARD_HEIGHTS: dict[str, int] = {
    "local_backup": 120,
    "file_log": 200,
    "screen_log": 64,
    "automated_checks": 280,
}

_DIAG_CARD_EXPANDED_CAP: dict[str, int] = {
    "local_backup": 180,
    "file_log": 360,
    "screen_log": 120,
    "automated_checks": 520,
}

# Tools → Phone — in-tab help (also referenced by tests).
PHONE_API_TOKEN_HELP = (
    "<ol>"
    "<li>Generate or paste a long random API token below.</li>"
    "<li>Required when <b>Allow LAN / Tailscale</b> is on and the token field is not empty.</li>"
    "<li>With remote access off, the dashboard on this PC alone does not check the token.</li>"
    "<li>Use <b>Copy link</b>, <b>Paste link</b>, or the QR code to hand the same token to your phone.</li>"
    "</ol>"
)

# Stack Server & Network | Phone Pairing cards vertically below this content width (px).
PHONE_CARDS_STACK_BELOW_W = 880


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


from ui.fonts import FONT_FAMILY_QSS

_GUIDE_CSS = """
body  {
    font-family: __UI_FONT__;
    font-size: 13px;
    margin: 0;
    padding: 16px 18px;
    background: #0a0e14;
    color: #c8d8f0;
    line-height: 1.6;
}
h2    {
    font-size: 14px;
    font-weight: 700;
    margin: 0 0 6px 0;
    color: #60a5fa;
    letter-spacing: 0.03em;
}
h3    {
    font-size: 11.5px;
    font-weight: 700;
    margin: 16px 0 5px 0;
    color: #93c5fd;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
p     { margin: 4px 0 10px 0; }
ol    { margin: 4px 0 10px 18px; padding: 0; }
ul    { margin: 2px 0 8px 22px; padding: 0; }
li    { margin-bottom: 5px; }
hr    { border: none; border-top: 1px solid #1e2d42; margin: 14px 0; }
code  {
    background: #141f2e;
    color: #67e8f9;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 11.5px;
    font-family: __UI_FONT__;
}
b     { color: #f0f7ff; }
em    { color: #94a3b8; font-style: normal; }
.note {
    color: #64748b;
    font-size: 12px;
    margin-top: 10px;
    padding: 6px 10px;
    border-left: 2px solid #1e3a5f;
    background: #0d1a2a;
    border-radius: 0 4px 4px 0;
}
""".replace("__UI_FONT__", FONT_FAMILY_QSS)

_GUIDE_START = """
<h2>Start here — stuck on connect?</h2>
<p><em>Most survey setups use <b>UDP listen</b> on the <b>Control</b> tab. Use this page first,
then open the UDP / TCP tabs for mode-specific detail.</em></p>
<hr/>
<h3>60-second path</h3>
<ol>
  <li><b>Control tab → Serial link:</b> pick your <b>COM</b> port (click Refresh if missing),
      set <b>Baud</b> to match the receiver (usually <code>115200</code>).</li>
  <li><b>Control tab → Network path → Listen host</b> <code>0.0.0.0</code> (all interfaces)
      or your PC LAN IP; <b>Listen port</b> to match the INS/GNSS output (often <code>10110</code>).</li>
  <li>Press <b>▶ Start</b> in the header bar (shortcut <code>Ctrl+B</code>).
      The status banner turns green and shows <b>Running.</b></li>
  <li>Switch to the <b>Activity</b> tab — sentences should stream in with direction labels.
      Status messages (start/stop, drops) appear as <b>EVENT</b> lines.</li>
  <li>Open <b>HUD</b> from the survey bar (or <code>Ctrl+Shift+S</code>) for live Hz,
      drops, and GNSS fix while Running.</li>
</ol>
<h3>Where things live</h3>
<ul>
  <li><b>COM + UDP listen:</b> Control tab → Serial link &amp; Network path.</li>
  <li><b>TCP / UDP remote:</b> Control tab → Network path → enable
      <b>Advanced network (TCP / UDP remote / all modes)</b>, then pick a mode radio.</li>
  <li><b>Named setups (presets):</b> Settings tab → Presets — click a name to <b>Load</b>, edit,
      <b>Save</b> or <b>Save as…</b> (bridge must be stopped to load).</li>
  <li><b>NMEA mode:</b> Settings tab → NMEA — Passthrough (recommended), Strict, or Raw binary.</li>
  <li><b>Phone / browser dashboard:</b> Settings tab → Phone (token, port, QR).</li>
  <li><b>Connection Hub:</b> Tools → Hub — auto-discovers GNSS serial ports and UDP contexts; click a
      card to populate the Control tab fields automatically.</li>
  <li><b>Tray:</b> closing the window while running hides to the tray; use tray <b>Exit</b>
      to quit completely.</li>
</ul>
<p class="note">Bench help: Settings → Diagnostics → <b>Bench pair setup…</b> or <b>Bench checklist.</b>
Full docs: Getting started… / Operator guide… buttons above.</p>
"""

_GUIDE_UDP = """
<h2>UDP — listen vs remote</h2>
<p><em><b>UDP listen</b> (default): this PC receives datagrams on a bound port — typical for
Trimble/INS Ethernet NMEA. <b>UDP remote</b> (Advanced): send to one fixed host:port.</em></p>
<hr/>
<h3>UDP listen (most survey installs)</h3>
<ol>
  <li><b>Control tab → Serial link:</b> set <b>COM</b> + <b>Baud</b> (e.g. COM7 @ 115200).</li>
  <li><b>Control tab → Network path:</b> set <b>Listen host</b> (e.g. <code>0.0.0.0</code>)
      and <b>Listen port</b> (e.g. <code>10110</code>).
      These are the <em>receive</em> fields — not target/destination.</li>
  <li>Optional: <b>Fan-out — send serial data to all UDP peers</b> — COM→network is copied to
      every sender that has talked to this port (UDP listen only).</li>
  <li>Press <b>▶ Start.</b> The header banner should turn green.
      The header status banner should show <b>Running</b>; use the <b>Activity</b>
      tab to confirm sentences are flowing.</li>
  <li>To reuse later: Settings → Presets → <b>Save as…</b> (load when stopped).</li>
</ol>
<h3>UDP remote (fixed peer — bench or one chart PC)</h3>
<ol>
  <li>Control tab → Network path → check <b>Advanced network (TCP / UDP remote / all modes).</b></li>
  <li>Under <b>Mode</b>, select <b>UDP remote.</b></li>
  <li><b>UDP remote (fixed peer)</b> → <b>Host</b> (e.g. <code>127.0.0.1</code> for local software)
      and <b>Port</b> (e.g. <code>10110</code>).</li>
  <li>Press <b>▶ Start.</b> Fan-out does not apply in remote mode.</li>
</ol>
<p class="note">Advanced network is also accessible from Settings → Presets if you prefer to
configure there, then press ▶ Start in the header.</p>
"""

_GUIDE_TCP_CLIENT = """
<h2>TCP client — connect outward to a server</h2>
<p><em>Use when your serial device should join an existing TCP service (remote host listens;
this app connects as the client).</em></p>
<hr/>
<h3>Steps</h3>
<ol>
  <li><b>Control tab → Serial link:</b> correct <b>COM</b> and <b>Baud.</b></li>
  <li>Control tab → Network path → check <b>Advanced network (TCP / UDP remote / all modes).</b></li>
  <li>Under <b>Mode</b>, select <b>TCP client.</b></li>
  <li><b>TCP client</b> group → <b>Host</b> (server IP) and <b>Port.</b></li>
  <li>Optional: <b>TCP reconnect delay</b> (seconds between retries if the server drops).</li>
  <li>Press <b>▶ Start</b> — the app actively opens the TCP connection.
      Watch the header status banner and <b>Activity</b> tab for confirmation.</li>
  <li>Save the setup: Settings → Presets → <b>Save as…</b> when it works.</li>
</ol>
<p class="note">TCP client requires Advanced network to be checked in Control → Network path.</p>
"""

_GUIDE_TCP_SERVER = """
<h2>TCP server — host a port on this PC</h2>
<p><em>Use when Hypack, a chart plotter, or another machine must connect <em>to</em> this PC
to read/write the COM port.</em></p>
<hr/>
<h3>Steps</h3>
<ol>
  <li><b>Control tab → Serial link:</b> set <b>COM</b> + <b>Baud.</b></li>
  <li>Control tab → Network path → check <b>Advanced network (TCP / UDP remote / all modes).</b></li>
  <li>Under <b>Mode</b>, select <b>TCP server.</b></li>
  <li><b>TCP server</b> group → <b>Bind</b>
      (<code>0.0.0.0</code> = any interface, <code>127.0.0.1</code> = this PC only)
      and <b>Port</b> (e.g. <code>4001</code>). Add an inbound Windows Firewall rule for
      the port if external clients need access.</li>
  <li>Press <b>▶ Start</b> — the app listens until a client connects (one client at a time).
      The header status banner updates when a client attaches.</li>
  <li>Point your client software at this PC's IP and the chosen listen port.</li>
</ol>
<p class="note">Bench TCP test: Settings → Diagnostics → automated TCP stress/demo buttons
(require TCP server mode + bridge running).</p>
"""

_GUIDE_CHECKLIST = """
<h2>Before you press ▶ Start</h2>
<p><em>Quick checks when nothing moves on the wire or sentences look wrong.</em></p>
<hr/>
<ul>
  <li><b>COM:</b> correct port (hit Refresh), not held by PuTTY/Tera Term/another app —
      use <b>Unlock COM</b> in Tools → Hub if shown. Baud matches the receiver exactly.</li>
  <li><b>UDP listen:</b> Listen host / Listen port in the Control tab match how the
      sender is configured; ping the INS from Settings → Terminal if needed.</li>
  <li><b>UDP remote / TCP:</b> Advanced network checked in Control → Network path;
      correct mode radio selected; host/port fields match the peer.</li>
  <li><b>Ports:</b> integers <code>1</code>–65535; avoid &lt; <code>1024</code>
      unless the OS permits it. No two apps can bind the same port simultaneously.</li>
  <li><b>Firewall:</b> add an inbound rule for UDP listen / TCP server ports if other
      machines need to reach this PC.</li>
  <li><b>NMEA mode</b> (Settings → NMEA):
      <b>Passthrough</b> for normal GNSS receivers;
      <b>Strict + sentence filter</b> to drop malformed lines;
      <b>Raw binary</b> only for RTCM or non-NMEA byte streams.</li>
  <li><b>While running:</b> the header status banner turns green; open <b>HUD</b>
      for live Hz, byte counts, drops, and rejects in plain language.</li>
</ul>
<p class="note">Still stuck? Open <b>Getting started…</b> above or run
Settings → Diagnostics → <b>Bench checklist</b> with the bridge stopped.</p>
"""


_PHONE_FORM_LABEL_MIN_WIDTH = 120
_PHONE_INLINE_BTN_PX = 32
_PHONE_FIELD_ACTION_GAP = 8


def _configure_phone_form(form: QtWidgets.QFormLayout) -> None:
    form.setContentsMargins(0, 0, 0, 0)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(12)
    form.setLabelAlignment(
        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    form.setFormAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
    )
    form.setFieldGrowthPolicy(
        QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
    )
    form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)


def apply_phone_dashboard_responsive(
    parent: QtWidgets.QWidget,
    width: int | None = None,
) -> None:
    """Stack Phone dashboard cards vertically when the window is narrower than ~720px."""
    grid = getattr(parent, "_phone_cards_grid", None)
    server = getattr(parent, "_phone_dashboard_server_card", None)
    phone = getattr(parent, "_phone_dashboard_phone_card", None)
    if grid is None or server is None or phone is None:
        return
    win_w = width if width is not None else parent.width()
    stack_vertical = win_w < PHONE_CARDS_STACK_BELOW_W
    if stack_vertical == getattr(parent, "_phone_cards_vertical", False):
        return

    grid.removeWidget(server)
    grid.removeWidget(phone)
    if stack_vertical:
        grid.addWidget(server, 0, 0)
        grid.addWidget(phone, 1, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.setRowStretch(0, 0)
        grid.setRowStretch(1, 0)
    else:
        grid.addWidget(server, 0, 0)
        grid.addWidget(phone, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 0)
        grid.setRowStretch(1, 0)
    parent._phone_cards_vertical = stack_vertical


def _phone_form_label(text: str, tooltip: str = "") -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text if text.endswith(":") else f"{text}:")
    lbl.setMinimumWidth(_PHONE_FORM_LABEL_MIN_WIDTH)
    lbl.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    if tooltip:
        lbl.setToolTip(tooltip)
    return lbl


def _phone_field_anchor(widget: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Left-align a control in the form field column (host spans full field width)."""
    host = QtWidgets.QWidget()
    host.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    row = QtWidgets.QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    row.addWidget(widget, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
    row.addStretch(1)
    return host


def _phone_form_add_row(
    form: QtWidgets.QFormLayout,
    label: QtWidgets.QLabel | str,
    field: QtWidgets.QWidget,
    *,
    anchor_field: bool = True,
    align_top: bool = False,
) -> None:
    """Add a form row; narrow fields are left-aligned, not centered in the column."""
    label_w = label if isinstance(label, QtWidgets.QLabel) else _phone_form_label(str(label))
    field_w = _phone_field_anchor(field) if anchor_field else field
    form.addRow(label_w, field_w)
    if align_top:
        row = form.rowCount() - 1
        label_item = form.itemAt(row, QtWidgets.QFormLayout.ItemRole.LabelRole)
        field_item = form.itemAt(row, QtWidgets.QFormLayout.ItemRole.FieldRole)
        if label_item is not None:
            label_item.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight
                | QtCore.Qt.AlignmentFlag.AlignTop
            )
        if field_item is not None:
            field_item.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignLeft
                | QtCore.Qt.AlignmentFlag.AlignTop
            )


def _phone_icon_tool_button(
    style_widget: QtWidgets.QWidget,
    pixmap: QtWidgets.QStyle.StandardPixmap,
    tooltip: str,
    *,
    object_name: str = "webInlineBtn",
    icon_role: str = "",
    checkable: bool = False,
    text_fallback: str = "",
) -> QtWidgets.QToolButton:
    """Icon-only inline button; ``icon_role`` tags slots for optional custom SVG assets."""
    btn = QtWidgets.QToolButton()
    btn.setObjectName(object_name)
    btn.setToolTip(tooltip)
    btn.setAutoRaise(False)
    btn.setCheckable(checkable)
    btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
    btn.setIconSize(QtCore.QSize(18, 18))
    btn.setFixedSize(_PHONE_INLINE_BTN_PX, _PHONE_INLINE_BTN_PX)
    if icon_role:
        btn.setProperty("webIconRole", icon_role)
    icon = style_widget.style().standardIcon(pixmap)
    if icon.isNull() and text_fallback:
        btn.setText(text_fallback)
        btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
    else:
        btn.setIcon(icon)
    return btn


def _phone_text_tool_button(
    text: str,
    tooltip: str,
    *,
    object_name: str = "webInlineBtn",
    checkable: bool = False,
) -> QtWidgets.QToolButton:
    btn = QtWidgets.QToolButton()
    btn.setObjectName(object_name)
    btn.setText(text)
    btn.setToolTip(tooltip)
    btn.setAutoRaise(False)
    btn.setCheckable(checkable)
    btn.setFixedSize(_PHONE_INLINE_BTN_PX, _PHONE_INLINE_BTN_PX)
    return btn


def _phone_inline_action_bar(*buttons: QtWidgets.QToolButton) -> QtWidgets.QWidget:
    host = QtWidgets.QWidget()
    host.setObjectName("webInlineActionBar")
    row = QtWidgets.QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    for btn in buttons:
        btn.setFixedSize(_PHONE_INLINE_BTN_PX, _PHONE_INLINE_BTN_PX)
        row.addWidget(btn)
    return host


def _phone_input_with_actions(
    field: QtWidgets.QWidget,
    *buttons: QtWidgets.QToolButton,
) -> QtWidgets.QWidget:
    host = QtWidgets.QWidget()
    row = QtWidgets.QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(_PHONE_FIELD_ACTION_GAP)
    row.addWidget(field, 1)
    if buttons:
        row.addWidget(_phone_inline_action_bar(*buttons), 0)
    return host


def _phone_port_controls_row(
    spin: QtWidgets.QWidget,
    lock_btn: QtWidgets.QToolButton,
    status_lbl: QtWidgets.QLabel,
) -> QtWidgets.QWidget:
    host = QtWidgets.QWidget()
    row = QtWidgets.QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    row.addWidget(
        spin,
        0,
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
    )
    row.addWidget(lock_btn, 0)
    row.addWidget(status_lbl, 0)
    row.addStretch(1)
    return host


def _phone_dashboard_card(title: str) -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout]:
    frame = QtWidgets.QFrame()
    frame.setObjectName("phoneDashboardCard")
    frame.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    lay = QtWidgets.QVBoxLayout(frame)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(10)
    title_lbl = QtWidgets.QLabel(title)
    title_lbl.setObjectName("phoneCardTitle")
    lay.addWidget(title_lbl)
    return frame, lay


def _wire_web_control_widgets(parent: QtWidgets.QWidget) -> None:
    """Connect web API / phone dashboard controls (shared by Phone tab only)."""
    if hasattr(parent, "_on_web_ui_prefs_changed"):
        parent.chk_web_enabled.toggled.connect(parent._on_web_ui_prefs_changed)
    if hasattr(parent, "_on_web_port_spin_changed"):
        parent.spin_web_port.valueChanged.connect(parent._on_web_port_spin_changed)
    if hasattr(parent, "_on_web_port_unlock_toggled"):
        parent.chk_web_port_unlock.toggled.connect(parent._on_web_port_unlock_toggled)
    if hasattr(parent, "_on_web_ui_prefs_changed"):
        parent.edit_web_token.editingFinished.connect(parent._on_web_ui_prefs_changed)
        parent.edit_web_phone_url.editingFinished.connect(parent._normalize_phone_url_field)
        parent.edit_web_phone_url.editingFinished.connect(parent._on_web_ui_prefs_changed)
    if hasattr(parent, "_on_web_lan_toggled"):
        parent.chk_web_lan.toggled.connect(parent._on_web_lan_toggled)
    elif hasattr(parent, "_on_web_ui_prefs_changed"):
        parent.chk_web_lan.toggled.connect(parent._on_web_ui_prefs_changed)
    if hasattr(parent, "_on_web_generate_token"):
        parent.btn_web_token_generate.clicked.connect(parent._on_web_generate_token)
    if hasattr(parent, "_on_web_copy_token"):
        parent.btn_web_token_copy.clicked.connect(parent._on_web_copy_token)
    if hasattr(parent, "_on_web_copy_phone_setup"):
        parent.btn_web_copy_setup.clicked.connect(parent._on_web_copy_phone_setup)
    if hasattr(parent, "_on_web_paste_setup"):
        parent.btn_web_paste_setup.clicked.connect(parent._on_web_paste_setup)
    if hasattr(parent, "_on_web_detect_phone_url"):
        parent.btn_web_detect_phone_url.clicked.connect(parent._on_web_detect_phone_url)
    if hasattr(parent, "_on_web_show_qr_toggled"):
        parent.chk_web_show_qr.toggled.connect(parent._on_web_show_qr_toggled)
        parent.edit_web_token.textChanged.connect(parent._on_web_token_text_changed)


def build_phone_dashboard_tab(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Web API, Tailscale URL, token, and QR — dedicated Tools page (not buried in Guide)."""
    inner = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(inner)
    lay.setContentsMargins(12, 12, 12, 12)
    lay.setSpacing(12)

    cards_host = QtWidgets.QWidget()
    cards_host.setObjectName("phoneDashboardCardsHost")
    cards_grid = QtWidgets.QGridLayout(cards_host)
    cards_grid.setContentsMargins(0, 0, 0, 0)
    cards_grid.setHorizontalSpacing(12)
    cards_grid.setVerticalSpacing(12)

    server_card, server_lay = _phone_dashboard_card("Server & Network")
    server_form_host = QtWidgets.QWidget()
    server_form = QtWidgets.QFormLayout(server_form_host)
    _configure_phone_form(server_form)

    parent.chk_web_enabled = QtWidgets.QCheckBox("Enable")
    parent.chk_web_enabled.setToolTip(
        "HTTP dashboard on this PC (port 8765 by default). On at launch for phone/monitor use. "
        "Requires a token when LAN/Tailscale access is enabled."
    )

    from ui.controls import WebPortSpinBox

    parent.spin_web_port = WebPortSpinBox()
    parent.spin_web_port.setRange(1024, 65535)
    parent.spin_web_port.setValue(8765)
    parent.spin_web_port.setAccelerated(True)
    parent.spin_web_port.setToolTip(
        "TCP port for the dashboard. Locked by default — click the lock to edit for 10 seconds. "
        "Mouse wheel does not change this value."
    )
    parent.chk_web_port_unlock = _phone_text_tool_button(
        "🔒",
        "Unlock port for 10 seconds to type or use step buttons",
        object_name="webPortLockBtn",
        checkable=True,
    )
    parent.chk_web_port_unlock.setAccessibleName("Unlock Web API port")
    parent.lbl_web_port_status = QtWidgets.QLabel("Locked")
    parent.lbl_web_port_status.setObjectName("webPortStatus")
    parent.lbl_web_port_status.setProperty("statusKind", "locked")

    parent.lbl_web_listen = QtWidgets.QLabel()
    parent.lbl_web_listen.setObjectName("webListenStatus")
    parent.lbl_web_listen.setWordWrap(True)
    parent.lbl_web_listen.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
    )
    parent.lbl_web_listen.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Preferred,
    )
    parent.lbl_web_listen.setMinimumHeight(0)

    parent.chk_web_lan = QtWidgets.QCheckBox("Allow LAN / Tailscale (0.0.0.0)")
    parent.chk_web_lan.setToolTip(
        "Listen on all network interfaces so phones on Tailscale or the survey LAN can connect. "
        "Use Windows firewall and the remote control token. Localhost-only is safer on bench PCs."
    )

    parent.btn_web_open_dashboard = QtWidgets.QPushButton("Open dashboard")
    parent.btn_web_open_dashboard.setObjectName("webPrimaryBtn")
    parent.btn_web_open_dashboard.setToolTip(
        "Open http://127.0.0.1:PORT/ in your default browser on this PC."
    )
    if hasattr(parent, "_on_web_open_dashboard"):
        parent.btn_web_open_dashboard.clicked.connect(parent._on_web_open_dashboard)
    parent.btn_web_open_dashboard.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )

    port_controls = _phone_port_controls_row(
        parent.spin_web_port,
        parent.chk_web_port_unlock,
        parent.lbl_web_port_status,
    )
    port_controls.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    _phone_form_add_row(
        server_form,
        _phone_form_label(
            "Web API",
            "Turn the local HTTP dashboard on or off on this PC.",
        ),
        parent.chk_web_enabled,
    )
    _phone_form_add_row(
        server_form,
        _phone_form_label(
            "Port",
            "Dashboard TCP port. Unlock briefly to change; restarts apply automatically.",
        ),
        port_controls,
        anchor_field=False,
    )
    listen_host = QtWidgets.QWidget()
    listen_host.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Minimum,
    )
    listen_lay = QtWidgets.QVBoxLayout(listen_host)
    listen_lay.setContentsMargins(0, 10, 0, 4)
    listen_lay.setSpacing(0)
    listen_lay.addWidget(parent.lbl_web_listen, 0)
    _phone_form_add_row(
        server_form,
        _phone_form_label(
            "This PC",
            "Local dashboard URL — open on this computer only.",
        ),
        listen_host,
        anchor_field=False,
        align_top=True,
    )
    _phone_form_add_row(
        server_form,
        _phone_form_label(
            "Remote access",
            "When enabled, bind to 0.0.0.0 so phones reach this PC via Tailscale or LAN IP.",
        ),
        parent.chk_web_lan,
    )
    _phone_form_add_row(
        server_form,
        _phone_form_label("Open", "Open the dashboard in your default browser on this PC."),
        parent.btn_web_open_dashboard,
    )
    server_lay.addWidget(server_form_host, 1)

    phone_card, phone_lay = _phone_dashboard_card("Phone Pairing")
    token_help = QtWidgets.QLabel(PHONE_API_TOKEN_HELP)
    token_help.setWordWrap(True)
    token_help.setTextFormat(QtCore.Qt.TextFormat.RichText)
    token_help.setObjectName("phonePairingSteps")
    phone_lay.addWidget(token_help)
    phone_form_host = QtWidgets.QWidget()
    phone_form = QtWidgets.QFormLayout(phone_form_host)
    _configure_phone_form(phone_form)

    parent.edit_web_phone_url = QtWidgets.QLineEdit()
    parent.edit_web_phone_url.setPlaceholderText("http://100.x.x.x:8765")
    parent.edit_web_phone_url.setToolTip(
        "URL your phone opens in the browser — use this PC's Tailscale or LAN IP, not 127.0.0.1. "
        "Run tailscale ip in cmd if unsure. Used for QR and setup links."
    )
    sp = QtWidgets.QStyle.StandardPixmap
    parent.btn_web_detect_phone_url = _phone_icon_tool_button(
        inner,
        sp.SP_BrowserReload,
        "Detect Tailscale / LAN IP and fill the URL",
        icon_role="detect",
    )
    parent.btn_web_detect_phone_url.setAccessibleName("Detect IP")
    parent.btn_web_copy_setup = _phone_icon_tool_button(
        inner,
        sp.SP_FileIcon,
        "Copy one-tap phone setup link (includes token)",
        icon_role="copyLink",
    )
    parent.btn_web_copy_setup.setAccessibleName("Copy Link")
    parent.btn_web_paste_setup = _phone_icon_tool_button(
        inner,
        sp.SP_DialogOpenButton,
        "Paste setup link from clipboard and import token",
        icon_role="pasteLink",
    )
    parent.btn_web_paste_setup.setAccessibleName("Paste Link")
    phone_url_field = _phone_input_with_actions(
        parent.edit_web_phone_url,
        parent.btn_web_detect_phone_url,
        parent.btn_web_copy_setup,
        parent.btn_web_paste_setup,
    )

    parent.edit_web_token = QtWidgets.QLineEdit()
    parent.edit_web_token.setPlaceholderText("Generate or paste token")
    parent.edit_web_token.setToolTip(
        "Sent as X-Bridge-Token on remote control requests when LAN/Tailscale is on. "
        "Generate a new secret, paste your own, or import from a setup link."
    )
    parent.edit_web_token.setClearButtonEnabled(True)
    parent.btn_web_token_generate = _phone_icon_tool_button(
        inner,
        sp.SP_FileDialogNewFolder,
        "Generate a new random API token",
        icon_role="generateToken",
    )
    parent.btn_web_token_generate.setAccessibleName("Generate token")
    parent.btn_web_token_copy = _phone_icon_tool_button(
        inner,
        sp.SP_FileIcon,
        "Copy API token to clipboard",
        icon_role="copyToken",
    )
    parent.btn_web_token_copy.setAccessibleName("Copy token")
    token_field = _phone_input_with_actions(
        parent.edit_web_token,
        parent.btn_web_token_generate,
        parent.btn_web_token_copy,
    )

    parent.chk_web_show_qr = QtWidgets.QCheckBox("Show QR code")
    parent.chk_web_show_qr.setChecked(True)
    parent.chk_web_show_qr.setToolTip(
        "Show a scannable QR for the phone setup link (recommended on boat PCs)."
    )

    parent.lbl_web_token_qr = QtWidgets.QLabel()
    parent.lbl_web_token_qr.setObjectName("webTokenQr")
    parent.lbl_web_token_qr.setFixedSize(168, 168)
    parent.lbl_web_token_qr.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    parent.lbl_web_token_qr.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    parent.lbl_web_token_qr.setVisible(parent.chk_web_show_qr.isChecked())
    parent.lbl_web_token_qr.setToolTip(
        "Scan with your phone camera while viewing this screen. Encodes the setup link with token."
    )

    qr_field = QtWidgets.QWidget()
    qr_col = QtWidgets.QVBoxLayout(qr_field)
    qr_col.setContentsMargins(0, 0, 0, 0)
    qr_col.setSpacing(8)
    qr_col.addWidget(_phone_field_anchor(parent.chk_web_show_qr), 0)
    qr_col.addWidget(parent.lbl_web_token_qr, 0, QtCore.Qt.AlignmentFlag.AlignLeft)

    phone_form.addRow(
        _phone_form_label(
            "Phone dashboard URL",
            "Must be reachable from the phone (Tailscale 100.x.x.x or LAN). "
            "127.0.0.1 only works on this PC.",
        ),
        phone_url_field,
    )
    phone_form.addRow(
        _phone_form_label(
            "API token",
            "X-Bridge-Token for remote Start/Stop, config, COM unlock, and discovery refresh.",
        ),
        token_field,
    )
    phone_form.addRow("", qr_field)
    phone_lay.addWidget(phone_form_host, 1)

    parent._phone_cards_host = cards_host
    parent._phone_cards_grid = cards_grid
    parent._phone_dashboard_server_card = server_card
    parent._phone_dashboard_phone_card = phone_card
    parent._phone_cards_vertical = False
    cards_grid.addWidget(server_card, 0, 0)
    cards_grid.addWidget(phone_card, 0, 1)
    cards_grid.setColumnStretch(0, 1)
    cards_grid.setColumnStretch(1, 1)
    lay.addWidget(cards_host, 0)
    _wire_web_control_widgets(parent)
    if hasattr(parent, "_sync_web_port_spin_locked"):
        parent._sync_web_port_spin_locked()
    elif hasattr(parent, "_sync_web_port_unlock_chrome"):
        parent._sync_web_port_unlock_chrome()
    if hasattr(parent, "_on_web_show_qr_toggled"):
        parent._on_web_show_qr_toggled(parent.chk_web_show_qr.isChecked())

    lay.addStretch(1)

    scroll = QtWidgets.QScrollArea()
    scroll.setObjectName("phoneDashboardScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setWidget(inner)
    QtCore.QTimer.singleShot(0, lambda: apply_phone_dashboard_responsive(parent))
    return scroll


def build_guide_tab(parent: QtWidgets.QWidget, *, embedded: bool = False) -> QtWidgets.QWidget:
    """Connection workflow reference (UDP/TCP/checklists) — no web controls here."""
    inner = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(inner)
    margins = 0 if embedded else 10
    lay.setContentsMargins(margins, margins, margins, margins)
    lay.setSpacing(8)

    if not embedded:
        header = QtWidgets.QLabel("Serial Link — connection help")
        header.setObjectName("tabHint")
        lay.addWidget(header)

        intro = QtWidgets.QLabel(
            "Step-by-step UDP/TCP workflows for Serial Link. "
            "Open \u2018Start here\u2019 if you are stuck; use the doc buttons for the full offline walkthrough."
        )
        intro.setWordWrap(True)
        intro.setObjectName("tabNote")
        lay.addWidget(intro)

    doc_note = QtWidgets.QLabel(
        "Use the tabs below for quick steps, or open the full offline manuals."
    )
    doc_note.setObjectName("tabNote")
    doc_note.setWordWrap(True)
    lay.addWidget(doc_note)
    doc_row = QtWidgets.QHBoxLayout()
    doc_row.setSpacing(8)

    def _open_doc(rel: str, title: str) -> None:
        show_bundled_doc(parent, rel, window_title=title)

    for label, rel in (
        ("Getting started…", "docs/GETTING_STARTED.md"),
        ("Operator guide…", "docs/OPERATOR_GUIDE.md"),
        ("NORBIT DCT…", "docs/NORBIT_DCT.md"),
    ):
        btn = QtWidgets.QPushButton(label)
        btn.setToolTip(f"Open {rel} in this app (offline)")
        btn.clicked.connect(lambda _checked=False, r=rel, t=label: _open_doc(r, t))
        doc_row.addWidget(btn)
    doc_row.addStretch(1)
    lay.addLayout(doc_row)

    phone_ptr = QtWidgets.QLabel(
        "Phone dashboard, Web API, token, and QR: open Tools \u2192 Phone."
    )
    phone_ptr.setWordWrap(True)
    phone_ptr.setObjectName("tabNote")
    if embedded:
        phone_ptr.hide()
    else:
        lay.addWidget(phone_ptr)

    tabs = QtWidgets.QTabWidget()
    tabs.setObjectName("guideTabWidget")
    tabs.setDocumentMode(True)

    for tab_title, html in (
        ("Start here", _GUIDE_START),
        ("UDP", _GUIDE_UDP),
        ("TCP Client", _GUIDE_TCP_CLIENT),
        ("TCP Server", _GUIDE_TCP_SERVER),
        ("Checklist", _GUIDE_CHECKLIST),
    ):
        browser = QtWidgets.QTextBrowser()
        browser.setObjectName("guideTextBrowser")
        browser.setOpenExternalLinks(False)
        browser.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        browser.document().setDefaultStyleSheet(_GUIDE_CSS)
        browser.setHtml(html)
        tabs.addTab(browser, tab_title)

    lay.addWidget(tabs, 1)

    if embedded:
        return inner

    scroll = QtWidgets.QScrollArea()
    scroll.setObjectName("guideTabScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setWidget(inner)
    return scroll


def build_send_tab(parent: QtWidgets.QWidget, *, embedded: bool = False) -> QtWidgets.QWidget:
    """Manual NMEA inject (Tools → Inject)."""
    host = QtWidgets.QWidget()
    margins = 0 if embedded else 14
    lay = QtWidgets.QVBoxLayout(host)
    lay.setContentsMargins(margins, margins, margins, margins)
    lay.setSpacing(10)

    if not embedded:
        hint = QtWidgets.QLabel(
            "Inject test NMEA while the bridge is Running (Tools → Inject). "
            "Use Send → serial for bench (COM7 → com0com → watch COM12). "
            "For a local shell, use Tools → Terminal. Gray placeholder text is not sent."
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

    if embedded:
        edit_host = QtWidgets.QWidget()
        edit_host.setObjectName("sendEditHost")
        edit_lay = QtWidgets.QVBoxLayout(edit_host)
        edit_lay.setContentsMargins(0, 0, 0, 0)
        edit_lay.setSpacing(8)
        edit_lay.addWidget(parent.send_edit, 1)
        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(8)
        parent.btn_insert_sample = QtWidgets.QPushButton("Insert sample GGA")
        parent.btn_send_ser = QtWidgets.QPushButton("Send → serial")
        parent.btn_send_net = QtWidgets.QPushButton("Send → network")
        parent.btn_send_both = QtWidgets.QPushButton("Send → both")
        for btn in (
            parent.btn_send_ser,
            parent.btn_send_net,
            parent.btn_send_both,
        ):
            btn.setMinimumWidth(110)
        action_row.addStretch(1)
        action_row.addWidget(parent.btn_insert_sample, 0)
        action_row.addWidget(parent.btn_send_ser, 0)
        action_row.addWidget(parent.btn_send_net, 0)
        action_row.addWidget(parent.btn_send_both, 0)
        edit_lay.addLayout(action_row)
        lay.addWidget(edit_host, 1)
        return host

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

    if not embedded:
        note = QtWidgets.QLabel(
            "If nothing moves: confirm the status bar shows COM open and the network line matches your mode. "
            "While running, the right end shows sentence rates (↓ ↑ Hz), plain-language transport health "
            "(no fake 0/0 pairs), and session totals — enable verbose log to see each line."
        )
        note.setWordWrap(True)
        note.setObjectName("tabNote")
        lay.addWidget(note)

    if embedded:
        return host
    return _scrollable(host)



def _mount_automated_checks_ui(
    parent: QtWidgets.QWidget,
    lay: QtWidgets.QVBoxLayout,
    *,
    expand_output: bool = False,
    embedded: bool = False,
) -> None:
    """Automated bench/dev checks — shared by Field diagnostics card and Modern Checks page."""
    if not embedded:
        intro = QtWidgets.QLabel(
            "Runs the same Python helpers as the command line. Output fills the panel below. "
            "Start the bridge first for live wire tests."
        )
        intro.setWordWrap(True)
        intro.setObjectName("tabNote")
        lay.addWidget(intro)

    def _add_group(title: str, buttons: list[QtWidgets.QPushButton]) -> None:
        frame = QtWidgets.QFrame()
        frame.setObjectName("modernChecksGroup")
        gl = QtWidgets.QVBoxLayout(frame)
        gl.setContentsMargins(12, 10, 12, 10)
        gl.setSpacing(8)
        hdr = QtWidgets.QLabel(title)
        hdr.setObjectName("modernChecksGroupTitle")
        gl.addWidget(hdr)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        for btn in buttons:
            row.addWidget(btn)
        row.addStretch(1)
        gl.addLayout(row)
        lay.addWidget(frame)

    parent.btn_bench_pair_setup = QtWidgets.QPushButton("Bench pair setup…")
    parent.btn_bench_pair_setup.setObjectName("btnBenchPairSetupDiag")
    parent.btn_bench_pair_setup.setToolTip(
        "Opens docs/OPERATOR_GUIDE.md (bench section 5) and runs com_free then check_setup — "
        "same checks as preflight_bench.bat. Install com0com from the guide first."
    )
    parent.btn_bench_pair_setup.clicked.connect(parent._open_bench_pair_setup)
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

    parent.btn_diag_network_bench = QtWidgets.QPushButton("Network bench (auto)")
    parent.btn_diag_network_bench.setObjectName("btnDiagNetworkBench")
    parent.btn_diag_network_bench.setToolTip(
        "Runs bench_network_automation.py: headless zero-drop UDP + TCP reconnect when the "
        "bench UDP port is free; otherwise a short live burst to the running bridge."
    )
    parent.btn_diag_fanout_bench = QtWidgets.QPushButton("Fan-out bench (auto)")
    parent.btn_diag_fanout_bench.setObjectName("btnDiagFanoutBench")
    parent.btn_diag_fanout_bench.setToolTip(
        "Runs bench_fanout_automation.py: headless two-peer fan-out + last-peer-only when UDP "
        "port is free; live registers two peers when the bridge is already Running."
    )
    parent.btn_diag_udp = QtWidgets.QPushButton("UDP sample burst (2.5 s)")
    parent.btn_diag_udp.setObjectName("btnDiagUdpBurst")
    parent.btn_diag_udp.setToolTip(
        "Runs nmea_static_sample.py toward the bench preset UDP target. "
        "Bridge should be Running (UDP listen) to see lines in Activity."
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
    parent.btn_diag_stop.setObjectName("modernChecksStopBtn")
    parent.btn_diag_stop.setEnabled(False)
    parent.btn_diag_stop.setToolTip("Kill the running helper process.")
    parent.btn_diag_clear = QtWidgets.QPushButton("Clear output")

    if embedded:
        _add_group(
            "Checklists",
            [
                parent.btn_bench_pair_setup,
                parent.btn_diag_verify,
                parent.btn_diag_setup,
                parent.btn_diag_setup_prod,
            ],
        )
        _add_group(
            "Automation & stress",
            [
                parent.btn_diag_network_bench,
                parent.btn_diag_fanout_bench,
                parent.btn_diag_udp,
                parent.btn_diag_tcp_stress,
                parent.btn_diag_tcp_demo,
                parent.btn_diag_stop,
                parent.btn_diag_clear,
            ],
        )
    else:
        btn_row1 = QtWidgets.QHBoxLayout()
        for b in (
            parent.btn_bench_pair_setup,
            parent.btn_diag_verify,
            parent.btn_diag_setup,
            parent.btn_diag_setup_prod,
        ):
            btn_row1.addWidget(b)
        btn_row1.addStretch(1)
        lay.addLayout(btn_row1)

        btn_row2 = QtWidgets.QHBoxLayout()
        for b in (
            parent.btn_diag_network_bench,
            parent.btn_diag_fanout_bench,
            parent.btn_diag_udp,
            parent.btn_diag_tcp_stress,
            parent.btn_diag_tcp_demo,
            parent.btn_diag_stop,
            parent.btn_diag_clear,
        ):
            btn_row2.addWidget(b)
        btn_row2.addStretch(1)
        lay.addLayout(btn_row2)

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
    lay.addLayout(cap_row)

    parent.chk_diag_mirror_log = QtWidgets.QCheckBox("Mirror output lines to Activity")
    parent.chk_diag_mirror_log.setToolTip(
        "When checked, each non-empty output line is also appended to the Activity panel."
    )
    lay.addWidget(parent.chk_diag_mirror_log)

    parent.diag_status_label = QtWidgets.QLabel("Idle — pick a check above.")
    parent.diag_status_label.setWordWrap(True)
    parent.diag_status_label.setObjectName("tabHint")
    lay.addWidget(parent.diag_status_label)

    parent.diag_output = QtWidgets.QPlainTextEdit()
    parent.diag_output.setReadOnly(True)
    parent.diag_output.setObjectName("diagOutput")
    parent.diag_output.setMaximumBlockCount(12_000)
    from ui.fonts import monospace_ui_font

    parent.diag_output.setFont(monospace_ui_font())
    if expand_output:
        parent.diag_output.setMinimumHeight(200)
        parent.diag_output.setMaximumHeight(_WIDGET_SIZE_MAX)
        parent.diag_output.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        lay.addWidget(parent.diag_output, 1)
    else:
        parent.diag_output.setMinimumHeight(72)
        parent.diag_output.setMaximumHeight(120)
        parent.diag_output.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        lay.addWidget(parent.diag_output)

    parent._diag_run_buttons = [
        parent.btn_diag_verify,
        parent.btn_diag_setup,
        parent.btn_diag_setup_prod,
        parent.btn_diag_network_bench,
        parent.btn_diag_fanout_bench,
        parent.btn_diag_udp,
        parent.btn_diag_tcp_stress,
        parent.btn_diag_tcp_demo,
        parent.btn_diag_capacity,
    ]
    parent.btn_diag_verify.clicked.connect(parent._diag_run_verify_all)
    parent.btn_diag_setup.clicked.connect(parent._diag_run_check_setup)
    parent.btn_diag_setup_prod.clicked.connect(parent._diag_run_check_setup_production)
    parent.btn_diag_network_bench.clicked.connect(parent._diag_run_network_bench)
    parent.btn_diag_fanout_bench.clicked.connect(parent._diag_run_fanout_bench)
    parent.btn_diag_udp.clicked.connect(parent._diag_run_udp_sample)
    parent.btn_diag_tcp_stress.clicked.connect(parent._diag_run_tcp_stress)
    parent.btn_diag_tcp_demo.clicked.connect(parent._diag_run_tcp_demo)
    parent.btn_diag_capacity.clicked.connect(parent._diag_run_capacity_probe)
    parent.btn_diag_stop.clicked.connect(parent._diag_stop)
    parent.btn_diag_clear.clicked.connect(parent.diag_output.clear)


def _modern_tools_section_title(text: str) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text)
    lbl.setObjectName("modernToolsSectionTitle")
    return lbl


def _modern_flat_page(
    object_name: str,
    headline: str,
    *,
    subtitle: str = "",
    icon: str = "",
    header_tone: str = "",
) -> tuple[QtWidgets.QWidget, QtWidgets.QVBoxLayout]:
    host = QtWidgets.QWidget()
    host.setObjectName(object_name)
    outer = QtWidgets.QVBoxLayout(host)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    header = QtWidgets.QFrame()
    header.setObjectName("modernToolsPageHeader")
    if header_tone:
        header.setProperty("headerTone", header_tone)
    h_lay = QtWidgets.QVBoxLayout(header)
    h_lay.setContentsMargins(20, 18, 20, 14)
    h_lay.setSpacing(6)

    title_row = QtWidgets.QHBoxLayout()
    title_row.setSpacing(10)
    if icon:
        icon_lbl = QtWidgets.QLabel(icon)
        icon_lbl.setObjectName("modernToolsPageIcon")
        title_row.addWidget(icon_lbl, 0, QtCore.Qt.AlignmentFlag.AlignTop)
    title = QtWidgets.QLabel(headline)
    title.setObjectName("modernToolsPageTitle")
    title_row.addWidget(title, 1)
    h_lay.addLayout(title_row)

    if subtitle:
        hint = QtWidgets.QLabel(subtitle)
        hint.setWordWrap(True)
        hint.setObjectName("modernToolsPageSubtitle")
        h_lay.addWidget(hint)

    outer.addWidget(header)

    card = QtWidgets.QFrame()
    card.setObjectName("modernToolsContentCard")
    lay = QtWidgets.QVBoxLayout(card)
    lay.setContentsMargins(18, 16, 18, 18)
    lay.setSpacing(12)
    outer.addWidget(card, 1)
    return host, lay


def _modern_tools_inline_section(title: str) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(title)
    lbl.setObjectName("modernToolsInlineSection")
    return lbl


def _modern_tools_section_sep() -> QtWidgets.QFrame:
    sep = QtWidgets.QFrame()
    sep.setObjectName("modernToolsSectionSep")
    sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    sep.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
    return sep


def _modern_live_status_label() -> QtWidgets.QLabel:
    from ui.modern_live_status import create_modern_live_status_label

    return create_modern_live_status_label()


def _mount_black_box_ui(parent: QtWidgets.QWidget, lay: QtWidgets.QVBoxLayout) -> None:
    parent.lbl_black_box_live_status = _modern_live_status_label()
    lay.addWidget(parent.lbl_black_box_live_status)
    parent.chk_local_backup = QtWidgets.QCheckBox(
        "Save raw COM data to local .raw file while bridge runs"
    )
    parent.chk_local_backup.setToolTip(
        "Writes raw COM traffic (network→COM and COM→network) to backup_*.raw with immediate disk flush. "
        "Continues even if UDP/TCP fails — independent of the rotating NMEA file log."
    )
    lay.addWidget(parent.chk_local_backup)
    from ui.local_backup_settings import mount_local_backup_location_row

    mount_local_backup_location_row(parent, lay, show_session_file=False)
    backup_note = QtWidgets.QLabel(
        "One new backup_*.raw file per Start (inside the folder above). Survey UDP→COM traffic is "
        "included. Permission or disk-full errors disable backup for that session without stopping the bridge."
    )
    backup_note.setWordWrap(True)
    backup_note.setObjectName("tabNote")
    lay.addWidget(backup_note)
    if hasattr(parent, "_restore_local_backup_prefs_ui"):
        parent.chk_local_backup.toggled.connect(parent._save_local_backup_pref)
    if hasattr(parent, "_refresh_tools_page_status"):
        parent.chk_local_backup.toggled.connect(lambda *_: parent._refresh_tools_page_status())


def _mount_file_log_ui(parent: QtWidgets.QWidget, lay: QtWidgets.QVBoxLayout) -> None:
    parent.lbl_file_log_live_status = _modern_live_status_label()
    lay.addWidget(parent.lbl_file_log_live_status)
    parent.chk_file_log = QtWidgets.QCheckBox("Write NMEA traffic to file while bridge runs")
    parent.chk_file_log.setToolTip(
        "Appends each bridged line to the path below. Separate from the Activity panel."
    )
    lay.addWidget(parent.chk_file_log)
    path_row = QtWidgets.QHBoxLayout()
    parent.file_log_path = QtWidgets.QLineEdit(str(Path.home() / "bridge_survey.log"))
    parent.file_log_path.setPlaceholderText("Path to .log file")
    parent.file_log_path.setToolTip(
        "Active log file. When it fills up, it is renamed .log.1, .log.2, …"
    )
    parent.btn_browse = QtWidgets.QPushButton("Browse…")
    path_row.addWidget(parent.file_log_path, 1)
    path_row.addWidget(parent.btn_browse)
    lay.addLayout(path_row)
    size_row = QtWidgets.QHBoxLayout()
    size_row.addWidget(QtWidgets.QLabel("Roll at:"))
    parent.cmb_file_log_mb = QtWidgets.QComboBox()
    for mb in (10, 25, 50, 100):
        parent.cmb_file_log_mb.addItem(f"{mb} MB", mb)
    parent.cmb_file_log_mb.setToolTip("Start a new log file when the active file reaches this size.")
    size_row.addWidget(parent.cmb_file_log_mb, 1)
    size_row.addWidget(QtWidgets.QLabel("Keep old files:"))
    parent.cmb_file_log_backups = QtWidgets.QComboBox()
    parent.cmb_file_log_backups.addItem("None — one file only", 0)
    for n in (3, 5, 10):
        parent.cmb_file_log_backups.addItem(str(n), n)
    parent.cmb_file_log_backups.setToolTip(
        "None: when the log fills, the same file is cleared and reused (~one file on disk). "
        "Otherwise keep that many rotated copies (e.g. .log.1, .log.2); oldest are deleted."
    )
    size_row.addWidget(parent.cmb_file_log_backups, 0)
    lay.addLayout(size_row)
    parent.lbl_file_log_retention = QtWidgets.QLabel(file_log_retention_hint(10, 5))
    parent.lbl_file_log_retention.setWordWrap(True)
    parent.lbl_file_log_retention.setObjectName("tabNote")
    lay.addWidget(parent.lbl_file_log_retention)
    if hasattr(parent, "_refresh_file_log_retention_hint"):
        parent.cmb_file_log_mb.currentIndexChanged.connect(parent._refresh_file_log_retention_hint)
        parent.cmb_file_log_backups.currentIndexChanged.connect(parent._refresh_file_log_retention_hint)
    if hasattr(parent, "_refresh_tools_page_status"):
        parent.chk_file_log.toggled.connect(lambda *_: parent._refresh_tools_page_status())
        parent.file_log_path.textChanged.connect(lambda *_: parent._refresh_tools_page_status())


def _mount_activity_clear_ui(parent: QtWidgets.QWidget, lay: QtWidgets.QVBoxLayout) -> None:
    from ui.controls import create_log_panel

    lay.addWidget(create_log_panel(parent, show_toggle=False, show_header=True), 1)


def build_modern_black_box_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    host, lay = _modern_flat_page(
        "modernBlackBoxPage",
        "Black box",
        subtitle="Crash-safe raw COM capture — one .raw file per bridge session.",
        icon="💾",
    )
    _mount_black_box_ui(parent, lay)
    lay.addStretch(1)
    return host


def build_modern_file_log_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    host, lay = _modern_flat_page(
        "modernFileLogPage",
        "File log",
        subtitle="Rotating NMEA log on disk — separate from the on-screen Activity panel.",
        icon="📄",
    )
    _mount_file_log_ui(parent, lay)
    note = QtWidgets.QLabel("Line format: PC time | GPS UTC | direction | NMEA sentence.")
    note.setWordWrap(True)
    note.setObjectName("tabNote")
    lay.addWidget(note)
    lay.addStretch(1)
    return host


def build_modern_activity_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tools_pages import build_modern_activity_body

    host, lay = _modern_flat_page(
        "modernActivityToolsPage",
        "Activity",
        subtitle="On-screen wire-tap housekeeping — does not affect disk logs.",
        icon="📋",
    )
    lay.addWidget(build_modern_activity_body(parent), 1)
    return host


def build_modern_presets_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.tools_pages import build_modern_presets_body

    host, lay = _modern_flat_page(
        "modernPresetsPage",
        "Presets",
        subtitle="Named COM, network, and NMEA setups — Load before Start, Save after changes.",
        icon="⚙",
    )
    lay.addWidget(build_modern_presets_body(parent), 1)
    return host


def build_modern_nmea_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.nmea_settings import build_modern_nmea_settings

    host, lay = _modern_flat_page(
        "modernNmeaPage",
        "NMEA",
        subtitle="How the bridge treats incoming data on the next Start — passthrough, filtered, or raw.",
        icon="📡",
    )
    lay.addWidget(build_modern_nmea_settings(parent), 1)
    return host


def build_modern_hub_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Modern Tools → Hub: full-height Connection Hub (COM + UDP discovery cards)."""
    from ui.connection_hub import ConnectionHubWidget

    host, lay = _modern_flat_page(
        "modernHubTab",
        "Hub",
        subtitle=(
            "Discover COM ports and network paths — click a tile to fill Control before Start. "
            "Blue border = hub pick for Start."
        ),
        icon="🛰",
    )
    hub = ConnectionHubWidget(standalone=True, show_page_header=False)
    hub.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Expanding,
    )
    hub.attach_bridge_window(parent)
    parent.connection_hub = hub
    lay.addWidget(hub, 1)
    scroll = getattr(hub, "_card_scroll", None)
    if scroll is not None:
        scroll.setMinimumHeight(0)
        scroll.setMaximumHeight(16777215)
        scroll.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
    return host


def build_modern_phone_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    host, lay = _modern_flat_page(
        "modernPhonePage",
        "Dashboard",
        subtitle="Web dashboard, token, and QR for remote Start/Stop from a phone.",
        icon="📱",
    )
    scroll = build_phone_dashboard_tab(parent)
    lay.addWidget(scroll, 1)
    return host


def build_modern_automated_checks_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Modern Tools → Checks: full-height automated checks (no nested scroll/card)."""
    host, lay = _modern_flat_page(
        "modernChecksPage",
        "Checks",
        subtitle="Bench and developer scripts — not required for normal survey work.",
        icon="🧪",
        header_tone="bench",
    )
    _mount_automated_checks_ui(parent, lay, expand_output=True, embedded=True)
    return host


def sort_modern_nav_by_saved_order(
    items: list,
    visible_order: list[str],
    *,
    tier: bool = False,
) -> list:
    """Sort Modern nav leaves or dropdown tiers by UI editor / saved tools_tabs order."""
    rank = {lbl: i for i, lbl in enumerate(visible_order)}

    def leaf_rank(item: tuple) -> int:
        return rank.get(item[1], len(visible_order) + 1)

    def dropdown_rank(item: tuple) -> int:
        children = item[3]
        child_ranks = [rank[c[1]] for c in children if c[1] in rank]
        return min(child_ranks) if child_ranks else len(visible_order) + 1

    key_fn = dropdown_rank if tier else leaf_rank
    return sorted(items, key=key_fn)


def build_modern_tools_nav_tiers() -> tuple[
    list[tuple[str, str, str]],
    list[tuple[str, str, str, list[tuple[str, str, str]]]],
]:
    """Top chip rail tiers: 4 primary leaves + 2 dropdown groups."""
    leaves = [
        ("control", "Control", "🎛"),
        ("presets", "Presets", "⚙"),
        ("hub", "Hub", "🛰"),
        ("nmea", "NMEA", "📡"),
    ]
    dropdowns = [
        (
            "logging",
            "Logging",
            "📋",
            [
                ("activity", "Activity", "📋"),
                ("black_box", "Black box", "💾"),
                ("file_log", "File log", "📄"),
            ],
        ),
        (
            "bench_tools",
            "Bench Tools",
            "🧪",
            [
                ("phone", "Dashboard", "📱"),
                ("inject", "Inject", "💉"),
                ("terminal", "Terminal", "⌨"),
                ("checks", "Checks", "🧪"),
            ],
        ),
    ]
    return leaves, dropdowns


def build_modern_tools_nav_groups() -> list[tuple[str, list[tuple[str, str, str]]]]:
    """Modern sidebar groups: Control | Setup | Logging | Bench Tools."""
    return [
        (
            "Control",
            [
                ("control", "Control", "🎛"),
            ],
        ),
        (
            "Setup",
            [
                ("presets", "Presets", "⚙"),
                ("hub", "Hub", "🛰"),
                ("nmea", "NMEA", "📡"),
            ],
        ),
        (
            "Logging",
            [
                ("activity", "Activity", "📋"),
                ("black_box", "Black box", "💾"),
                ("file_log", "File log", "📄"),
            ],
        ),
        (
            "Bench Tools",
            [
                ("phone", "Dashboard", "📱"),
                ("inject", "Inject", "💉"),
                ("terminal", "Terminal", "⌨"),
                ("checks", "Checks", "🧪"),
            ],
        ),
    ]


def build_modern_tools_nav() -> list[tuple[str, str, str]]:
    """Modern Tools sidebar/chip leaves: flat (section_id, label, icon) in display order."""
    out: list[tuple[str, str, str]] = []
    for _group, items in build_modern_tools_nav_groups():
        out.extend(items)
    return out


def build_modern_tools_all_pages() -> list[tuple[str, str, str]]:
    """All stack pages including header-only Guide."""
    return [*build_modern_tools_nav(), ("guide", "Guide", "📖")]


def build_modern_inject_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    host, lay = _modern_flat_page(
        "modernInjectPage",
        "Inject",
        subtitle="Send test NMEA or raw bytes out the COM port while the bridge runs.",
        icon="💉",
    )
    lay.addWidget(build_send_tab(parent, embedded=True), 1)
    return host


def build_modern_terminal_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.system_terminal import build_system_terminal_tab

    host, lay = _modern_flat_page(
        "modernTerminalPage",
        "Terminal",
        subtitle="Local shell for bench scripts and ping — separate from bridge inject.",
        icon="⌨",
    )
    lay.addWidget(build_system_terminal_tab(parent, embedded=True), 1)
    return host


def build_modern_guide_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    from ui.operator_guide import build_operator_guide_panel

    host, lay = _modern_flat_page(
        "modernGuidePage",
        "Guide",
        subtitle="Learn the workflow in plain language — pick a path, follow the steps, jump to the right tab.",
        icon="📖",
    )
    lay.addWidget(build_operator_guide_panel(parent), 1)
    return host


def build_diagnostics_tab(
    parent: QtWidgets.QWidget,
    *,
    skip_hub: bool = False,
    card_keys: frozenset[str] | None = None,
) -> QtWidgets.QWidget:
    """File log + on-screen log options.

    Args:
            skip_hub: When True, the ConnectionHubWidget section is omitted.
            Use this in layouts (e.g. Modern) that already provide Hub under
            Tools so the widget is not created twice.
        card_keys: When set, only build these collapsible cards (Modern Tools split).
    """
    full_panel = card_keys is None

    def _want(key: str) -> bool:
        return full_panel or key in card_keys  # type: ignore[operator]
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

    if full_panel:
        hint = QtWidgets.QLabel(
            "Optional rotating file log for survey records. "
            "The main live log (Log tab in Standard, Activity in Modern, or above the strip in Field) "
            "is separate — use On-screen log below to clear it."
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

    if full_panel and not skip_hub:
        from ui.connect_panels import mount_connection_hub_on_diagnostics

        mount_connection_hub_on_diagnostics(parent, lay)

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

    if _want("local_backup"):
        lv = _add_collapsible_card(
            splitter,
            "Local black-box backup",
            start_open=_card_open("local_backup", True),
            on_toggled=lambda on: _persist_card("local_backup", on),
        )
        _register_card("local_backup")
        _mount_black_box_ui(parent, lv)

    if _want("file_log"):
        fv = _add_collapsible_card(
            splitter,
            "Rotating file log",
            start_open=_card_open("file_log", False),
            on_toggled=lambda on: _persist_card("file_log", on),
        )
        _register_card("file_log")
        _mount_file_log_ui(parent, fv)

    if _want("screen_log"):
        sv = _add_collapsible_card(
            splitter,
            "On-screen log",
            start_open=_card_open("screen_log", False),
            on_toggled=lambda on: _persist_card("screen_log", on),
        )
        _register_card("screen_log")
        _mount_activity_clear_ui(parent, sv)

    if _want("automated_checks"):
        bv = _add_collapsible_card(
            splitter,
            "Automated checks (runs on this PC)",
            start_open=_card_open("automated_checks", False),
            on_toggled=lambda on: _persist_card("automated_checks", on),
        )
        _register_card("automated_checks")
        _mount_automated_checks_ui(parent, bv, expand_output=False)

    merged_cards = dict(getattr(parent, "_diag_card_widgets", {}) or {})
    merged_cards.update(card_widgets)
    parent._diag_card_widgets = merged_cards
    if full_panel:
        parent._diag_cards_splitter = splitter
        parent._diag_cards_layout = lay
        if hasattr(parent, "_apply_diag_card_order"):
            parent._apply_diag_card_order()
        else:
            _apply_diag_splitter_sizes(parent)
    else:
        _apply_diag_splitter_sizes(parent)

    return _scrollable(host)

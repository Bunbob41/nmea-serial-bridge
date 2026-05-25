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
    "automated_checks",
    "file_log",
    "screen_log",
    "traffic_quality",
]

_DEFAULT_DIAG_CARD_HEIGHTS: dict[str, int] = {
    "file_log": 200,
    "screen_log": 64,
    "traffic_quality": 120,
    "automated_checks": 280,
}

_DIAG_CARD_EXPANDED_CAP: dict[str, int] = {
    "file_log": 360,
    "screen_log": 120,
    "traffic_quality": 200,
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


_GUIDE_CSS = """
body  { font-family: sans-serif; font-size: 13px; margin: 0; padding: 0; }
h2    { font-size: 15px; font-weight: bold; margin: 0 0 4px 0; }
h3    { font-size: 13px; font-weight: bold; margin: 10px 0 2px 0; }
p     { margin: 4px 0 8px 0; }
ol    { margin: 4px 0 8px 16px; padding: 0; }
ul    { margin: 2px 0 4px 20px; padding: 0; }
li    { margin-bottom: 3px; }
hr    { border: none; border-top: 1px solid #555; margin: 10px 0; }
code  { background: #2a2a2a; color: #e8e8e8; padding: 1px 4px; border-radius: 3px; font-size: 12px; }
.note { color: #999; font-style: italic; margin-top: 6px; }
"""

_GUIDE_UDP = """
<h2>Method 1 — UDP Flow (Point-to-Point / Broadcast)</h2>
<p><em>Best for fast, connectionless data streams to a specific machine or local software
(e.g. bench testing, MissionPlanner, local chart plotter).</em></p>
<hr/>
<h3>How to Configure</h3>
<ol>
  <li>Open the main <b>Tools</b> tab (Standard) or <b>Tools</b> drawer (Field) and select <b>Presets</b>.</li>
  <li>Click <b>Save as…</b> to create a new named preset (or edit fields and <b>Save</b>).</li>
  <li>Name your preset (e.g. <em>"Bench UDP Test"</em>).</li>
  <li><b>Serial Configuration:</b>
    <ul>
      <li>Select the target <b>COM Port</b> (e.g. COM7).</li>
      <li>Set the <b>Baud Rate</b> (e.g. 115200).</li>
    </ul>
  </li>
  <li><b>Network Configuration (UDP):</b>
    <ul>
      <li>Set Protocol to <b>UDP Remote</b> or <b>UDP Listen</b>.</li>
      <li>Set <b>Target IP:</b> the IP address receiving the data
          (use <code>127.0.0.1</code> for local software).</li>
      <li>Set <b>Target Port:</b> the port the receiving software listens on
          (e.g. <code>10110</code>).</li>
    </ul>
  </li>
  <li>Click <b>Save</b> or <b>Save as…</b>.</li>
  <li>Return to the <b>Connect</b> tab: confirm <b>Serial &amp; network</b> (connection hub or manual fields),
      then <b>Start bridge</b> in the <b>Run bridge</b> panel.</li>
</ol>
<p class="note">UDP Listen mode tracks every sender that transmits to your port and can
fan-out replies to all of them (toggle the <em>Fan-out to all UDP peers</em> checkbox).</p>
"""

_GUIDE_TCP_CLIENT = """
<h2>Method 2 — TCP Client Flow (Connecting Outward)</h2>
<p><em>Best for connecting your local serial hardware to an established remote server.</em></p>
<hr/>
<h3>How to Configure</h3>
<ol>
  <li>Open the main <b>Tools</b> tab (Standard) or <b>Tools</b> drawer (Field) and select <b>Presets</b>.</li>
  <li>Click <b>Save as…</b> to create a new named preset (or edit fields and <b>Save</b>).</li>
  <li>Name your preset (e.g. <em>"Remote Server Link"</em>).</li>
  <li><b>Serial Configuration:</b>
    <ul>
      <li>Select the target <b>COM Port</b>.</li>
      <li>Set the <b>Baud Rate</b>.</li>
    </ul>
  </li>
  <li><b>Network Configuration (TCP Client):</b>
    <ul>
      <li>Set Protocol to <b>TCP Client</b>.</li>
      <li>Set <b>Server IP:</b> the exact IP address of the remote machine.</li>
      <li>Set <b>Server Port:</b> the port the remote server has opened for you.</li>
    </ul>
  </li>
  <li>Click <b>Save</b> or <b>Save as…</b>.</li>
  <li>Return to <b>Connect</b> and click <b>Start bridge</b>.
      The app will actively attempt to connect to the remote server.</li>
</ol>
<p class="note">The bridge retries the connection automatically if the server drops.
Watch the Network chip in the status bar for connection state.</p>
"""

_GUIDE_TCP_SERVER = """
<h2>Method 3 — TCP Server Flow (Hosting Locally)</h2>
<p><em>Best for allowing external software or remote machines to connect to your local
serial hardware.</em></p>
<hr/>
<h3>How to Configure</h3>
<ol>
  <li>Open the main <b>Tools</b> tab (Standard) or <b>Tools</b> drawer (Field) and select <b>Presets</b>.</li>
  <li>Click <b>Save as…</b> to create a new named preset (or edit fields and <b>Save</b>).</li>
  <li>Name your preset (e.g. <em>"Local Host Access"</em>).</li>
  <li><b>Serial Configuration:</b>
    <ul>
      <li>Select the target <b>COM Port</b>.</li>
      <li>Set the <b>Baud Rate</b>.</li>
    </ul>
  </li>
  <li><b>Network Configuration (TCP Server):</b>
    <ul>
      <li>Set Protocol to <b>TCP Server</b>.</li>
      <li>Set <b>Listen IP:</b> use <code>0.0.0.0</code> to accept connections from any
          machine, or <code>127.0.0.1</code> to restrict to this computer only.</li>
      <li>Set <b>Listen Port:</b> choose an open port (e.g. <code>10110</code>).
          Ensure this port is not blocked by your firewall.</li>
    </ul>
  </li>
  <li>Click <b>Save</b> or <b>Save as…</b>.</li>
  <li>Return to <b>Connect</b> and click <b>Start bridge</b>.
      The app will listen and wait for a client to connect.</li>
</ol>
<p class="note">Only one TCP client can connect at a time in server mode. The status bar
Network chip shows the connected client address once a connection is established.</p>
"""

_GUIDE_CHECKLIST = """
<h2>Technical Verification Checklist</h2>
<p><em>Verify these fields before starting the bridge to avoid silent data corruption.</em></p>
<hr/>
<ul>
  <li><b>COM Port:</b> must be a valid local identifier (COM1–256 on Windows,
      <code>/dev/tty…</code> on Linux). Use the Refresh button if it does not appear.</li>
  <li><b>Baud Rate:</b> must match the physical hardware exactly —
      a mismatch produces garbled NMEA sentences without an error.</li>
  <li><b>Target / Listen IP:</b> must be a valid IPv4 address (<code>X.X.X.X</code>).</li>
  <li><b>Port Numbers:</b> integer between <code>1</code> and <code>65535</code>.
      Avoid ports below <code>1024</code> — they are OS-reserved and may require
      elevated privileges.</li>
  <li><b>Firewall:</b> TCP Server and UDP Listen modes require the chosen port to be
      reachable. Add a Windows Defender inbound rule if external machines cannot connect.</li>
  <li><b>NMEA Mode:</b> use <em>Passthrough</em> for trusted hardware;
      use <em>Strict</em> to drop malformed sentences and track rejects in the status bar.</li>
</ul>
<p class="note">After clicking Start bridge, watch the Serial and Network chips in the
bottom status bar. Green text indicates an active connection; red indicates an error.</p>
"""


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
    lay.setSpacing(10)

    header = QtWidgets.QLabel("Phone dashboard — Web API & QR")
    header.setObjectName("tabHint")
    lay.addWidget(header)

    intro = QtWidgets.QLabel(
        "Control the bridge from a phone browser on Tailscale or survey LAN. "
        "Enable the API, set this PC's reachable URL (not 127.0.0.1 on iPhone), "
        "then scan the QR or copy the setup link."
    )
    intro.setWordWrap(True)
    intro.setObjectName("tabNote")
    lay.addWidget(intro)

    web_box = QtWidgets.QGroupBox("Web control — phone dashboard & API token")
    web_box.setObjectName("connectGroupBox")
    web_box.setMinimumHeight(280)
    web_box.setMinimumWidth(480)
    web_row = QtWidgets.QHBoxLayout(web_box)
    web_row.setSpacing(12)
    web_left = QtWidgets.QWidget()
    web_form = QtWidgets.QFormLayout(web_left)
    web_form.setVerticalSpacing(10)
    web_form.setFieldGrowthPolicy(
        QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
    )
    parent.chk_web_enabled = QtWidgets.QCheckBox("Enable Web API on this PC")
    parent.chk_web_enabled.setToolTip(
        "Starts a local HTTP server (default 127.0.0.1:8765) for /status, /config, and start/stop. "
        "See specs/005-hybrid-ui-webui/quickstart.md."
    )
    from ui.controls import WebPortSpinBox

    parent.spin_web_port = WebPortSpinBox()
    parent.spin_web_port.setRange(1024, 65535)
    parent.spin_web_port.setValue(8765)
    parent.spin_web_port.setAccelerated(True)
    parent.spin_web_port.setToolTip(
        "TCP port for the phone dashboard (/status, /config). "
        "Locked by default — check Unlock port for 10 seconds to change. "
        "Mouse wheel never changes this value (avoids accidental scroll)."
    )
    parent.chk_web_port_unlock = QtWidgets.QCheckBox("Unlock port (10 s)")
    parent.chk_web_port_unlock.setToolTip(
        "Enable the port field for ten seconds so you can type or use the step buttons. "
        "Unchecks automatically; port stays locked otherwise."
    )
    port_row = QtWidgets.QHBoxLayout()
    port_row.setSpacing(8)
    port_row.addWidget(
        parent.spin_web_port,
        0,
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
    )
    port_row.addWidget(parent.chk_web_port_unlock, 1)
    port_host = QtWidgets.QWidget()
    port_host.setLayout(port_row)
    parent.lbl_web_listen = QtWidgets.QLabel()
    parent.lbl_web_listen.setObjectName("tabNote")
    parent.lbl_web_listen.setWordWrap(True)
    parent.chk_web_lan = QtWidgets.QCheckBox("Allow LAN / Tailscale access (binds 0.0.0.0)")
    parent.chk_web_lan.setToolTip(
        "Exposes the web API on all interfaces. Use Windows firewall and the API token below. "
        "Localhost-only is safer on bench PCs."
    )
    parent.edit_web_token = QtWidgets.QLineEdit()
    parent.edit_web_token.setPlaceholderText("Remote control token — generate for LAN/phone")
    parent.edit_web_token.setToolTip(
        "Remote control token (X-Bridge-Token) for Start/Stop and COM changes from your phone. "
        "Copy the setup link (not 127.0.0.1) to the phone dashboard."
    )
    parent.edit_web_token.setClearButtonEnabled(True)
    parent.chk_web_show_qr = QtWidgets.QCheckBox("Show QR")
    parent.chk_web_show_qr.setChecked(True)
    parent.chk_web_show_qr.setToolTip(
        "Display a scannable QR code for the phone setup link (recommended on boat PCs)."
    )
    token_btn_row = QtWidgets.QHBoxLayout()
    parent.btn_web_token_generate = QtWidgets.QPushButton("Generate token")
    parent.btn_web_token_generate.setToolTip("Create a new random API token and save it")
    parent.btn_web_token_copy = QtWidgets.QPushButton("Copy token")
    parent.btn_web_token_copy.setToolTip("Copy API token to clipboard")
    parent.btn_web_copy_setup = QtWidgets.QPushButton("Copy phone setup link")
    parent.btn_web_copy_setup.setToolTip(
        "Copy a one-tap URL for the phone dashboard (opens in mobile browser and saves the token)."
    )
    parent.btn_web_paste_setup = QtWidgets.QPushButton("Paste setup link")
    parent.btn_web_paste_setup.setToolTip(
        "Import token from clipboard — paste a setup link copied on your phone or another device."
    )
    parent.edit_web_phone_url = QtWidgets.QLineEdit()
    parent.edit_web_phone_url.setPlaceholderText(
        "http://100.x.x.x:8765 — Tailscale IP (NOT 127.0.0.1)"
    )
    parent.edit_web_phone_url.setToolTip(
        "Base URL your phone uses in Safari — must be this PC's Tailscale or LAN IP, "
        "not 127.0.0.1. Run tailscale ip -4 on this PC if unsure. Used for QR and setup links."
    )
    parent.btn_web_detect_phone_url = QtWidgets.QPushButton("Detect Tailscale IP")
    parent.btn_web_detect_phone_url.setToolTip(
        "Fill Phone dashboard URL from tailscale ip -4 or local network addresses."
    )
    token_btn_row.addWidget(parent.chk_web_show_qr)
    token_btn_row.addWidget(parent.btn_web_token_generate)
    token_btn_row.addWidget(parent.btn_web_token_copy)
    token_btn_row.addWidget(parent.btn_web_copy_setup)
    token_btn_row.addWidget(parent.btn_web_paste_setup)
    token_btn_row.addStretch(1)
    token_btn_host = QtWidgets.QWidget()
    token_btn_host.setLayout(token_btn_row)
    token_hint = QtWidgets.QLabel(
        "Phone must use this PC's Tailscale IP (100.x.x.x:8765) — 127.0.0.1 will not work on iPhone. "
        "Detect Tailscale IP, then Copy phone setup link or scan QR. Saved in ui_prefs.json."
    )
    token_hint.setObjectName("tabHint")
    token_hint.setWordWrap(True)

    parent.lbl_web_token_qr = QtWidgets.QLabel()
    parent.lbl_web_token_qr.setObjectName("webTokenQr")
    parent.lbl_web_token_qr.setFixedSize(220, 220)
    parent.lbl_web_token_qr.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignCenter
    )
    parent.lbl_web_token_qr.setFrameShape(QtWidgets.QFrame.Shape.Box)
    parent.lbl_web_token_qr.setVisible(parent.chk_web_show_qr.isChecked())
    parent.lbl_web_token_qr.setToolTip(
        "QR encodes a phone setup link — scan from the phone camera while viewing this PC screen."
    )
    qr_side = QtWidgets.QWidget()
    qr_lay = QtWidgets.QVBoxLayout(qr_side)
    qr_lay.setContentsMargins(0, 28, 0, 0)
    qr_lay.addWidget(parent.lbl_web_token_qr, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
    qr_lay.addStretch(1)

    web_form.addRow("", parent.chk_web_enabled)
    web_form.addRow("Port:", port_host)
    web_form.addRow("", parent.lbl_web_listen)
    web_form.addRow("", parent.chk_web_lan)
    phone_url_row = QtWidgets.QHBoxLayout()
    phone_url_row.addWidget(parent.edit_web_phone_url, 1)
    phone_url_row.addWidget(parent.btn_web_detect_phone_url)
    phone_url_host = QtWidgets.QWidget()
    phone_url_host.setLayout(phone_url_row)
    web_form.addRow("Phone dashboard URL:", phone_url_host)
    web_form.addRow("Remote control token:", parent.edit_web_token)
    web_form.addRow("", token_btn_host)
    web_form.addRow("", token_hint)
    web_row.addWidget(web_left, 1)
    web_row.addWidget(qr_side, 0)
    lay.addWidget(web_box, 0)
    _wire_web_control_widgets(parent)
    if hasattr(parent, "_sync_web_port_spin_locked"):
        parent._sync_web_port_spin_locked()
    if hasattr(parent, "_on_web_show_qr_toggled"):
        parent._on_web_show_qr_toggled(parent.chk_web_show_qr.isChecked())

    open_row = QtWidgets.QHBoxLayout()
    parent.btn_web_open_dashboard = QtWidgets.QPushButton("Open dashboard in browser")
    parent.btn_web_open_dashboard.setToolTip(
        "Open the phone dashboard URL in your default browser (uses Phone dashboard URL field)."
    )
    if hasattr(parent, "_on_web_open_dashboard"):
        parent.btn_web_open_dashboard.clicked.connect(parent._on_web_open_dashboard)
    open_row.addWidget(parent.btn_web_open_dashboard)
    open_row.addStretch(1)
    lay.addLayout(open_row)
    lay.addStretch(1)

    scroll = QtWidgets.QScrollArea()
    scroll.setObjectName("phoneDashboardScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setWidget(inner)
    return scroll


def build_guide_tab(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Connection workflow reference (UDP/TCP/checklists) — no web controls here."""
    inner = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(inner)
    lay.setContentsMargins(10, 10, 10, 10)
    lay.setSpacing(8)

    header = QtWidgets.QLabel("Network ↔ COM Bridge — Connection Workflows")
    header.setObjectName("tabHint")
    lay.addWidget(header)

    repo_root = Path(__file__).resolve().parent.parent
    doc_note = QtWidgets.QLabel(
        "Full walkthrough: docs/GETTING_STARTED.md · Operator manual: docs/OPERATOR_GUIDE.md"
    )
    doc_note.setObjectName("tabNote")
    doc_note.setWordWrap(True)
    lay.addWidget(doc_note)
    doc_row = QtWidgets.QHBoxLayout()
    doc_row.setSpacing(8)

    def _open_doc(rel: str, title: str) -> None:
        path = repo_root / rel
        if not path.is_file():
            QtWidgets.QMessageBox.information(
                parent,
                title,
                f"Document not found:\n{path}\n\nSee docs/ in the install or repo folder.",
            )
            return
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(str(path.resolve()))
        )

    for label, rel in (
        ("Getting started…", "docs/GETTING_STARTED.md"),
        ("Operator guide…", "docs/OPERATOR_GUIDE.md"),
        ("NORBIT DCT…", "docs/NORBIT_DCT.md"),
    ):
        btn = QtWidgets.QPushButton(label)
        btn.setToolTip(f"Open {rel}")
        btn.clicked.connect(lambda _checked=False, r=rel, t=label: _open_doc(r, t))
        doc_row.addWidget(btn)
    doc_row.addStretch(1)
    lay.addLayout(doc_row)

    phone_ptr = QtWidgets.QLabel(
        "Phone dashboard, Web API, token, and QR: open Tools → Phone (not this Guide tab)."
    )
    phone_ptr.setWordWrap(True)
    phone_ptr.setObjectName("tabNote")
    lay.addWidget(phone_ptr)

    tabs = QtWidgets.QTabWidget()
    tabs.setObjectName("guideTabWidget")
    tabs.setDocumentMode(True)

    for tab_title, html in (
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

    scroll = QtWidgets.QScrollArea()
    scroll.setObjectName("guideTabScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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
    qa.setMaximumWidth(560)
    qa_wrap = QtWidgets.QWidget()
    qa_wrap_lay = QtWidgets.QVBoxLayout(qa_wrap)
    qa_wrap_lay.setContentsMargins(0, 0, 0, 0)
    qa_wrap_lay.addWidget(qa)
    qa_wrap_lay.addStretch(1)
    qv.addWidget(
        qa_wrap,
        0,
        QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft,
    )

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
        "Opens docs/OPERATOR_GUIDE.md (bench section 5) and runs com_free then check_setup — "
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

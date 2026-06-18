"""Visual operator guide for Modern Tools → Guide (plain language, go-there actions)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.doc_viewer import show_bundled_doc


def _guide_go_tab(parent: QtWidgets.QWidget, tab_name: str) -> None:
    if getattr(parent, "_ui_mode", "") == "modern":
        opener = getattr(parent, "_open_modern_section_by_sid", None)
        if callable(opener):
            from ui.modern import _MODERN_LEGACY_SECTION

            sid = _MODERN_LEGACY_SECTION.get(tab_name.strip(), tab_name.strip().lower())
            opener(sid)
            return
    finder = getattr(parent, "_tab_index_by_name", None)
    tabs = getattr(parent, "_main_tabs", None)
    if not callable(finder) or tabs is None:
        return
    idx = finder(tab_name)
    if idx >= 0:
        tabs.setCurrentIndex(idx)


def _guide_go_tools(parent: QtWidgets.QWidget, section: str) -> None:
    opener = getattr(parent, "_open_modern_tools_section", None)
    if callable(opener):
        opener(section)
        return
    tools_nav = getattr(parent, "_tools_nav", None)
    main_tabs = getattr(parent, "_main_tabs", None)
    if tools_nav is None or main_tabs is None:
        return
    for i in range(main_tabs.count()):
        if main_tabs.tabText(i).strip().lower() == "tools":
            main_tabs.setCurrentIndex(i)
            break
    for row in range(tools_nav.count()):
        item = tools_nav.item(row)
        if item is not None and item.text().strip().lower() == section.replace("_", " "):
            tools_nav.setCurrentRow(row)
            return


def _guide_open_doc(parent: QtWidgets.QWidget, rel: str, title: str) -> None:
    show_bundled_doc(parent, rel, window_title=title)


def _guide_flow_diagram(stages: list[str]) -> QtWidgets.QWidget:
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(6)
    host = QtWidgets.QWidget()
    host.setObjectName("guideFlowHost")
    host.setLayout(row)
    for i, label in enumerate(stages):
        if i > 0:
            arrow = QtWidgets.QLabel("→")
            arrow.setObjectName("guideFlowArrow")
            row.addWidget(arrow, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        node = QtWidgets.QLabel(label)
        node.setObjectName("guideFlowNode")
        node.setWordWrap(True)
        node.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        row.addWidget(node, 1)
    return host


def _guide_step_card(
    number: int,
    title: str,
    body: str,
    *,
    primary_label: str = "",
    primary_cb: Optional[Callable[[], None]] = None,
    secondary_label: str = "",
    secondary_cb: Optional[Callable[[], None]] = None,
) -> QtWidgets.QFrame:
    card = QtWidgets.QFrame()
    card.setObjectName("guideStepCard")
    lay = QtWidgets.QHBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(12)

    num = QtWidgets.QLabel(str(number))
    num.setObjectName("guideStepNumber")
    num.setFixedSize(28, 28)
    num.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(num, 0, QtCore.Qt.AlignmentFlag.AlignTop)

    text_col = QtWidgets.QVBoxLayout()
    text_col.setSpacing(4)
    ttl = QtWidgets.QLabel(title)
    ttl.setObjectName("guideStepTitle")
    ttl.setWordWrap(True)
    text_col.addWidget(ttl)
    body_lbl = QtWidgets.QLabel(body)
    body_lbl.setWordWrap(True)
    body_lbl.setObjectName("guideStepBody")
    text_col.addWidget(body_lbl)
    lay.addLayout(text_col, 1)

    btn_col = QtWidgets.QVBoxLayout()
    btn_col.setSpacing(6)
    if primary_label and primary_cb is not None:
        btn = QtWidgets.QPushButton(primary_label)
        btn.setObjectName("guideStepAction")
        btn.clicked.connect(primary_cb)
        btn_col.addWidget(btn)
    if secondary_label and secondary_cb is not None:
        btn2 = QtWidgets.QPushButton(secondary_label)
        btn2.setObjectName("guideStepActionSecondary")
        btn2.clicked.connect(secondary_cb)
        btn_col.addWidget(btn2)
    if primary_label or secondary_label:
        lay.addLayout(btn_col, 0)

    return card


def _guide_tip_card(title: str, body: str) -> QtWidgets.QFrame:
    card = QtWidgets.QFrame()
    card.setObjectName("guideTipCard")
    lay = QtWidgets.QVBoxLayout(card)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(4)
    ttl = QtWidgets.QLabel(title)
    ttl.setObjectName("guideTipTitle")
    lay.addWidget(ttl)
    body_lbl = QtWidgets.QLabel(body)
    body_lbl.setWordWrap(True)
    body_lbl.setObjectName("guideTipBody")
    lay.addWidget(body_lbl)
    return card


def _guide_fix_card(
    parent: QtWidgets.QWidget,
    title: str,
    bullets: list[str],
    *,
    action_label: str = "",
    action_cb: Optional[Callable[[], None]] = None,
) -> QtWidgets.QFrame:
    card = QtWidgets.QFrame()
    card.setObjectName("guideFixCard")
    lay = QtWidgets.QVBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(6)
    ttl = QtWidgets.QLabel(title)
    ttl.setObjectName("guideFixTitle")
    lay.addWidget(ttl)
    for line in bullets:
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        dot = QtWidgets.QLabel("•")
        dot.setObjectName("guideFixBullet")
        row.addWidget(dot, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        lbl = QtWidgets.QLabel(line)
        lbl.setWordWrap(True)
        lbl.setObjectName("guideFixBody")
        row.addWidget(lbl, 1)
        lay.addLayout(row)
    if action_label and action_cb is not None:
        btn = QtWidgets.QPushButton(action_label)
        btn.setObjectName("guideStepAction")
        btn.clicked.connect(action_cb)
        lay.addWidget(btn, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
    _ = parent
    return card


def _scroll_page(body: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(body)
    return scroll


def _build_first_time_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    page = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 8)
    lay.setSpacing(12)

    intro = QtWidgets.QLabel(
        "This app moves GPS data from your network into a COM port for survey gear. "
        "Follow the steps below — most field setups take about five minutes."
    )
    intro.setWordWrap(True)
    intro.setObjectName("guideIntro")
    lay.addWidget(intro)

    lay.addWidget(
        _guide_flow_diagram(["GNSS / INS\non network", "This PC\nSerial Link", "COM port", "Sonar / display"])
    )

    p = parent
    lay.addWidget(
        _guide_step_card(
            1,
            "Load a saved setup (optional)",
            "On a bench PC, open Presets and Load «Desk test». On the boat, load your boat preset.",
            primary_label="Open Presets",
            primary_cb=lambda: _guide_go_tools(p, "presets"),
        )
    )
    lay.addWidget(
        _guide_step_card(
            2,
            "Choose COM and speed",
            "On Control, pick the COM port wired to your downstream device. Baud is usually 115200 — match the receiver manual.",
            primary_label="Open Control",
            primary_cb=lambda: _guide_go_tab(p, "Control"),
        )
    )
    lay.addWidget(
        _guide_step_card(
            3,
            "Set UDP listen (most installs)",
            "Under Network path, use UDP listen. Set Listen port to match the GNSS output (often 10110). Listen host 0.0.0.0 is fine.",
            primary_label="Open Control",
            primary_cb=lambda: _guide_go_tab(p, "Control"),
        )
    )
    lay.addWidget(
        _guide_step_card(
            4,
            "Press Start",
            "Click the green Start button in the top bar. When the banner turns green, the bridge is running.",
            primary_label="Open Control",
            primary_cb=lambda: _guide_go_tab(p, "Control"),
        )
    )
    lay.addWidget(
        _guide_step_card(
            5,
            "Confirm data is moving",
            "Open Activity to see live sentences. Open HUD for update rate (Hz) and fix quality while you run.",
            primary_label="Open Activity",
            primary_cb=lambda: _guide_go_tab(p, "Activity"),
            secondary_label="Open HUD",
            secondary_cb=lambda: getattr(p, "_open_hud", lambda: None)(),
        )
    )

    lay.addWidget(
        _guide_tip_card(
            "Auto-find gear",
            "Not sure which COM or UDP port to use? Open Tools → Hub — it scans for common GNSS devices and fills Control for you.",
        )
    )
    lay.addStretch(1)
    return page


def _build_udp_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    page = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 8)
    lay.setSpacing(12)

    lay.addWidget(
        _guide_tip_card(
            "When to use UDP listen",
            "Trimble R10, Applanix POS MV, and most INS boxes send NMEA over UDP to a port on this PC. "
            "You listen — you do not dial out to them.",
        )
    )

    p = parent
    for n, title, body, pl, pcb in (
        (
            1,
            "Match the listen port",
            "Control → Network path → Listen port must equal the port configured on the GNSS (check the receiver web UI or manual).",
            "Open Control",
            lambda host=p: _guide_go_tab(host, "Control"),
        ),
        (
            2,
            "Bind to all interfaces",
            "Listen host 0.0.0.0 accepts traffic on every network adapter. Use your PC LAN IP only if your IT team requires it.",
            "Open Control",
            lambda host=p: _guide_go_tab(host, "Control"),
        ),
        (
            3,
            "Start and watch Activity",
            "After Start, sentences should appear within a few seconds. If nothing shows, see the Fix it path.",
            "Open Activity",
            lambda host=p: _guide_go_tab(host, "Activity"),
        ),
        (
            4,
            "Save when it works",
            "Tools → Presets → Save as… while stopped so the next session is one click.",
            "Open Presets",
            lambda host=p: _guide_go_tools(host, "presets"),
        ),
    ):
        lay.addWidget(_guide_step_card(n, title, body, primary_label=pl, primary_cb=pcb))

    lay.addWidget(
        _guide_tip_card(
            "Typical Trimble / R10 bench values",
            "COM7 @ 115200 · UDP listen 0.0.0.0:10110 · NMEA mode Passthrough (Tools → NMEA).",
        )
    )
    lay.addStretch(1)
    return page


def _build_tcp_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    page = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 8)
    lay.setSpacing(12)

    intro = QtWidgets.QLabel(
        "TCP is less common than UDP for GNSS. Enable Advanced network on Control first, then pick a mode."
    )
    intro.setWordWrap(True)
    intro.setObjectName("guideIntro")
    lay.addWidget(intro)

    p = parent
    lay.addWidget(
        _guide_tip_card(
            "TCP client — connect out to a server",
            "Use when another program on the network is already listening and this PC must join as a client.",
        )
    )
    for n, title, body in (
        (1, "Enable Advanced network", "Control → Network path → check Advanced network, select TCP client."),
        (2, "Enter server host and port", "Fill the TCP client fields with the IP and port of the listening service."),
        (3, "Start and confirm", "Press Start. The status banner shows when the TCP session is up."),
    ):
        lay.addWidget(
            _guide_step_card(
                n,
                title,
                body,
                primary_label="Open Control",
                primary_cb=lambda host=p: _guide_go_tab(host, "Control"),
            )
        )

    lay.addWidget(
        _guide_tip_card(
            "TCP server — others connect to this PC",
            "Use when Hypack, a plotter, or another machine must connect to this computer to reach the COM port.",
        )
    )
    for n, title, body in (
        (1, "Enable Advanced network", "Control → Network path → check Advanced network, select TCP server."),
        (2, "Pick bind address and port", "Bind 0.0.0.0 for LAN access or 127.0.0.1 for local-only. Add a Windows firewall rule if remote PCs connect."),
        (3, "Point clients at this PC", "After Start, configure client software with this PC's IP and your chosen port."),
    ):
        lay.addWidget(
            _guide_step_card(
                n,
                title,
                body,
                primary_label="Open Control",
                primary_cb=lambda host=p: _guide_go_tab(host, "Control"),
            )
        )
    lay.addStretch(1)
    return page


def _build_mavlink_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    page = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 8)
    lay.setSpacing(12)

    lay.addWidget(
        _guide_tip_card(
            "Cube / MAVLink + Mission Planner",
            "Serial Link owns the autopilot COM port and listens on UDP. Mission Planner uses "
            "UDP Client to talk to the bridge — not plain UDP (which also tries to listen on 14550).",
        )
    )

    p = parent
    for n, title, body, pl, pcb in (
        (
            1,
            "Raw binary + listen port 14550",
            "Control → COM (Cube telemetry port) @ 115200. Tools → NMEA → Raw binary. "
            "Listen port 14550, Fan-out on. Presets → load Cube MAVLink or Save as when done.",
            "Open Control",
            lambda host=p: _guide_go_tab(host, "Control"),
        ),
        (
            2,
            "Start Serial Link first",
            "Quit Mission Planner if it was using 14550. Start bridge — banner Running, "
            "Activity shows COM→NET with fd bytes when the Cube is powered.",
            "Open Activity",
            lambda host=p: _guide_go_tab(host, "Activity"),
        ),
        (
            3,
            "Mission Planner → UDP Client",
            "Right-click Connect → UDP Client. Remote 127.0.0.1:14550. "
            "Do not open the same COM in MP.",
            "",
            None,
        ),
        (
            4,
            "Remote laptop / mesh",
            "From another PC on LAN or Tailscale: UDP Client to survey PC IP:14550. "
            "Allow inbound UDP in Windows firewall.",
            "Full guide…",
            lambda host=p: _guide_open_doc(host, "docs/OPERATOR_GUIDE.md", "Operator guide"),
        ),
    ):
        lay.addWidget(
            _guide_step_card(
                n,
                title,
                body,
                primary_label=pl,
                primary_cb=pcb,
            )
        )

    lay.addWidget(
        _guide_tip_card(
            "Port conflict?",
            "Only Serial Link listens on 14550. MP plain UDP binds the same port → error. "
            "MP 'disposed object' usually means MAVLink never stabilized — check Raw mode and COM→NET in Activity.",
        )
    )
    lay.addStretch(1)
    return page


def _build_fix_page(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    page = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 8)
    lay.setSpacing(10)

    p = parent
    fixes = (
        (
            "Nothing in Activity after Start",
            [
                "Confirm the green Running banner is showing.",
                "UDP: listen port must match the GNSS sender — not a destination field.",
                "COM: make sure no other app (PuTTY, Tera Term) has the same port open.",
            ],
            "Open Control",
            lambda: _guide_go_tab(p, "Control"),
        ),
        (
            "COM port won't open",
            [
                "Click Refresh on Control and pick the port again.",
                "Tools → Hub may show Unlock COM if another process holds the port.",
                "Unplug and replug USB serial adapters, then Refresh.",
            ],
            "Open Hub",
            lambda: _guide_go_tools(p, "hub"),
        ),
        (
            "Sentences look garbled or missing",
            [
                "Baud on Control must exactly match the receiver (often 115200).",
                "Tools → NMEA: use Passthrough for normal GNSS text.",
                "Use Raw binary only for RTCM — not for NMEA sentences.",
            ],
            "Open NMEA",
            lambda: _guide_go_tools(p, "nmea"),
        ),
        (
            "Need bench proof before the boat",
            [
                "Load Presets → Desk test, Start, then Tools → Checks → UDP sample burst.",
                "Watch Activity or a paired com0com port for test sentences.",
            ],
            "Open Checks",
            lambda: _guide_go_tools(p, "checks"),
        ),
        (
            "Mission Planner / MAVLink won't connect",
            [
                "Serial Link must Start first with NMEA → Raw binary and listen port 14550.",
                "Mission Planner: UDP Client to 127.0.0.1:14550 — not plain UDP.",
                "Activity must show COM→NET before MP will hold parameters.",
            ],
            "Operator guide…",
            lambda: _guide_open_doc(p, "docs/OPERATOR_GUIDE.md", "Operator guide"),
        ),
    )
    for title, bullets, action_label, action_cb in fixes:
        lay.addWidget(
            _guide_fix_card(p, title, bullets, action_label=action_label, action_cb=action_cb)
        )
    lay.addStretch(1)
    return page


class OperatorGuideWidget(QtWidgets.QWidget):
    """Scenario-based guide with step cards and navigation shortcuts."""

    def __init__(self, parent_window: QtWidgets.QWidget) -> None:
        super().__init__(parent_window)
        self.setObjectName("operatorGuidePanel")
        self._host = parent_window

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        pick_lbl = QtWidgets.QLabel("What do you need help with?")
        pick_lbl.setObjectName("guidePickLabel")
        root.addWidget(pick_lbl)

        chip_row = QtWidgets.QHBoxLayout()
        chip_row.setSpacing(8)
        self._scenario_group = QtWidgets.QButtonGroup(self)
        self._scenario_group.setExclusive(True)
        self._stack = QtWidgets.QStackedWidget()
        self._stack.setObjectName("guideScenarioStack")

        scenarios: list[tuple[str, str, str, Callable[[], QtWidgets.QWidget]]] = [
            ("start", "First time", "🚀", lambda: _build_first_time_page(self._host)),
            ("udp", "UDP survey", "📡", lambda: _build_udp_page(self._host)),
            ("mavlink", "Cube / MAVLink", "🛸", lambda: _build_mavlink_page(self._host)),
            ("tcp", "TCP setup", "🔌", lambda: _build_tcp_page(self._host)),
            ("fix", "Fix it", "🔧", lambda: _build_fix_page(self._host)),
        ]

        for i, (_sid, label, icon, builder) in enumerate(scenarios):
            btn = QtWidgets.QPushButton(f"{icon}  {label}")
            btn.setObjectName("guideScenarioChip")
            btn.setCheckable(True)
            btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self._scenario_group.addButton(btn, i)
            chip_row.addWidget(btn)
            self._stack.addWidget(_scroll_page(builder()))

        chip_row.addStretch(1)
        root.addLayout(chip_row)
        root.addWidget(self._stack, 1)

        doc_lbl = QtWidgets.QLabel("Full offline manuals")
        doc_lbl.setObjectName("guideDocLabel")
        root.addWidget(doc_lbl)
        doc_row = QtWidgets.QHBoxLayout()
        doc_row.setSpacing(8)
        for doc_label, rel in (
            ("Getting started…", "docs/GETTING_STARTED.md"),
            ("Operator guide…", "docs/OPERATOR_GUIDE.md"),
            ("NORBIT DCT…", "docs/NORBIT_DCT.md"),
        ):
            btn = QtWidgets.QPushButton(doc_label)
            btn.setObjectName("guideDocBtn")
            btn.setToolTip(f"Open {rel} inside Serial Link")
            btn.clicked.connect(
                lambda _c=False, r=rel, t=doc_label: _guide_open_doc(self._host, r, t)
            )
            doc_row.addWidget(btn)
        doc_row.addStretch(1)
        root.addLayout(doc_row)

        self._scenario_group.idClicked.connect(self._stack.setCurrentIndex)
        self._scenario_group.button(0).setChecked(True)
        self._stack.setCurrentIndex(0)


def build_operator_guide_panel(parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    return OperatorGuideWidget(parent)

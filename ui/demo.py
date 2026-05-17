"""Guided product demo — presenter teleprompter + automated walkthrough."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.app_icon import apply_app_icon
from ui.styles import PRODUCT_DEMO_STYLESHEET
from version import __version__

ActionFn = Callable[[QtWidgets.QWidget], None]

# Default hold on each step (was ~3s on many beats — now 6s for presenter pacing).
DEMO_STEP_HOLD_MS = 6000
DEMO_STEP_HOLD_LONG_MS = 10_000
DEMO_STEP_HOLD_WATCH_MS = 28_000

PHASE_LABELS = {
    "intro": "Overview",
    "bench": "Bench · UDP",
    "hud": "Survey HUD",
    "tcp": "TCP · moving map",
    "ops": "Go-live tools",
    "wrap": "Wrap-up",
}


@dataclass(frozen=True)
class DemoStep:
    step_id: str
    phase: str
    title: str
    cue: str
    narration: str
    pause_ms: int
    action: Optional[ActionFn] = None


def _log(win: QtWidgets.QWidget, line: str) -> None:
    if hasattr(win, "_log_ui"):
        win._log_ui(f"[Demo] {line}")  # type: ignore[attr-defined]


def _apply_desk(win: QtWidgets.QWidget) -> None:
    if hasattr(win, "_apply_bench_preset"):
        win._apply_bench_preset()  # type: ignore[attr-defined]


def _apply_boat(win: QtWidgets.QWidget) -> None:
    if hasattr(win, "_apply_production_preset"):
        win._apply_production_preset()  # type: ignore[attr-defined]


def _set_udp_listen(win: QtWidgets.QWidget) -> None:
    win.chk_advanced_net.setChecked(False)  # type: ignore[attr-defined]
    win.rb_udp_listen.setChecked(True)  # type: ignore[attr-defined]
    if hasattr(win, "_mode_toggle"):
        win._mode_toggle()  # type: ignore[attr-defined]


def _set_tcp_server(win: QtWidgets.QWidget) -> None:
    win.chk_advanced_net.setChecked(True)  # type: ignore[attr-defined]
    win.rb_tcp_server.setChecked(True)  # type: ignore[attr-defined]
    if hasattr(win, "_mode_toggle"):
        win._mode_toggle()  # type: ignore[attr-defined]


def _set_tcp_server_from_presets(win: QtWidgets.QWidget) -> None:
    _open_presets_tab(win)
    _set_tcp_server(win)


def _verbose_log_on(win: QtWidgets.QWidget) -> None:
    chk = getattr(win, "chk_verbose", None)
    if chk is not None:
        chk.setChecked(True)
    preset = getattr(win, "cmb_log_preset", None)
    if preset is not None:
        for i in range(preset.count()):
            if preset.itemData(i) == "all":
                preset.setCurrentIndex(i)
                break


def _open_drawer(win: QtWidgets.QWidget) -> None:
    drawer = getattr(win, "_drawer_btn", None)
    if drawer is not None:
        drawer.setChecked(True)


def _open_tools(win: QtWidgets.QWidget, tab_title: str) -> None:
    _open_drawer(win)
    tabs = getattr(win, "_drawer_tabs", None) or getattr(win, "_main_tabs", None)
    if tabs is None:
        return
    key = tab_title.lower()[:4]
    for i in range(tabs.count()):
        label = tabs.tabText(i).lower()
        if label.startswith(key) or key in label:
            tabs.setCurrentIndex(i)
            return


def _open_presets_tab(win: QtWidgets.QWidget) -> None:
    _open_tools(win, "preset")


def _open_nmea_tab(win: QtWidgets.QWidget) -> None:
    _open_tools(win, "nmea")


def _open_diag_tab(win: QtWidgets.QWidget) -> None:
    _open_tools(win, "diag")


def _start_if_stopped(win: QtWidgets.QWidget) -> None:
    b = getattr(win, "bridge", None)
    if b is not None and getattr(b, "running", False):
        return
    if hasattr(win, "start_bridge"):
        win.start_bridge()  # type: ignore[attr-defined]


def _stop_bridge(win: QtWidgets.QWidget) -> None:
    if hasattr(win, "stop_bridge"):
        win.stop_bridge()  # type: ignore[attr-defined]


def _stop_diag(win: QtWidgets.QWidget) -> None:
    if hasattr(win, "_diag_stop"):
        win._diag_stop()  # type: ignore[attr-defined]


def _open_hud(win: QtWidgets.QWidget) -> None:
    if hasattr(win, "_open_stats_popout"):
        win._open_stats_popout()  # type: ignore[attr-defined]


def _udp_burst(win: QtWidgets.QWidget) -> None:
    if hasattr(win, "_diag_run_udp_sample"):
        win._diag_run_udp_sample()  # type: ignore[attr-defined]


def _tcp_demo(win: QtWidgets.QWidget) -> None:
    _open_tools(win, "diag")
    if hasattr(win, "_diag_run_tcp_demo"):
        win._diag_run_tcp_demo()  # type: ignore[attr-defined]


def _send_sample(win: QtWidgets.QWidget) -> None:
    _open_tools(win, "send")
    if hasattr(win, "_insert_send_sample"):
        win._insert_send_sample()  # type: ignore[attr-defined]


def _prep_tcp_switch(win: QtWidgets.QWidget) -> None:
    _stop_diag(win)
    _stop_bridge(win)


def _finish_boat_preset(win: QtWidgets.QWidget) -> None:
    _stop_diag(win)
    _stop_bridge(win)
    _apply_boat(win)


PRODUCT_DEMO_STEPS: tuple[DemoStep, ...] = (
    DemoStep(
        "intro",
        "intro",
        "Welcome",
        "Point at: Field layout — log, connect row, Tools drawer.",
        "This is the Field layout: a full-width NMEA log, Start/Stop up front, and a Tools drawer "
        "for NMEA settings, Send, Diagnostics, and Net.\n\n"
        "One window for the survey day — not a maze of tabs.",
        DEMO_STEP_HOLD_MS,
        None,
    ),
    DemoStep(
        "survey_bar",
        "intro",
        "Survey bar",
        "Point at: Presets · Recent · Checklists · HUD · Tools · Demo.",
        "The survey bar is your quick lane.\n"
        "Presets and Recent restore COM + UDP + NMEA; Checklists runs bench or boat preflight; "
        "HUD opens live metrics; Tools opens the drawer; Demo is this teleprompter.\n\n"
        "Most operators never need the full menu bar.",
        DEMO_STEP_HOLD_MS,
        None,
    ),
    DemoStep(
        "desk",
        "bench",
        "Bench preset",
        "Point at: Presets menu — load bench preset (or survey bar Presets).",
        "Loading the bench-style preset — com0com path with UDP on this PC.\n"
        "The bridge owns one COM; your simulator sends UDP here; "
        "Hypack or Tera Term watches the paired COM port.",
        DEMO_STEP_HOLD_MS,
        _apply_desk,
    ),
    DemoStep(
        "tools_presets",
        "bench",
        "Tools · Presets",
        "Point at: Tools drawer — Presets tab.",
        "Presets save everything you care about: COM, baud, UDP listen, optional boat LAN notes, "
        "and Advanced network (TCP server/client) when you need it.\n"
        "We start on UDP listen; TCP server comes later in the demo.",
        DEMO_STEP_HOLD_MS,
        _open_presets_tab,
    ),
    DemoStep(
        "tools_nmea",
        "bench",
        "Tools · NMEA",
        "Point at: Tools drawer — NMEA tab.",
        "NMEA mode lives here: Passthrough for Trimble/simulators, Strict for bench QA, "
        "Raw only for RTCM or other binary streams.\n"
        "The connect row above stays for COM, baud, and UDP listen while Running.",
        DEMO_STEP_HOLD_MS,
        _open_nmea_tab,
    ),
    DemoStep(
        "udp",
        "bench",
        "UDP listen",
        "Point at: Connect row — UDP host/port (Advanced off for now).",
        "UDP listen means this PC owns the port.\n"
        "Senders aim at your listen address — the bridge does not fight NMEA Simulator for the same bind.",
        DEMO_STEP_HOLD_MS,
        _set_udp_listen,
    ),
    DemoStep(
        "udp_start",
        "bench",
        "Start bridge",
        "Point at: Running in the log + status bar.",
        "Starting the bridge now.\n"
        "An idle log right after start is normal — traffic appears when something sends UDP.",
        DEMO_STEP_HOLD_MS,
        _start_if_stopped,
    ),
    DemoStep(
        "udp_log",
        "bench",
        "Full live log",
        "Point at: Every NMEA line scrolling in the log.",
        "Switching the log to full detail so the audience sees real sentences, not just summaries.",
        DEMO_STEP_HOLD_MS,
        _verbose_log_on,
    ),
    DemoStep(
        "udp_feed",
        "bench",
        "UDP traffic burst",
        "Point at: Log filling with GGA / RMC.",
        "Firing a short UDP burst into the listen port.\n"
        "Watch sentences appear — that is network traffic entering the bridge.",
        DEMO_STEP_HOLD_LONG_MS,
        _udp_burst,
    ),
    DemoStep(
        "status_hz",
        "bench",
        "Wire Hz on the status bar",
        "Point at: Status bar — Into COM ~5 Hz after the burst.",
        "Into COM is wire rate from the network side — about one tick per UDP batch at 5 Hz.\n"
        "From COM is serial read activity; on com0com it can look higher because of echo.\n\n"
        "Session totals in the HUD count sentences, not chunks.",
        DEMO_STEP_HOLD_MS,
        None,
    ),
    DemoStep(
        "hud",
        "hud",
        "Survey HUD",
        "Point at: Detached HUD on a second monitor.",
        "Opening the Survey HUD — large tiles for Into COM, From COM, Transport, and session totals.\n"
        "Built to sit beside Hypack while the main window stays on the bridge PC.",
        DEMO_STEP_HOLD_LONG_MS,
        _open_hud,
    ),
    DemoStep(
        "hud_detail",
        "hud",
        "Read the HUD",
        "Point at: Transport OK · Into COM · session counters.",
        "Transport OK means queues are healthy — no backlog warnings.\n"
        "Into COM should track your feed rate; From COM reflects what left on serial.\n\n"
        "Collapse sections you do not need; pin the window on the projector side.",
        DEMO_STEP_HOLD_MS,
        None,
    ),
    DemoStep(
        "tcp_switch",
        "tcp",
        "Switch to TCP",
        "Say: same bridge, different wire — TCP server next.",
        "Stopping UDP and switching to TCP server mode.\n"
        "External apps connect to us; same COM path out to the autopilot.",
        DEMO_STEP_HOLD_MS,
        _prep_tcp_switch,
    ),
    DemoStep(
        "tcp_mode",
        "tcp",
        "TCP server",
        "Point at: Tools → Presets — Advanced network, TCP server, port 4001.",
        "TCP server binds on this PC — default port 4001.\n"
        "Clients on this machine use 127.0.0.1:4001; other PCs on the LAN use this PC's IP.",
        DEMO_STEP_HOLD_MS,
        _set_tcp_server_from_presets,
    ),
    DemoStep(
        "tcp_start",
        "tcp",
        "Start bridge (TCP)",
        "Point at: Log — TCP server listening.",
        "Bridge starting in TCP server mode.\n"
        "No client connected yet is fine — the log will say listening.",
        DEMO_STEP_HOLD_MS,
        _start_if_stopped,
    ),
    DemoStep(
        "tcp_demo",
        "tcp",
        "Moving map demo",
        "Point at: Chart / Hypack — track starts moving north.",
        "Launching the ~4 minute TCP demo feed — Los Angeles toward Sacramento at presenter speed.\n"
        "Five NMEA sentences, five times per second; the chart should crawl along the coast.",
        DEMO_STEP_HOLD_MS,
        _tcp_demo,
    ),
    DemoStep(
        "tcp_watch",
        "tcp",
        "Let it run",
        "Point at: Chart + HUD — Transport OK, Into COM ~5 Hz.",
        "Give the audience time to watch the track and the HUD.\n"
        "Transport should stay OK — the demo client reads TCP replies so queues do not fill.\n\n"
        "Click Next step when you are ready (or wait for the timer).",
        DEMO_STEP_HOLD_WATCH_MS,
        None,
    ),
    DemoStep(
        "diag_tools",
        "ops",
        "Diagnostics",
        "Point at: Tools — Diag — TCP demo / stress / verify.",
        "Diagnostics is where you stress-test and verify before the boat leaves the dock.\n"
        "TCP demo (~4 min) is what we just started; TCP stress is the long soak; "
        "Full verify runs compile, bench, and check_setup in one shot.",
        DEMO_STEP_HOLD_MS,
        _open_diag_tab,
    ),
    DemoStep(
        "send",
        "ops",
        "Send tab",
        "Point at: Tools — Send, sample GGA in the box.",
        "Send tab injects test NMEA while the bridge is running.\n"
        "On the bench, watch the paired COM — not the port the bridge owns.",
        DEMO_STEP_HOLD_MS,
        _send_sample,
    ),
    DemoStep(
        "preflight",
        "ops",
        "Checklists",
        "Point at: Survey bar — Checklists (or Tools → Diagnostics).",
        "Checklists run check_setup for bench or boat — COM free, UDP port, subnet hints.\n"
        "Use Bench checklist on the dock; Boat checklist before leaving for the water.",
        DEMO_STEP_HOLD_MS,
        _open_diag_tab,
    ),
    DemoStep(
        "boat",
        "wrap",
        "Boat / INS preset",
        "Point at: Presets — load boat-style preset.",
        "Boat-style preset loads production Ethernet and COM for the survey PC.\n"
        "Mission Planner stays on its own link; this bridge is NMEA to the Cube GPS port.",
        DEMO_STEP_HOLD_MS,
        _finish_boat_preset,
    ),
    DemoStep(
        "done",
        "wrap",
        "You're done",
        "Invite questions — Demo, HUD, Checklists anytime.",
        "Story in one line: bench preset and UDP, live log and HUD, TCP with a moving map, "
        "Diagnostics and Send for confidence, boat preset for go-live.\n\n"
        "Thank you — questions?",
        DEMO_STEP_HOLD_MS,
        None,
    ),
)


def _total_pause_ms(steps: tuple[DemoStep, ...] = PRODUCT_DEMO_STEPS) -> int:
    return sum(s.pause_ms for s in steps)


class DemoRunner(QtCore.QObject):
    finished = QtCore.Signal()
    stopped = QtCore.Signal()
    step_changed = QtCore.Signal(int, object)  # index, DemoStep
    pause_seconds_left = QtCore.Signal(int)

    def __init__(self, host: QtWidgets.QWidget, steps: tuple[DemoStep, ...] = PRODUCT_DEMO_STEPS) -> None:
        super().__init__(host)
        self._host = host
        self._steps = steps
        self._index = -1
        self._running = False
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._advance)
        self._pause_ui = QtCore.QTimer(self)
        self._pause_ui.timeout.connect(self._emit_pause_tick)
        self._pause_deadline = 0.0
        self._waiting_for_bridge = False
        self._poll_gen = 0

    def running(self) -> bool:
        return self._running

    def current_index(self) -> int:
        return self._index

    def reset(self) -> None:
        """Drop pending timers / polls so auto-play can start again after Stop."""
        self._poll_gen += 1
        self._running = False
        self._timer.stop()
        self._pause_ui.stop()
        self._waiting_for_bridge = False

    def start(self) -> None:
        if self._running:
            return
        self.reset()
        self._running = True
        self._index = -1
        _log(self._host, "Automated demo started")
        self._advance()

    def stop(self) -> None:
        was_running = self._running
        self.reset()
        if was_running:
            _stop_diag(self._host)
            _log(self._host, "Demo stopped")
        self.stopped.emit()

    def skip_to_next_step(self) -> None:
        """Presenter control — end the wait and go to the next step."""
        if not self._running:
            return
        self._timer.stop()
        self._pause_ui.stop()
        self._waiting_for_bridge = False
        self.pause_seconds_left.emit(0)
        self._advance()

    def _advance(self) -> None:
        if not self._running:
            return
        self._pause_ui.stop()
        self._index += 1
        if self._index >= len(self._steps):
            self._running = False
            self._timer.stop()
            self._pause_ui.stop()
            self._waiting_for_bridge = False
            _log(self._host, "Automated demo finished")
            self.finished.emit()
            return
        step = self._steps[self._index]
        self.step_changed.emit(self._index, step)
        _log(self._host, f"Step {self._index + 1}/{len(self._steps)}: {step.title}")
        try:
            if step.action is not None:
                step.action(self._host)
        except Exception as exc:
            _log(self._host, f"Step action error: {exc}")
        if self._needs_bridge_wait(step):
            self._waiting_for_bridge = True
            self._poll_bridge(0, self._poll_gen)
            return
        self._schedule_pause(step.pause_ms)

    def _needs_bridge_wait(self, step: DemoStep) -> bool:
        return step.step_id in ("udp_start", "tcp_start")

    def _poll_bridge(self, attempt: int, poll_gen: int = -1) -> None:
        if poll_gen >= 0 and poll_gen != self._poll_gen:
            return
        if not self._running or not self._waiting_for_bridge:
            return
        b = getattr(self._host, "bridge", None)
        if b is not None and getattr(b, "running", False):
            self._waiting_for_bridge = False
            self._schedule_pause(self._steps[self._index].pause_ms)
            return
        if attempt >= 40:
            _log(self._host, "Bridge did not reach Running in time — continuing demo")
            self._waiting_for_bridge = False
            self._schedule_pause(self._steps[self._index].pause_ms)
            return
        gen = self._poll_gen
        QtCore.QTimer.singleShot(250, lambda: self._poll_bridge(attempt + 1, gen))

    def _schedule_pause(self, ms: int) -> None:
        if not self._running:
            return
        if ms <= 0:
            self.pause_seconds_left.emit(0)
            self._advance()
            return
        self._pause_deadline = time.monotonic() + ms / 1000.0
        self._pause_ui.start(200)
        self._emit_pause_tick()
        self._timer.start(ms)

    def _emit_pause_tick(self) -> None:
        if not self._running:
            return
        left = int(max(0.0, self._pause_deadline - time.monotonic()) + 0.99)
        self.pause_seconds_left.emit(left)


class ProductDemoDialog(QtWidgets.QDialog):
    def __init__(self, host: QtWidgets.QWidget) -> None:
        super().__init__(host)
        self._host = host
        self.setObjectName("ProductDemoDialog")
        self.setStyleSheet(PRODUCT_DEMO_STYLESHEET)
        apply_app_icon(self)
        self.setWindowTitle(f"Presenter — NMEA Bridge v{__version__}")
        self.setMinimumSize(760, 500)
        self.resize(860, 560)
        self._step_hold_ms = 0
        self._presenter_index = -1

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        top = QtWidgets.QHBoxLayout()
        title_bar = QtWidgets.QLabel("PRODUCT DEMO")
        title_bar.setObjectName("demoTitleBar")
        top.addWidget(title_bar)
        top.addStretch(1)
        self._phase_chip = QtWidgets.QLabel("Ready")
        self._phase_chip.setObjectName("demoPhaseChip")
        top.addWidget(self._phase_chip)
        self._pin = QtWidgets.QCheckBox("Stay on top")
        self._pin.setObjectName("demoPinTop")
        self._pin.toggled.connect(self._on_pin)
        top.addWidget(self._pin)
        root.addLayout(top)

        self._progress = QtWidgets.QProgressBar()
        self._progress.setObjectName("demoProgress")
        self._progress.setRange(0, len(PRODUCT_DEMO_STEPS))
        self._progress.setValue(0)
        self._progress.setFormat("Step %v of %m")
        root.addWidget(self._progress)

        body = QtWidgets.QHBoxLayout()
        body.setSpacing(12)

        self._list = QtWidgets.QListWidget()
        self._list.setObjectName("demoStepList")
        self._list.setMinimumWidth(200)
        self._list.setMaximumWidth(240)
        self._fill_step_list()
        self._list.currentRowChanged.connect(self._on_list_row)
        body.addWidget(self._list)

        card = QtWidgets.QFrame()
        card.setObjectName("demoPresentCard")
        card_lay = QtWidgets.QVBoxLayout(card)
        card_lay.setContentsMargins(18, 16, 18, 16)
        card_lay.setSpacing(10)

        self._step_index_lbl = QtWidgets.QLabel("")
        self._step_index_lbl.setObjectName("demoStepIndex")
        card_lay.addWidget(self._step_index_lbl)

        self._step_title = QtWidgets.QLabel("Ready to present")
        self._step_title.setObjectName("demoStepTitle")
        self._step_title.setWordWrap(True)
        card_lay.addWidget(self._step_title)

        self._cue = QtWidgets.QLabel("Next step when you are ready — or pick a beat on the left.")
        self._cue.setObjectName("demoCue")
        self._cue.setWordWrap(True)
        card_lay.addWidget(self._cue)

        self._narration = QtWidgets.QTextEdit()
        self._narration.setObjectName("demoNarration")
        self._narration.setReadOnly(True)
        self._narration.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._narration.setStyleSheet("background: transparent;")
        nf = QtGui.QFont("Segoe UI", 13)
        self._narration.setFont(nf)
        card_lay.addWidget(self._narration, 1)

        self._countdown = QtWidgets.QLabel("")
        self._countdown.setObjectName("demoCountdown")
        card_lay.addWidget(self._countdown)

        body.addWidget(card, 1)
        root.addLayout(body, 1)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_prev = QtWidgets.QPushButton("Previous step")
        self._btn_prev.setObjectName("demoBtnPrev")
        self._btn_next = QtWidgets.QPushButton("Next step")
        self._btn_next.setObjectName("demoBtnNext")
        self._btn_step = QtWidgets.QPushButton("Run selected step")
        self._btn_step.setObjectName("demoBtnStep")
        btn_row.addWidget(self._btn_prev)
        btn_row.addWidget(self._btn_next)
        btn_row.addWidget(self._btn_step)
        btn_row.addStretch(1)
        self._btn_run = QtWidgets.QPushButton("Auto-play script")
        self._btn_run.setObjectName("demoBtnRun")
        self._btn_stop = QtWidgets.QPushButton("Stop auto")
        self._btn_stop.setObjectName("demoBtnStop")
        self._btn_stop.setEnabled(False)
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setObjectName("demoBtnClose")
        btn_row.addWidget(self._btn_run)
        btn_row.addWidget(self._btn_stop)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        self._next_tooltip_manual = "Next beat — runs setup for that step (your pace)"
        self._next_tooltip_auto = "Skip the timer during auto-play"
        self._btn_next.setToolTip(self._next_tooltip_manual)
        self._btn_prev.setToolTip("Go back one beat in the script (does not undo bridge actions)")
        self._btn_step.setToolTip("Run setup for the highlighted step in the list")
        self._btn_run.setToolTip("Optional: hands-off walkthrough with timed pauses")

        mins = max(1, round(_total_pause_ms() / 60_000))
        n = len(PRODUCT_DEMO_STEPS)
        self._step_index_lbl.setText(f"{n} steps · manual or auto")

        self._runner = DemoRunner(host)
        self._runner.step_changed.connect(self._on_step)
        self._runner.pause_seconds_left.connect(self._on_pause_tick)
        self._runner.finished.connect(self._on_completed)
        self._runner.stopped.connect(self._on_stopped)
        self._btn_run.clicked.connect(self._start_auto)
        self._btn_stop.clicked.connect(self._stop_all)
        self._btn_next.clicked.connect(self._on_next_step)
        self._btn_prev.clicked.connect(self._manual_back)
        self._btn_step.clicked.connect(self._run_selected)
        close_btn.clicked.connect(self.close)

        self._bootstrap_presenter()

    def _fill_step_list(self) -> None:
        self._list.clear()
        last_phase: Optional[str] = None
        for i, step in enumerate(PRODUCT_DEMO_STEPS):
            if step.phase != last_phase:
                hdr = QtWidgets.QListWidgetItem(PHASE_LABELS.get(step.phase, step.phase))
                hdr.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
                hdr.setForeground(QtGui.QColor("#9a8a72"))
                self._list.addItem(hdr)
                last_phase = step.phase
            it = QtWidgets.QListWidgetItem(f"  {step.title}")
            it.setData(QtCore.Qt.ItemDataRole.UserRole, i)
            self._list.addItem(it)

    def _step_index_from_row(self, row: int) -> Optional[int]:
        if row < 0:
            return None
        it = self._list.item(row)
        if it is None:
            return None
        idx = it.data(QtCore.Qt.ItemDataRole.UserRole)
        if idx is None:
            return None
        return int(idx)

    def _select_list_row_for_step(self, step_index: int) -> None:
        for row in range(self._list.count()):
            idx = self._step_index_from_row(row)
            if idx == step_index:
                self._list.setCurrentRow(row)
                return

    def _show_step_preview(self, step_index: int) -> None:
        if step_index < 0:
            return
        step = PRODUCT_DEMO_STEPS[step_index]
        total = len(PRODUCT_DEMO_STEPS)
        pace = "your pace"
        if self._runner.running() and step.pause_ms > 0:
            pace = f"{max(1, step.pause_ms // 1000)}s auto-hold"
        self._step_index_lbl.setText(f"Step {step_index + 1} of {total}  ·  {pace}")
        self._phase_chip.setText(PHASE_LABELS.get(step.phase, step.phase))
        self._step_title.setText(step.title)
        self._cue.setText(step.cue)
        self._narration.setPlainText(step.narration)

    def _bootstrap_presenter(self) -> None:
        """Manual pitch mode from the first open — no need to start auto."""
        self._presenter_index = 0
        self._progress.setValue(1)
        self._show_step_preview(0)
        self._select_list_row_for_step(0)
        self._phase_chip.setText("Manual")
        self._countdown.setText("Pitch mode — Next step when ready (auto-play is optional)")
        self._sync_nav_buttons()

    def _sync_nav_buttons(self) -> None:
        auto = self._runner.running()
        complete = self._phase_chip.text() == "Complete"
        at_end = self._presenter_index >= len(PRODUCT_DEMO_STEPS) - 1
        self._btn_prev.setEnabled(not auto and not complete and self._presenter_index > 0)
        self._btn_next.setEnabled(not auto and (not at_end or complete))
        self._btn_step.setEnabled(not auto and not complete)
        self._btn_run.setEnabled(not auto and not complete)
        self._btn_stop.setEnabled(auto)

    def _on_list_row(self, row: int) -> None:
        idx = self._step_index_from_row(row)
        if idx is None:
            return
        if self._runner.running():
            return
        self._presenter_index = idx
        self._progress.setValue(idx + 1)
        self._show_step_preview(idx)
        self._sync_nav_buttons()
        self._countdown.setText("Jumped in the script — Next step or Run selected step")

    def _on_step(self, index: int, step: DemoStep) -> None:
        self._presenter_index = index
        self._progress.setValue(index + 1)
        self._step_hold_ms = step.pause_ms
        self._show_step_preview(index)
        self._select_list_row_for_step(index)
        self._btn_next.setEnabled(True)
        self._btn_next.setToolTip(self._next_tooltip_auto)
        self._btn_prev.setEnabled(False)
        self._btn_step.setEnabled(False)
        self._countdown.setText("")
        self._sync_nav_buttons()

    def _on_pause_tick(self, seconds_left: int) -> None:
        if not self._runner.running():
            self._countdown.setText("")
            return
        if seconds_left <= 0:
            self._countdown.setText("Moving to next step...")
            return
        total_s = max(1, self._step_hold_ms // 1000)
        self._countdown.setText(
            f"{seconds_left}s of {total_s}s on this step  —  or click Next step"
        )

    def _start_auto(self) -> None:
        self._presenter_index = -1
        self._phase_chip.setText("Auto")
        self._btn_next.setToolTip(self._next_tooltip_auto)
        self._progress.setValue(0)
        self._countdown.setText("")
        self._sync_nav_buttons()
        self._runner.start()

    def _on_next_step(self) -> None:
        if self._runner.running():
            self._runner.skip_to_next_step()
            return
        self._manual_advance()

    def _manual_advance(self) -> None:
        if self._phase_chip.text() == "Complete":
            self._bootstrap_presenter()
            return
        next_idx = self._presenter_index + 1
        if next_idx >= len(PRODUCT_DEMO_STEPS):
            self._on_completed()
            return
        step = PRODUCT_DEMO_STEPS[next_idx]
        self._presenter_index = next_idx
        self._progress.setValue(next_idx + 1)
        self._step_hold_ms = 0
        self._phase_chip.setText("Manual")
        self._show_step_preview(next_idx)
        self._select_list_row_for_step(next_idx)
        _log(self._host, f"Manual advance: {step.title}")
        if step.action is not None:
            try:
                step.action(self._host)
            except Exception as exc:
                _log(self._host, f"Step error: {exc}")
        self._btn_next.setToolTip(self._next_tooltip_manual)
        self._countdown.setText("Your pace — Next step when ready")
        self._sync_nav_buttons()

    def _manual_back(self) -> None:
        if self._runner.running() or self._presenter_index <= 0:
            return
        idx = self._presenter_index - 1
        self._presenter_index = idx
        self._progress.setValue(idx + 1)
        self._show_step_preview(idx)
        self._select_list_row_for_step(idx)
        self._countdown.setText("Your pace — Previous / Next step to move in the script")
        self._sync_nav_buttons()

    def _on_stopped(self) -> None:
        idx = self._runner.current_index()
        if idx >= 0:
            self._presenter_index = idx
        if self._phase_chip.text() == "Auto":
            self._phase_chip.setText("Manual")
        self._btn_next.setToolTip(self._next_tooltip_manual)
        self._countdown.setText("Auto stopped — Auto-play script to run again, or use Previous / Next step")
        self._sync_nav_buttons()

    def _on_completed(self) -> None:
        self._presenter_index = len(PRODUCT_DEMO_STEPS) - 1
        self._progress.setValue(len(PRODUCT_DEMO_STEPS))
        self._phase_chip.setText("Complete")
        self._step_index_lbl.setText(f"All {len(PRODUCT_DEMO_STEPS)} steps done")
        self._step_title.setText("Demo complete")
        self._cue.setText("Thank the audience — open for questions.")
        self._countdown.setText("Next step to start over from Welcome")
        self._step_hold_ms = 0
        self._btn_next.setToolTip("Start presentation again from Welcome")
        self._sync_nav_buttons()

    def _run_selected(self) -> None:
        row = self._list.currentRow()
        idx = self._step_index_from_row(row)
        if idx is None:
            idx = 0
        self._presenter_index = idx
        step = PRODUCT_DEMO_STEPS[idx]
        self._show_step_preview(idx)
        self._progress.setValue(idx + 1)
        _log(self._host, f"Manual step: {step.title}")
        if step.action is not None:
            try:
                step.action(self._host)
            except Exception as exc:
                _log(self._host, f"Step error: {exc}")
        self._phase_chip.setText("Manual")
        self._countdown.setText("Ran setup for this step — Next step when ready")
        self._sync_nav_buttons()

    def _stop_all(self) -> None:
        if self._runner.running():
            self._runner.stop()
        else:
            _stop_diag(self._host)
            self._runner.reset()
            self._on_stopped()

    def _on_pin(self, on: bool) -> None:
        flags = self.windowFlags()
        if on:
            self.setWindowFlags(flags | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def recover_if_stuck(self) -> None:
        """If auto was aborted but UI still looks locked, reset presenter controls."""
        if self._runner.running():
            return
        if self._phase_chip.text() == "Auto":
            self._on_stopped()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._runner.reset()
        _stop_diag(self._host)
        super().closeEvent(event)


def open_product_demo(host: QtWidgets.QWidget) -> ProductDemoDialog:
    dlg = ProductDemoDialog(host)
    dlg.show()
    dlg.raise_()
    dlg.activateWindow()
    return dlg

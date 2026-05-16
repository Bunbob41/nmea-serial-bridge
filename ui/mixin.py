# ui/mixin.py — bridge start/stop, logging, validation (shared by all UIs)
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Optional

import asyncio
import serial.tools.list_ports
from PySide6 import QtCore, QtGui, QtWidgets

from bench_config import load_bench_defaults, load_production_defaults
from bridge_core import (
    BridgeAsyncThread,
    NetMode,
    SerialNetBridge,
    SERIAL_OPEN_TIMEOUT_S,
    START_WATCHDOG_MS,
    UI_LOG_FLUSH_MS,
    UI_LOG_MAX_LINES_PER_FLUSH,
    UI_LOG_PENDING_MAX,
    _FileSurveyLog,
    _friendly_serial_error,
    _nmea_line_bytes,
    _open_serial_port_timed,
    _parse_port,
)
from nmea_codec import NmeaFilter, NmeaMode
from nmea_static_edh import EDH_ALT_M, EDH_LAT_DEG, EDH_LON_DEG, build_gga, build_rmc
from log_serial_coalesce import serial_timeout_line_suppress
from py_interpreter import cli_python_executable
from ui.stats_line import format_live_stats_line
from ui.stats_popout import SurveyStatsPopout

_REPO_ROOT = Path(__file__).resolve().parent.parent


class BridgeLogicMixin:
    """Shared bridge GUI logic; subclasses must create widgets before _finalize_ui()."""

    def _init_bridge_state(self) -> None:
        self.bridge: Optional[SerialNetBridge] = None
        self._worker: Optional[BridgeAsyncThread] = None
        self._file_log: Optional[_FileSurveyLog] = None
        self._stopping = False
        self._start_gen = 0
        self._active_path: Optional[str] = None
        self._starting = False
        self._stop_guard_timer = QtCore.QTimer(self)
        self._stop_guard_timer.setSingleShot(True)
        self._stop_guard_timer.timeout.connect(self._stop_timeout_guard)
        self._start_watchdog_timer = QtCore.QTimer(self)
        self._start_watchdog_timer.setSingleShot(True)
        self._start_watchdog_timer.timeout.connect(self._start_watchdog_fired)
        self._pending_ui: Deque[str] = deque()
        self._ui_drops = 0
        self._log_flush_timer = QtCore.QTimer(self)
        self._log_flush_timer.timeout.connect(self._flush_ui_log)
        self._stats_timer = QtCore.QTimer(self)
        self._stats_timer.timeout.connect(self._tick_stats)
        self._stats_popout_window: Optional[SurveyStatsPopout] = None
        self._splitter_sizes_backup: Optional[list[int]] = None
        self._diag_qprocess: Optional[QtCore.QProcess] = None
        self._diag_current_title = ""
        self._ui_log_serial_dup_last: Optional[str] = None
        self._ui_log_serial_dup_mono: float = 0.0

    def _reset_ui_log_serial_coalesce(self) -> None:
        self._ui_log_serial_dup_last = None
        self._ui_log_serial_dup_mono = 0.0

    def _finalize_ui(self) -> None:
        lay = self.layout()
        if isinstance(lay, QtWidgets.QVBoxLayout) and not getattr(self, "_survey_menu_placed", False):
            lay.insertWidget(0, self._create_survey_menu_bar())
            self._survey_menu_placed = True

        from ui.controls import wire_connection_controls
        wire_connection_controls(self)
        self.refresh_ports()
        self._mode_toggle()
        self._log_flush_timer.start(UI_LOG_FLUSH_MS)
        self._stats_timer.start(400)
        self._on_ui_ready()

    def _create_survey_menu_bar(self) -> QtWidgets.QMenuBar:
        mb = QtWidgets.QMenuBar(self)
        vm = mb.addMenu("&View")

        act_fs = QtGui.QAction("Full screen", self)
        act_fs.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_F11))
        act_fs.setStatusTip("Toggle full screen (survey / multi-monitor layouts)")
        act_fs.triggered.connect(self._toggle_fullscreen)
        self.addAction(act_fs)
        vm.addAction(act_fs)

        act_pop = QtGui.QAction("Pop out survey stats…", self)
        act_pop.setShortcut(QtGui.QKeySequence("Ctrl+Shift+S"))
        act_pop.setStatusTip("Large readable Hz / transport / totals for Hypack or a second monitor")
        act_pop.triggered.connect(self._open_stats_popout)
        self.addAction(act_pop)
        vm.addAction(act_pop)

        return mb

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            if self._splitter_sizes_backup and hasattr(self, "_splitter"):
                self._splitter.setSizes(self._splitter_sizes_backup)
                self._splitter_sizes_backup = None
        else:
            if hasattr(self, "_splitter"):
                self._splitter_sizes_backup = list(self._splitter.sizes())
                self._apply_fullscreen_splitter_bias()
            self.showFullScreen()

    def _apply_fullscreen_splitter_bias(self) -> None:
        """Give logs / tools a friendlier ratio on large displays."""
        sp = getattr(self, "_splitter", None)
        if sp is None:
            return
        o = sp.orientation()
        total = max(sum(sp.sizes()), 1)
        if o == QtCore.Qt.Orientation.Horizontal:
            # Standard: favor slightly more log width when very wide
            w = max(self.width(), total)
            tabs_w = int(w * 0.62)
            log_w = max(w - tabs_w, 200)
            sp.setSizes([tabs_w, log_w])
        else:
            h = max(self.height(), total)
            name = self.__class__.__name__.lower()
            if "logfirst" in name:
                top = int(h * 0.74)
                bot = max(h - top, 100)
                sp.setSizes([top, bot])
            else:
                # Minimal: more log height for survey noise
                top = int(h * 0.58)
                bot = max(h - top, 120)
                sp.setSizes([top, bot])

    def _open_stats_popout(self) -> None:
        pop = self._stats_popout_window
        if pop is not None:
            pop.show()
            pop.raise_()
            pop.activateWindow()
            self._refresh_stats_popout()
            return
        pop = SurveyStatsPopout(self)
        pop.destroyed.connect(self._on_stats_popout_destroyed)
        self._stats_popout_window = pop
        self._refresh_stats_popout()
        pop.show()
        pop.raise_()
        pop.activateWindow()

    def _on_stats_popout_destroyed(self, *_args: object) -> None:
        self._stats_popout_window = None

    def _refresh_stats_popout(self) -> None:
        pop = self._stats_popout_window
        if pop is None:
            return
        try:
            vis = pop.isVisible()
        except RuntimeError:
            self._stats_popout_window = None
            return
        if not vis:
            return
        pop.set_status_lines(self.status_serial.text(), self.status_network.text())
        pop.set_stats_text(self.lbl_stats.text(), self.lbl_stats.toolTip())

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        pop = getattr(self, "_stats_popout_window", None)
        if pop is not None:
            pop.close()
            self._stats_popout_window = None
        super().closeEvent(event)

    def _on_ui_ready(self) -> None:
        pass

    def _preflight_com(self, com: str, baud: int) -> Optional[str]:
        """Quick COM probe on GUI thread before async start."""
        try:
            ser = _open_serial_port_timed(com, baud, SERIAL_OPEN_TIMEOUT_S)
            ser.close()
            return None
        except Exception as exc:
            return _friendly_serial_error(exc, com)

    def _toggle_log_panel(self, visible: bool) -> None:
        self._splitter.widget(1).setVisible(visible)
        if visible:
            self._splitter.setSizes([520, 360])
        else:
            self._splitter.setSizes([900, 0])

    def _polish_widget(self, w: QtWidgets.QWidget) -> None:
        style = w.style()
        style.unpolish(w)
        style.polish(w)

    def _set_status_banner(self, state: str, title: str, detail: str = "") -> None:
        self.status_banner.setProperty("state", state)
        self._polish_widget(self.status_banner)
        text = title if not detail else f"{title}\n{detail}"
        self.status_banner_text.setText(text)

    def _set_active_path(self, path: Optional[str]) -> None:
        self._active_path = path
        self.btn_bench_preset.setProperty("active", path == "bench")
        self.btn_production_preset.setProperty("active", path == "production")
        self._polish_widget(self.btn_bench_preset)
        self._polish_widget(self.btn_production_preset)
        self._refresh_intent_hint()

    def _refresh_intent_hint(self) -> None:
        if self.rb_udp_remote.isChecked():
            self.intent_hint.setText(
                "⚠ Wrong mode: UDP remote is for talking to a fixed peer. "
                "For INS/simulator tests use Desk or Boat path (UDP listen)."
            )
            return
        if not self.rb_udp_listen.isChecked() and self.chk_advanced_net.isChecked():
            self.intent_hint.setText(
                "TCP mode selected — only use if your device speaks TCP, not UDP NMEA."
            )
            return
        if self._active_path == "bench":
            com = self.com_cb.currentText() or "COM?"
            self.intent_hint.setText(
                f"Desk test: bridge owns {com}. Send UDP to 127.0.0.1:{self.udp_port.text()}. "
                f"Watch the paired com0com port (e.g. COM12), not {com}. "
                f"Do not open Tera Term on {com}."
            )
        elif self._active_path == "production":
            d = load_production_defaults()
            self.intent_hint.setText(
                f"Boat: INS sends UDP to {d.get('pc_ip', 'PC IP')}:{self.udp_port.text()} → "
                f"{self.com_cb.currentText() or 'COM?'}. "
                "Close Mission Planner on that COM while bridging."
            )
        else:
            self.intent_hint.setText(
                "Choose Desk test or Boat / INS above, then Start. "
                "The bridge listens on UDP; your device must send NMEA to this PC."
            )

    def _validate_before_start(self) -> Optional[str]:
        if self._worker and self._worker.isRunning():
            return "Bridge is still stopping. Wait a moment, then try again."
        if self._starting:
            return "Start already in progress."
        if not self.com_cb.currentText().strip():
            return "Select a COM port (Refresh ports if the list is empty)."
        if self._active_path is None:
            return "Choose Desk test or Boat / INS first — this sets the correct UDP mode."
        if self.rb_udp_remote.isChecked():
            return (
                "UDP remote is wrong for INS/bench. Click Desk test or Boat / INS, "
                "or enable Advanced and select UDP listen."
            )
        if not self.rb_udp_listen.isChecked():
            return "For standard NMEA UDP, select UDP listen (use Desk/Boat path or Advanced)."
        try:
            baud = int(self.baud_edit.text())
            if baud <= 0:
                raise ValueError
        except ValueError:
            return "Enter a valid baud rate (e.g. 115200)."
        try:
            _parse_port(self.udp_port.text(), "UDP port")
        except ValueError as e:
            return str(e)
        return None

    def _apply_com_preset(self, com: str, baud: int, udp_host: str, udp_port: int) -> None:
        idx = self.com_cb.findText(com)
        if idx >= 0:
            self.com_cb.setCurrentIndex(idx)
        else:
            self.com_cb.addItem(com)
            self.com_cb.setCurrentText(com)
        self.baud_edit.setText(str(baud))
        self.rb_udp_listen.setChecked(True)
        self.udp_host.setText(udp_host)
        self.udp_port.setText(str(udp_port))
        self.rb_nmea_passthrough.setChecked(True)
        self.chk_show_log.setChecked(True)
        self._toggle_log_panel(True)
        self.chk_verbose_log.setChecked(True)
        self._mode_toggle()
        self._refresh_intent_hint()

    def _apply_bench_preset(self) -> None:
        """Bench: UDP listen -> COM from bench_defaults.json (com0com / localhost)."""
        d = load_bench_defaults()
        com = str(d["com"])
        baud = int(d["baud"])
        udp_host = str(d["udp_host"])
        udp_port = int(d["udp_port"])
        self._apply_com_preset(com, baud, udp_host, udp_port)
        self._set_active_path("bench")
        self._log_ui(
            f"Bench preset: {com} + UDP LISTEN {udp_host}:{udp_port}. "
            f"Test with 127.0.0.1:{udp_port} (python nmea_static_edh.py). "
            f"Watch paired COM (e.g. COM12), not {com}."
        )

    def _apply_production_preset(self) -> None:
        """Boat: INS UDP -> bridge -> physical COM -> Cube (edit production in bench_defaults.json)."""
        d = load_production_defaults()
        com = str(d["com"])
        baud = int(d["baud"])
        udp_host = str(d["udp_host"])
        udp_port = int(d["udp_port"])
        pc_ip = str(d.get("pc_ip", "192.168.1.10"))
        ins_ip = str(d.get("ins_ip", ""))
        mask = str(d.get("subnet_mask", "255.255.255.0"))
        notes = str(d.get("notes", "")).strip()
        self._apply_com_preset(com, baud, udp_host, udp_port)
        self._set_active_path("production")
        lines = [
            f"Production preset: {com} @ {baud}, UDP LISTEN {udp_host}:{udp_port}.",
            f"Survey PC Ethernet: {pc_ip} / {mask} (static recommended).",
            f"Configure INS NMEA UDP output -> {pc_ip}:{udp_port} (INS often {ins_ip}).",
            "Start bridge BEFORE opening Mission Planner on the Cube COM.",
            "MP sees position via the autopilot UART — not this PC's COM GPS.",
        ]
        if notes:
            lines.append(notes)
        self._log_ui("\n".join(lines))


    def _on_advanced_net_toggle(self, checked: bool) -> None:
        self._advanced_net.setVisible(checked)
        self._mode_toggle()


    def _selected_nmea_mode(self) -> NmeaMode:
        return NmeaMode.STRICT if self.rb_nmea_strict.isChecked() else NmeaMode.PASSTHROUGH

    def _selected_nmea_filter(self) -> NmeaFilter:
        enabled = {st for st, cb in self._nmea_type_checks.items() if cb.isChecked()}
        return NmeaFilter(enabled_types=enabled)


    def _insert_send_sample(self) -> None:
        when = datetime.now(timezone.utc)
        gga = build_gga(when, EDH_LAT_DEG, EDH_LON_DEG, EDH_ALT_M)
        rmc = build_rmc(when, EDH_LAT_DEG, EDH_LON_DEG)
        self.send_edit.setPlainText(f"{gga}\r\n{rmc}")


    def _browse_log(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Survey log file", self.file_log_path.text(), "Log files (*.log);;All files (*)")
        if path:
            self.file_log_path.setText(path)

    def _mode_toggle(self, *_args) -> None:
        m_udp_l = self.rb_udp_listen.isChecked()
        m_udp_r = self.rb_udp_remote.isChecked()
        m_tcp_s = self.rb_tcp_server.isChecked()
        m_tcp_c = self.rb_tcp_client.isChecked()

        self._udp_box.setVisible(m_udp_l or m_udp_r)
        self.udp_host.setEnabled(m_udp_l)
        self.udp_port.setEnabled(m_udp_l or m_udp_r)
        self.remote_host.setEnabled(m_udp_r)
        self.remote_port.setEnabled(m_udp_r)

        self._tcp_srv_box.setVisible(m_tcp_s)
        self._tcp_cli_box.setVisible(m_tcp_c)
        self.tcp_srv_host.setEnabled(m_tcp_s)
        self.tcp_srv_port.setEnabled(m_tcp_s)
        self.tcp_cli_host.setEnabled(m_tcp_c)
        self.tcp_cli_port.setEnabled(m_tcp_c)
        self._refresh_intent_hint()
        self.tcp_reconnect_spin.setEnabled(m_tcp_c)

    def _enqueue_ui(self, line: str) -> None:
        while len(self._pending_ui) >= UI_LOG_PENDING_MAX:
            self._pending_ui.popleft()
            self._ui_drops += 1
        self._pending_ui.append(line)

    def _flush_ui_log(self) -> None:
        if not self._pending_ui:
            return
        n = min(UI_LOG_MAX_LINES_PER_FLUSH, len(self._pending_ui))
        chunk = [self._pending_ui.popleft() for _ in range(n)]
        self.log_view.appendPlainText("\n".join(chunk))
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _log_ui(self, txt: str) -> None:
        if self._should_coalesce_serial_gui_log(txt):
            return
        self._enqueue_ui(txt)

    def _should_coalesce_serial_gui_log(self, txt: str, window_s: float = 2.5) -> bool:
        """Live log: drop repeat ``Serial COMx: timed out (open/write).`` within window."""
        suppress, last, mono = serial_timeout_line_suppress(
            self._ui_log_serial_dup_last,
            self._ui_log_serial_dup_mono,
            txt,
            window_s=window_s,
        )
        self._ui_log_serial_dup_last = last
        self._ui_log_serial_dup_mono = mono
        return suppress

    def _update_status_bar(self, serial_line: str, network_line: str) -> None:
        self.status_serial.setText(serial_line)
        self.status_network.setText(network_line)
        self._refresh_stats_popout()

    def _set_connection_locked(self, locked: bool) -> None:
        for w in self._connection_widgets:
            w.setEnabled(not locked)
        for w in getattr(self, "_nmea_widgets", []):
            w.setEnabled(not locked)
        self.start_btn.setEnabled(not locked)
        self.stop_btn.setEnabled(locked)

    def _stats_tooltip(self) -> str:
        return (
            "Live QA (this session)\n\n"
            "↓ Hz — Complete NMEA sentences per second from UDP/TCP toward the serial port "
            "(rolling 1 s window). Matches what your simulator/INS sends after line assembly — "
            "not raw packet count.\n"
            "↑ Hz — Sentences per second from COM toward the network.\n"
            "Send→COM …/s — Only when the Send tab is actively injecting at ≥ ~0.05/s "
            "(rolling 1 s). Does not add to ↓ Hz.\n\n"
            "transport OK — No queue drops, no rejects, and both write queues empty.\n"
            "If something is wrong, the bar spells it out (drops / rejects / queued chunks).\n\n"
            "session totals — Lifetime sentences forwarded: remote →COM (UDP/TCP) and COM→net.\n\n"
            "Live log: identical “Serial … timed out (open/write).” lines are shown at most once per ~2.5 s "
            "(same window as the bridge engine; avoids spam during stress or Stop)."
        )

    def _starting_network_blurb(self) -> str:
        if self.rb_udp_listen.isChecked():
            return f"UDP listen {self.udp_host.text().strip()}:{self.udp_port.text().strip()}"
        if self.rb_udp_remote.isChecked():
            return f"UDP remote {self.remote_host.text().strip()}:{self.remote_port.text().strip()}"
        if self.rb_tcp_server.isChecked():
            return f"TCP server {self.tcp_srv_host.text().strip()}:{self.tcp_srv_port.text().strip()}"
        return f"TCP client {self.tcp_cli_host.text().strip()}:{self.tcp_cli_port.text().strip()}"

    def _running_banner_detail(self, b: SerialNetBridge) -> str:
        if b.mode == NetMode.UDP_LISTEN and b.udp_listen:
            host, port = b.udp_listen
            return f"{b.com} @ {b.baud} — UDP listen {host}:{port}"
        if b.mode == NetMode.UDP_REMOTE and b.udp_remote:
            host, port = b.udp_remote
            return f"{b.com} @ {b.baud} — UDP → {host}:{port}"
        if b.mode == NetMode.TCP_SERVER:
            return f"{b.com} @ {b.baud} — TCP server {b.tcp_bind_host}:{b.tcp_bind_port}"
        if b.mode == NetMode.TCP_CLIENT:
            return f"{b.com} @ {b.baud} — TCP client → {b.tcp_client_host}:{b.tcp_client_port}"
        return f"{b.com} @ {b.baud}"

    def _merge_bridge_stats(self, base: Optional[dict] = None) -> dict:
        b = self.bridge
        if not b:
            return {}
        _ = base  # worker may send partial snapshots; always read live counters
        return {
            "drops_n2s": b.drops_net_to_serial,
            "drops_s2n": b.drops_serial_to_net,
            "rej_n2s": b.rejected_net_to_serial,
            "rej_s2n": b.rejected_serial_to_net,
            "n2s_q": b.net_to_serial.qsize(),
            "s2n_q": b.serial_to_net.qsize(),
            "hz_down": b.hz_remote_to_serial(),
            "hz_gui": b.hz_gui_to_serial(),
            "hz_up": b.hz_serial_to_net(),
            "lines_down": b.lines_remote_to_serial,
            "lines_up": b.lines_serial_to_net,
        }

    def _stats_from_bridge(self, _d: dict) -> None:
        if not self.bridge:
            return
        merged = self._merge_bridge_stats(_d)
        self.lbl_stats.setText(format_live_stats_line(merged))
        self.lbl_stats.setToolTip(self._stats_tooltip())
        self._refresh_stats_popout()

    def _tick_stats(self) -> None:
        if self.bridge:
            self._stats_from_bridge({})
        else:
            self.lbl_stats.setText(
                "Stopped — live Hz, transport health, and session totals appear here when Running (hover)"
            )
            self.lbl_stats.setToolTip(self._stats_tooltip())
            self._refresh_stats_popout()

    def _diag_udp_port(self) -> Optional[int]:
        try:
            return _parse_port(self.udp_port.text(), "UDP port")
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self,
                "Diagnostics",
                "Enter a valid UDP listen port on the Connect tab first.",
            )
            return None

    def _diag_set_running_ui(self, running: bool) -> None:
        for b in getattr(self, "_diag_run_buttons", ()):
            b.setEnabled(not running)
        if hasattr(self, "btn_diag_stop"):
            self.btn_diag_stop.setEnabled(running)

    def _append_diag_output(self, text: str) -> None:
        if not hasattr(self, "diag_output"):
            return
        self.diag_output.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.diag_output.insertPlainText(text)
        self.diag_output.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        if getattr(self, "chk_diag_mirror_log", None) and self.chk_diag_mirror_log.isChecked():
            for line in text.splitlines():
                if line.strip():
                    self._log_ui(line)

    def _diag_start_script(self, title: str, script: str, args: list[str]) -> None:
        if self._diag_qprocess is not None and self._diag_qprocess.state() != QtCore.QProcess.ProcessState.NotRunning:
            self._append_diag_output("A check is already running — press Stop or wait for it to finish.\n")
            return
        self.diag_output.clear()
        self._diag_current_title = title
        exe = cli_python_executable()
        rel = _REPO_ROOT / script
        cmd = f"{exe} {rel.name} {' '.join(args)}".strip()
        self._append_diag_output(f"$ {cmd}\n(working dir: {_REPO_ROOT})\n\n")
        self.diag_status_label.setText(f"Running: {title}…")
        self._diag_set_running_ui(True)

        proc = QtCore.QProcess(self)
        proc.setProgram(exe)
        proc.setArguments([str(rel), *args])
        proc.setWorkingDirectory(str(_REPO_ROOT))
        proc.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.SeparateChannels)
        proc.readyReadStandardOutput.connect(self._diag_on_stdout)
        proc.readyReadStandardError.connect(self._diag_on_stderr)
        proc.finished.connect(self._diag_on_finished)
        proc.errorOccurred.connect(self._diag_on_error)
        self._diag_qprocess = proc
        proc.start()

    def _diag_on_stdout(self) -> None:
        p = self._diag_qprocess
        if not p:
            return
        self._append_diag_output(bytes(p.readAllStandardOutput()).decode(errors="replace"))

    def _diag_on_stderr(self) -> None:
        p = self._diag_qprocess
        if not p:
            return
        self._append_diag_output(bytes(p.readAllStandardError()).decode(errors="replace"))

    def _diag_on_error(self, error: QtCore.QProcess.ProcessError) -> None:
        self._append_diag_output(f"\n[process error: {int(error)}]\n")

    def _diag_on_finished(self, exit_code: int, exit_status: QtCore.QProcess.ExitStatus) -> None:
        p = self.sender()
        if p is not self._diag_qprocess:
            return
        normal = exit_status == QtCore.QProcess.ExitStatus.NormalExit
        ok = normal and exit_code == 0
        label = "PASS" if ok else "FAIL"
        self.diag_status_label.setText(
            f"Finished: {self._diag_current_title} — exit code {exit_code} — {label}"
        )
        self._append_diag_output(f"\n--- done (exit {exit_code}) — {label} ---\n")
        self._diag_set_running_ui(False)
        self._diag_qprocess = None
        p.deleteLater()

    def _diag_stop(self) -> None:
        if self._diag_qprocess and self._diag_qprocess.state() != QtCore.QProcess.ProcessState.NotRunning:
            self._diag_qprocess.kill()
            self._append_diag_output("\n[stopped by user]\n")

    def _diag_run_verify_all(self) -> None:
        self._diag_start_script("verify_all (full automated suite)", "verify_all.py", [])

    def _diag_run_com_free(self) -> None:
        args: list[str] = []
        com = self.com_cb.currentText().strip()
        if com:
            args.extend(["--com", com])
        try:
            baud = int(self.baud_edit.text().strip())
            if baud > 0:
                args.extend(["--baud", str(baud)])
        except ValueError:
            pass
        self._diag_start_script("com_free (COM port availability)", "com_free.py", args)

    def _diag_run_check_setup(self) -> None:
        port = self._diag_udp_port()
        if port is None:
            return
        self._diag_start_script("check_setup (UDP + COM hints)", "check_setup.py", ["--port", str(port)])

    def _diag_run_check_setup_production(self) -> None:
        port = self._diag_udp_port()
        if port is None:
            return
        self._diag_start_script("check_setup --production", "check_setup.py", ["--port", str(port), "--production"])

    def _diag_run_udp_sample(self) -> None:
        port = self._diag_udp_port()
        if port is None:
            return
        self._diag_start_script(
            "nmea_static_edh (2.5 s UDP burst @ 5 Hz)",
            "nmea_static_edh.py",
            ["--dest-host", "127.0.0.1", "--dest-port", str(port), "--duration", "2.5", "--quiet"],
        )

    def refresh_ports(self) -> None:
        self.com_cb.clear()
        for p in serial.tools.list_ports.comports():
            self.com_cb.addItem(p.device)

    def _send_manual(self, where: str) -> None:
        if not self.bridge or not self.bridge.running:
            self._log_ui(
                "Send: bridge not running — Connect tab: choose path, Start, wait for Running."
            )
            return
        raw = self.send_edit.toPlainText()
        data = _nmea_line_bytes(raw)
        if not data:
            self._log_ui(
                "Send: box is empty — type/paste NMEA in tab 3, or click Insert EDH sample GGA."
            )
            return
        self._log_ui(f"Send: {len(data)} bytes -> {where}")
        b = self.bridge
        w = self._worker

        def _do() -> None:
            if not b.running:
                return
            if where == "serial":
                b.schedule_net_to_serial(data, "GUI→SER")
            elif where == "net":
                b.schedule_serial_to_net(data, "GUI→NET")
            else:
                b.schedule_net_to_serial(data, "GUI→SER")
                b.schedule_serial_to_net(data, "GUI→NET")

        if w:
            w.call_on_loop(_do)
        else:
            _do()

    def start_bridge(self) -> None:
        err = self._validate_before_start()
        if err:
            self._log_ui(err)
            QtWidgets.QMessageBox.warning(self, "Cannot start", err)
            return
        com = self.com_cb.currentText().strip()
        try:
            baud = int(self.baud_edit.text())
            if baud <= 0:
                raise ValueError("baud must be positive")
        except ValueError:
            self._log_ui("Invalid baud rate — enter a positive number (e.g. 115200).")
            QtWidgets.QMessageBox.warning(self, "Cannot start", "Enter a valid baud rate.")
            return

        if self.chk_file_log.isChecked():
            try:
                self._file_log = _FileSurveyLog(Path(self.file_log_path.text().strip()))
            except Exception as e:
                self._log_ui(f"File log error: {e}")
                QtWidgets.QMessageBox.warning(self, "File log", f"Could not open log file:\n{e}")
                self._file_log = None
        else:
            self._file_log = None

        udp_listen = None
        udp_remote = None
        mode: NetMode
        tcp_reconnect = self.tcp_reconnect_spin.value()

        try:
            if self.rb_udp_listen.isChecked():
                mode = NetMode.UDP_LISTEN
                udp_listen = (self.udp_host.text().strip(), _parse_port(self.udp_port.text(), "UDP port"))
            elif self.rb_udp_remote.isChecked():
                mode = NetMode.UDP_REMOTE
                host = self.remote_host.text().strip()
                if not host:
                    raise ValueError("UDP remote host is required")
                udp_remote = (host, _parse_port(self.remote_port.text(), "UDP remote port"))
            elif self.rb_tcp_server.isChecked():
                mode = NetMode.TCP_SERVER
                tcp_bh = self.tcp_srv_host.text().strip()
                tcp_bp = _parse_port(self.tcp_srv_port.text(), "TCP server port")
            else:
                mode = NetMode.TCP_CLIENT
                tcp_ch = self.tcp_cli_host.text().strip()
                if not tcp_ch:
                    raise ValueError("TCP client host is required")
                tcp_cp = _parse_port(self.tcp_cli_port.text(), "TCP client port")
        except ValueError as e:
            self._log_ui(str(e))
            QtWidgets.QMessageBox.warning(self, "Cannot start", str(e))
            return

        if self._worker and self._worker.isRunning():
            self._log_ui("Stop the bridge before starting again.")
            return

        file_log = self._file_log
        nmea_mode = self._selected_nmea_mode()
        nmea_filter = self._selected_nmea_filter()
        verbose = self.chk_verbose_log.isChecked

        def build(loop: asyncio.AbstractEventLoop) -> SerialNetBridge:
            common = dict(
                loop=loop,
                ui_log=self._worker.log_msg.emit,
                ui_log_verbose=verbose,
                status_cb=self._worker.status_msg.emit,
                stats_cb=self._worker.stats_msg.emit,
                file_log=file_log,
                tcp_reconnect_delay=tcp_reconnect,
                nmea_mode=nmea_mode,
                nmea_filter=nmea_filter,
            )
            if mode == NetMode.TCP_SERVER:
                return SerialNetBridge(
                    com, baud, mode, tcp_bind_host=tcp_bh, tcp_bind_port=tcp_bp, **common
                )
            if mode == NetMode.TCP_CLIENT:
                return SerialNetBridge(
                    com, baud, mode, tcp_client_host=tcp_ch, tcp_client_port=tcp_cp, **common
                )
            return SerialNetBridge(
                com, baud, mode, udp_listen=udp_listen, udp_remote=udp_remote, **common
            )

        self._set_connection_locked(True)
        self._update_status_bar("Serial: starting…", "Network: starting…")
        self._starting = True
        self._set_status_banner(
            "starting",
            "Starting…",
            f"Opening {com} @ {baud} — {self._starting_network_blurb()}",
        )
        self._start_gen += 1
        gen = self._start_gen
        self._log_ui(f"Start: opening {com} @ {baud} (background thread)…")

        self._worker = BridgeAsyncThread(build)
        self._worker.log_msg.connect(self._log_ui)
        self._worker.status_msg.connect(self._update_status_bar)
        self._worker.stats_msg.connect(self._stats_from_bridge)
        self._worker.start_done.connect(lambda ok: self._on_worker_start_done(ok, gen))
        self._start_watchdog_timer.start(START_WATCHDOG_MS)
        self._worker.start()

    def _on_worker_start_done(self, ok: bool, gen: int) -> None:
        self._start_watchdog_timer.stop()
        if gen != self._start_gen:
            return
        worker = self._worker
        if ok and worker and worker.bridge:
            self.bridge = worker.bridge
            self._on_bridge_started(self.bridge)
            return
        if worker:
            worker.request_stop()
            worker.wait(3000)
        self._worker = None
        self.bridge = None
        self._fail_start_ui(
            "Serial or network could not be opened. See the live log for details."
        )

    def _fail_start_ui(self, message: str) -> None:
        self.bridge = None
        if self._worker and self._worker.isRunning():
            self._worker.request_stop()
            self._worker.wait(2000)
        self._worker = None
        if self._file_log:
            self._file_log.close()
            self._file_log = None
        self._set_connection_locked(False)
        self._update_status_bar("Serial: stopped", "Network: stopped")
        self._starting = False
        self._set_status_banner("failed", "Start failed", message)
        self.start_btn.setText("Start bridge")
        QtWidgets.QMessageBox.critical(self, "Bridge failed to start", message)

    def _start_watchdog_fired(self) -> None:
        worker = self._worker
        b = self.bridge or (worker.bridge if worker else None)
        if b and b.running and b._network_ready:
            return
        self._start_gen += 1
        self._log_ui(
            "Start timed out (>15s).\n"
            "Close the app, run: python com_free.py, then launch again."
        )
        if worker:
            worker.request_stop()
            worker.wait(3000)
        self._fail_start_ui(
            "Start timed out after 15 seconds.\n\n"
            "Close any app using the COM port, run python com_free.py, then try again."
        )

    def _on_bridge_started(self, b: SerialNetBridge) -> None:
        self._starting = False
        self._reset_ui_log_serial_coalesce()
        self._set_status_banner("running", "Running", self._running_banner_detail(b))
        self.start_btn.setText("Running…")
        if b.mode == NetMode.UDP_LISTEN and b.udp_listen:
            host, port = b.udp_listen
            dest = f"127.0.0.1:{port}" if host in ("0.0.0.0", "", "::") else f"{host}:{port}"
            self._log_ui(
                "=== BRIDGE RUNNING ===\n"
                f"UDP listen {host}:{port} -> {b.com} @ {b.baud}.\n"
                "The bridge is idle until NMEA arrives — that is normal.\n"
                f"Send traffic to {dest} (e.g. python nmea_static_edh.py), or Tab 3 Send -> serial.\n"
                f"Watch paired COM (e.g. COM12) in Tera Term — not {b.com}."
            )
        else:
            self._log_ui(
                f"=== BRIDGE RUNNING === {b.com} @ {b.baud} ({b.mode.value}). "
                "Idle until data moves on the wire."
            )

    def stop_bridge(self) -> None:
        if self._stopping:
            self._finish_stop_ui()
            return
        worker = self._worker
        self.bridge = None
        self._worker = None
        if not worker:
            self._finish_stop_ui()
            return

        self._stopping = True
        self._update_status_bar("Serial: stopping…", "Network: stopping…")
        self._log_ui("Stopping bridge…")
        worker.request_stop()
        worker.wait(4000)
        self._finish_stop_ui()
        self._start_gen += 1
        self._start_watchdog_timer.stop()

    def _stop_timeout_guard(self) -> None:
        if not self._stopping:
            return
        self._log_ui(
            "Stop took too long — UI reset. Close Tera Term/PuTTY on the COM port, then try again."
        )
        self._finish_stop_ui()

    def _finish_stop_ui(self) -> None:
        """Re-enable controls on the Qt main thread after async stop."""
        self._reset_ui_log_serial_coalesce()
        self._stop_guard_timer.stop()
        self._stopping = False
        if self._file_log:
            self._file_log.close()
            self._file_log = None
        self._set_connection_locked(False)
        self.stop_btn.setText("■  Stop bridge")
        self._starting = False
        self.start_btn.setText("Start bridge")
        self._set_status_banner("stopped", "Stopped", "Choose a path and Start when ready.")
        self._update_status_bar("Serial: stopped", "Network: stopped")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        p = self._diag_qprocess
        if p is not None:
            if p.state() != QtCore.QProcess.ProcessState.NotRunning:
                p.kill()
                p.waitForFinished(2000)
            self._diag_qprocess = None
            p.deleteLater()
        running = self.bridge and self.bridge.running
        worker = self._worker
        if running or (worker and worker.isRunning()):
            event.ignore()
            self.bridge = None
            if worker:
                worker.request_stop()
                worker.wait(4000)
            self._worker = None
            self._finish_stop_ui()
            self._start_gen += 1
            QtCore.QTimer.singleShot(200, self.close)
            return
        event.accept()


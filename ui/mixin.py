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

    def _finalize_ui(self) -> None:
        from ui.controls import wire_connection_controls
        wire_connection_controls(self)
        self.refresh_ports()
        self._mode_toggle()
        self._log_flush_timer.start(UI_LOG_FLUSH_MS)
        self._stats_timer.start(400)
        self._on_ui_ready()

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
        self._enqueue_ui(txt)

    def _update_status_bar(self, serial_line: str, network_line: str) -> None:
        self.status_serial.setText(serial_line)
        self.status_network.setText(network_line)

    def _set_connection_locked(self, locked: bool) -> None:
        for w in self._connection_widgets:
            w.setEnabled(not locked)
        for w in getattr(self, "_nmea_widgets", []):
            w.setEnabled(not locked)
        self.start_btn.setEnabled(not locked)
        self.stop_btn.setEnabled(locked)

    def _stats_from_bridge(self, d: dict) -> None:
        self.lbl_stats.setText(
            f"Drops {d['drops_n2s']}/{d['drops_s2n']} | "
            f"Reject {d['rej_n2s']}/{d['rej_s2n']} | "
            f"Q {d['n2s_q']}/{d['s2n_q']}"
        )

    def _tick_stats(self) -> None:
        if self.bridge:
            self._stats_from_bridge(
                {
                    "drops_n2s": self.bridge.drops_net_to_serial,
                    "drops_s2n": self.bridge.drops_serial_to_net,
                    "rej_n2s": self.bridge.rejected_net_to_serial,
                    "rej_s2n": self.bridge.rejected_serial_to_net,
                    "n2s_q": self.bridge.net_to_serial.qsize(),
                    "s2n_q": self.bridge.serial_to_net.qsize(),
                }
            )
        else:
            self.lbl_stats.setText("Drops 0/0 | Reject 0/0 | Q 0/0")

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
        self._set_status_banner("starting", "Starting…", f"Opening {com} and UDP :{self.udp_port.text()}")
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
        self._set_status_banner("running", "Running", f"{b.com} @ {b.baud} — UDP listen :{b.udp_listen[1] if b.udp_listen else '?'}")
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


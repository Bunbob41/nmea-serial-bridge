"""Thread-safe bridge UI façade for Web control plane (no bridge protocol here)."""
from __future__ import annotations

import threading
import time
import weakref
from collections import deque
from typing import Any, Callable, Deque, List, Optional

from PySide6 import QtCore
from web_facade_types import (
    WEB_LOG_MAX_LINES,
    NetworkCardDto,
    SerialDeviceDto,
    WebCommandResult,
    WebConfigPayload,
    WebDiscoveryPayload,
    WebLogLine,
    WebLogPayload,
    WebMeta,
    WebSessionState,
    classify_web_log_line,
)


class BridgeAppFacade(QtCore.QObject):
    """Lives on Qt main thread; HTTP layer reads snapshot and queues commands here."""

    _dispatch_command = QtCore.Signal(object)
    _dispatch_read = QtCore.Signal(object)

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._window_ref: Optional[weakref.ReferenceType[Any]] = None
        self._lock = threading.Lock()
        self._snapshot = WebSessionState()
        self._command_lock = threading.Lock()
        self._last_facade_error: Optional[str] = None
        self._facade_publish_interval_s = 0.5
        self._last_publish_mono = 0.0
        self._discovery_lock = threading.Lock()
        self._discovery_payload = WebDiscoveryPayload()
        self._log_lock = threading.Lock()
        self._log_seq = 0
        self._log_lines: Deque[WebLogLine] = deque(maxlen=WEB_LOG_MAX_LINES)
        self._log_paused = False
        self._log_paused_dropped = 0
        self._dispatch_command.connect(self._run_dispatch_command)
        self._dispatch_read.connect(self._run_dispatch_read)

    def attach_window(self, window: Any) -> None:
        self._window_ref = weakref.ref(window)

    def _window(self) -> Any:
        if self._window_ref is not None:
            win = self._window_ref()
            if win is not None:
                return win
        # Facade is constructed as BridgeAppFacade(main_window) — parent is always
        # the bridge QWidget even when attach_window() was never called (subclass
        # _on_ui_ready overrides skipped mixin setup in releases before 1.8.2).
        parent = self.parent()
        if parent is not None and hasattr(parent, "_is_bridge_running"):
            return parent
        return None

    def commands_ready(self) -> bool:
        return self._window() is not None

    def update_snapshot(self, **fields: Any) -> None:
        now = time.monotonic()
        if now - self._last_publish_mono < self._facade_publish_interval_s:
            return
        self._last_publish_mono = now
        with self._lock:
            for key, value in fields.items():
                if hasattr(self._snapshot, key):
                    setattr(self._snapshot, key, value)
            self._snapshot.updated_mono = now

    def get_status(self) -> WebSessionState:
        with self._lock:
            return WebSessionState(**self._snapshot.to_dict())

    def get_config(self) -> WebConfigPayload:
        if self._window() is None:
            return WebConfigPayload()
        return self._invoke_read_on_main(self._read_config_from_window)

    def _read_config_from_window(self, win: Any) -> WebConfigPayload:
        from ui.connection_fields import parse_baud, read_baud_widget

        hub = getattr(win, "connection_hub", None)
        hub_id = hub.selected_device_id() if hub is not None else None
        manual = bool(getattr(win, "_manual_override_dirty", False))
        baud = parse_baud(read_baud_widget(win.baud_edit)) or 115200
        mode = "udp_listen"
        if getattr(win, "chk_advanced_net", None) and win.chk_advanced_net.isChecked():
            if win.rb_tcp_server.isChecked():
                mode = "tcp_server"
            elif win.rb_tcp_client.isChecked():
                mode = "tcp_client"
            elif win.rb_udp_remote.isChecked():
                mode = "udp_remote"
        nmea = "passthrough"
        try:
            nmea = win._selected_nmea_mode().value  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            port = int(win.udp_port.text().strip())
        except ValueError:
            port = 10110
        remote_host = ""
        remote_port = 10110
        if mode == "tcp_client":
            if hasattr(win, "tcp_cli_host"):
                remote_host = win.tcp_cli_host.text().strip()
            if hasattr(win, "tcp_cli_port"):
                try:
                    remote_port = int(win.tcp_cli_port.text().strip())
                except ValueError:
                    remote_port = 4001
        elif mode == "tcp_server":
            if hasattr(win, "tcp_srv_host"):
                remote_host = win.tcp_srv_host.text().strip()
            if hasattr(win, "tcp_srv_port"):
                try:
                    remote_port = int(win.tcp_srv_port.text().strip())
                except ValueError:
                    remote_port = 4001
        elif hasattr(win, "remote_host"):
            remote_host = win.remote_host.text().strip()
            if hasattr(win, "remote_port"):
                try:
                    remote_port = int(win.remote_port.text().strip())
                except ValueError:
                    remote_port = 10110
        return WebConfigPayload(
            com_port=win.com_cb.currentText().strip(),
            baud=baud,
            udp_listen_host=win.udp_host.text().strip(),
            udp_listen_port=port,
            nmea_mode=nmea,
            hub_device_id=hub_id,
            manual_override=manual,
            network_mode=mode,
            remote_host=remote_host,
            remote_port=remote_port,
        )

    def apply_config(self, patch: dict[str, Any]) -> WebCommandResult:
        return self._invoke_on_main(lambda w: self._apply_config_on_main(w, patch))

    def request_start(self) -> WebCommandResult:
        return self._invoke_on_main(self._start_on_main)

    def request_stop(self) -> WebCommandResult:
        return self._invoke_on_main(self._stop_on_main)

    def _invoke_read_on_main(
        self, fn: Callable[[Any], WebConfigPayload]
    ) -> WebConfigPayload:
        if self._window() is None:
            return WebConfigPayload()
        box: dict[str, WebConfigPayload] = {}
        done = threading.Event()
        self._dispatch_read.emit((fn, box, done))
        if not done.wait(timeout=5.0):
            return WebConfigPayload()
        return box.get("result", WebConfigPayload())

    @QtCore.Slot(object)
    def _run_dispatch_read(self, payload: object) -> None:
        fn, box, done = payload  # type: ignore[misc]
        try:
            win = self._window()
            if win is None:
                box["result"] = WebConfigPayload()
            else:
                box["result"] = fn(win)
        except Exception:
            box["result"] = WebConfigPayload()
        finally:
            done.set()

    def _invoke_on_main(self, fn: Callable[[Any], WebCommandResult]) -> WebCommandResult:
        if self._window() is None:
            return WebCommandResult(False, "Application window not available", "unavailable")
        if not self._command_lock.acquire(blocking=False):
            return WebCommandResult(False, "Another command is in progress", "busy")
        box: dict[str, WebCommandResult] = {}
        done = threading.Event()
        # HTTP runs on a worker thread with no Qt event loop; QTimer.singleShot would
        # never fire. Queued signal delivery runs this slot on the facade's thread.
        self._dispatch_command.emit((fn, box, done))
        if not done.wait(timeout=20.0):
            self._command_lock.release()
            return WebCommandResult(False, "Command timed out", "busy")
        return box.get("result", WebCommandResult(False, "No result", "error"))

    @QtCore.Slot(object)
    def _run_dispatch_command(self, payload: object) -> None:
        fn, box, done = payload  # type: ignore[misc]
        try:
            win = self._window()
            if win is None:
                box["result"] = WebCommandResult(
                    False, "Application window not available", "unavailable"
                )
            else:
                box["result"] = fn(win)
        except Exception as exc:
            box["result"] = WebCommandResult(False, str(exc), "error")
        finally:
            self._command_lock.release()
            done.set()

    def _start_on_main(self, win: Any) -> WebCommandResult:
        err = win._validate_before_start()
        if err:
            self._last_facade_error = err
            return WebCommandResult(False, err, "validation", "stopped")
        win.start_bridge()
        running = win._is_bridge_running()
        state = "running" if running else "starting"
        return WebCommandResult(True, "Bridge start requested", None, state)

    def _stop_on_main(self, win: Any) -> WebCommandResult:
        if win._is_bridge_running():
            win.stop_bridge()
            return WebCommandResult(True, "Bridge stop requested", None, "stopping")
        return WebCommandResult(True, "Bridge already stopped", None, "stopped")

    def _apply_config_on_main(self, win: Any, patch: dict[str, Any]) -> WebCommandResult:
        from ui.connection_fields import validate_baud, validate_udp_port

        unsupported = {
            "ntrip_caster",
            "ntrip_mount",
            "fanout",
            "tcp_sink",
            "discovery_refresh",
            "unlock_ports",
        }
        for key in patch:
            if key in unsupported:
                return WebCommandResult(
                    False,
                    f"Setting '{key}' is not supported via Web in this release",
                    "unsupported",
                )

        running = win._is_bridge_running()
        mutable_while_running = {"hub_device_id", "manual_override"}
        if running:
            for key in patch:
                if key not in mutable_while_running:
                    return WebCommandResult(
                        False,
                        "Stop the bridge before changing COM, baud, or network bind",
                        "running_guard",
                    )

        if "baud" in patch:
            err = validate_baud(str(patch["baud"]))
            if err:
                return WebCommandResult(False, err, "validation")
        if "udp_listen_port" in patch:
            err = validate_udp_port(str(patch["udp_listen_port"]))
            if err:
                return WebCommandResult(False, err, "validation")

        if "remote_host" in patch or "remote_port" in patch:
            mode = str(patch.get("network_mode", "")).strip()
            if not mode:
                if getattr(win, "rb_tcp_server", None) and win.rb_tcp_server.isChecked():
                    mode = "tcp_server"
                elif getattr(win, "rb_tcp_client", None) and win.rb_tcp_client.isChecked():
                    mode = "tcp_client"
                elif getattr(win, "rb_udp_remote", None) and win.rb_udp_remote.isChecked():
                    mode = "udp_remote"
                else:
                    mode = "udp_listen"
            host = str(patch.get("remote_host", "")).strip()
            port_text = str(patch.get("remote_port", "")).strip()
            if mode == "tcp_client":
                if "remote_host" in patch and hasattr(win, "tcp_cli_host"):
                    win.tcp_cli_host.setText(host)
                if "remote_port" in patch and hasattr(win, "tcp_cli_port"):
                    win.tcp_cli_port.setText(port_text or "4001")
            elif mode == "tcp_server":
                if "remote_host" in patch and hasattr(win, "tcp_srv_host"):
                    win.tcp_srv_host.setText(host or "0.0.0.0")
                if "remote_port" in patch and hasattr(win, "tcp_srv_port"):
                    win.tcp_srv_port.setText(port_text or "4001")
            else:
                if "remote_host" in patch and hasattr(win, "remote_host"):
                    win.remote_host.setText(host)
                if "remote_port" in patch and hasattr(win, "remote_port"):
                    win.remote_port.setText(port_text or "10110")
        if "network_mode" in patch:
            mode = str(patch["network_mode"]).strip()
            adv = getattr(win, "chk_advanced_net", None)
            if adv is not None:
                adv.setChecked(mode != "udp_listen")
            rb_map = {
                "udp_listen": getattr(win, "rb_udp_listen", None),
                "udp_remote": getattr(win, "rb_udp_remote", None),
                "tcp_client": getattr(win, "rb_tcp_client", None),
                "tcp_server": getattr(win, "rb_tcp_server", None),
            }
            rb = rb_map.get(mode)
            if rb is not None:
                rb.setChecked(True)
            if hasattr(win, "_mode_toggle"):
                win._mode_toggle()
        if "hub_device_id" in patch and patch["hub_device_id"]:
            device_id = str(patch["hub_device_id"])
            hub = getattr(win, "connection_hub", None)
            if hub is not None:
                win._on_hub_selection(device_id)
            else:
                from discovery_service import resolve_network_bind_from_device_id

                if device_id.startswith("config:"):
                    port = device_id.split(":", 1)[1].strip()
                    if port:
                        idx = win.com_cb.findText(port)
                        if idx >= 0:
                            win.com_cb.setCurrentIndex(idx)
                        else:
                            win.com_cb.setCurrentText(port)
                elif device_id.startswith("serial:"):
                    port = device_id.split(":", 1)[-1].strip()
                    if port and not port.startswith("serial"):
                        idx = win.com_cb.findText(port)
                        if idx >= 0:
                            win.com_cb.setCurrentIndex(idx)
                        else:
                            win.com_cb.setCurrentText(port)
                bind = resolve_network_bind_from_device_id(device_id)
                if bind is not None:
                    host, port = bind
                    rb = getattr(win, "rb_udp_listen", None)
                    if rb is not None:
                        rb.setChecked(True)
                    win.udp_host.setText(host)
                    win.udp_port.setText(str(port))
                    if hasattr(win, "_mode_toggle"):
                        win._mode_toggle()
        if "udp_listen_host" in patch:
            win.udp_host.setText(str(patch["udp_listen_host"]).strip() or "0.0.0.0")
        if "udp_listen_port" in patch:
            win.udp_port.setText(str(int(patch["udp_listen_port"])))
        listen_mode = str(patch.get("network_mode", "")).strip() or "udp_listen"
        if (
            listen_mode == "udp_listen"
            and ("udp_listen_host" in patch or "udp_listen_port" in patch)
            and hasattr(win, "_mode_toggle")
        ):
            rb = getattr(win, "rb_udp_listen", None)
            if rb is not None:
                rb.setChecked(True)
            adv = getattr(win, "chk_advanced_net", None)
            if adv is not None:
                adv.setChecked(False)
            win._mode_toggle()
        if "manual_override" in patch:
            hub = getattr(win, "connection_hub", None)
            if hub is not None:
                hub.set_manual_override(bool(patch["manual_override"]))
        # Apply explicit COM/baud after hub selection so web/dashboard picks are not
        # overwritten by Connection Hub last-known-good presets.
        if "com_port" in patch:
            text = str(patch["com_port"]).strip()
            idx = win.com_cb.findText(text)
            if idx >= 0:
                win.com_cb.setCurrentIndex(idx)
            else:
                win.com_cb.setCurrentText(text)
        if "baud" in patch:
            from ui.connection_fields import coerce_baud, write_baud_widget

            write_baud_widget(win.baud_edit, int(patch["baud"]))

        return WebCommandResult(True, "Configuration updated", None, "running" if running else "stopped")

    # ------------------------------------------------------------------ discovery
    def update_discovery_snapshot(self, snap: Any) -> None:
        """Called on Qt main thread after hub discovery updates (T006)."""
        try:
            from discovery_service import DiscoverySnapshot

            if not isinstance(snap, DiscoverySnapshot):
                return
            serials = [
                SerialDeviceDto(
                    device_id=d.device_id,
                    port=d.port,
                    description=d.description,
                    manufacturer=d.manufacturer,
                    match_keyword=d.match_keyword,
                    status=d.status,
                )
                for d in snap.serial_devices
            ]
            networks = [
                NetworkCardDto(
                    device_id=c.device_id,
                    label=c.label,
                    mode_hint=c.mode_hint,
                    host=c.host,
                    port=c.port,
                    port_available=c.port_available,
                    peer_count=c.peer_count,
                    status=c.status,
                    discovery_source=c.discovery_source,
                )
                for c in snap.network_cards
            ]
            with self._discovery_lock:
                self._discovery_payload = WebDiscoveryPayload(
                    updated_mono=snap.mono_ts,
                    scan_note=getattr(snap, "scan_note", ""),
                    scan_busy=False,
                    serial_devices=serials,
                    network_cards=networks,
                    errors=list(getattr(snap, "errors", [])),
                )
        except Exception:
            pass

    def get_discovery(self) -> WebDiscoveryPayload:
        with self._discovery_lock:
            return self._discovery_payload

    def set_discovery_scan_busy(self, busy: bool) -> None:
        """Web dashboard: scan spinner while LAN/COM discovery worker runs."""
        self._set_discovery_busy(busy)

    def _set_discovery_busy(self, busy: bool) -> None:
        with self._discovery_lock:
            old = self._discovery_payload
            self._discovery_payload = WebDiscoveryPayload(
                updated_mono=old.updated_mono,
                scan_note=old.scan_note,
                scan_busy=busy,
                serial_devices=old.serial_devices,
                network_cards=old.network_cards,
                errors=old.errors,
            )

    def request_refresh_discovery(self) -> WebCommandResult:
        return self._invoke_on_main(self._refresh_discovery_on_main)

    def request_refresh_serial_ports(self) -> WebCommandResult:
        """Rescan COM ports only (fast; no LAN scan). Updates web discovery snapshot."""
        return self._invoke_on_main(self._refresh_serial_ports_on_main)

    def _refresh_serial_ports_on_main(self, win: Any) -> WebCommandResult:
        try:
            if hasattr(win, "refresh_ports"):
                win.refresh_ports()
            if hasattr(win, "_poll_discovery_snapshot"):
                win._poll_discovery_snapshot()
            n = len(self.get_discovery().serial_devices)
            return WebCommandResult(
                True,
                f"Found {n} serial port(s)" if n else "No serial ports detected on this PC",
                None,
                "ok",
            )
        except Exception as exc:
            return WebCommandResult(False, str(exc), "error")

    def _refresh_discovery_on_main(self, win: Any) -> WebCommandResult:
        try:
            win._on_hub_refresh_discovery()
            self._set_discovery_busy(True)
            return WebCommandResult(True, "Discovery scan started", None, "scanning")
        except Exception as exc:
            return WebCommandResult(False, str(exc), "error")

    def request_unlock_ports(self) -> WebCommandResult:
        ctx: dict[str, Any] = {}

        def _prepare(win: Any) -> WebCommandResult:
            from ui.connection_fields import parse_baud, read_baud_widget

            com = win.com_cb.currentText().strip()
            if not com:
                return WebCommandResult(False, "No COM port configured", "validation")
            ctx["com"] = com
            ctx["baud"] = parse_baud(read_baud_widget(win.baud_edit)) or 115200
            ctx["running"] = win._is_bridge_running()
            bridge = getattr(win, "bridge", None)
            ctx["bridge_com"] = bridge.com if bridge is not None else None
            try:
                ctx["udp_port"] = int(win.udp_port.text().strip())
            except (ValueError, AttributeError):
                ctx["udp_port"] = 10110
            try:
                ctx["udp_host"] = win.udp_host.text().strip() or "0.0.0.0"
            except AttributeError:
                ctx["udp_host"] = "0.0.0.0"
            return WebCommandResult(True, "", None, "stopped")

        prep = self._invoke_on_main(_prepare)
        if not prep.ok:
            return prep
        try:
            from port_release import hint_udp_listen_busy, smart_release_com

            state = smart_release_com(
                ctx["com"],
                ctx["baud"],
                bridge_running=bool(ctx["running"]),
                bridge_com=ctx.get("bridge_com"),
            )
            messages: list[str] = [state.reason]
            hint = hint_udp_listen_busy(ctx["udp_host"], int(ctx["udp_port"]))
            if hint:
                messages.append(hint)
            ctx["state"] = state
            ctx["message"] = " | ".join(messages)
        except Exception as exc:
            return WebCommandResult(False, str(exc), "error")

        def _finish(win: Any) -> WebCommandResult:
            try:
                if hasattr(win, "refresh_ports"):
                    win.refresh_ports()
                state = ctx["state"]
                self._apply_com_lock_state_on_main(win, state)
                ok = bool(state.last_attempt_ok)
                running = bool(ctx["running"])
                return WebCommandResult(
                    ok,
                    ctx["message"],
                    None if ok else "release_failed",
                    "running" if running else "stopped",
                )
            except Exception as exc:
                return WebCommandResult(False, str(exc), "error")

        return self._invoke_on_main(_finish)

    def request_probe_com_port(self, com_port: str) -> WebCommandResult:
        port = str(com_port or "").strip()
        if not port:
            return WebCommandResult(False, "Choose a COM port first.", "validation")
        ctx: dict[str, Any] = {"port": port}

        def _prepare(win: Any) -> WebCommandResult:
            from ui.connection_fields import parse_baud, read_baud_widget

            baud = parse_baud(read_baud_widget(win.baud_edit)) or 115200
            running = win._is_bridge_running()
            bridge = getattr(win, "bridge", None)
            bridge_com = bridge.com if bridge is not None else None
            if running and bridge_com and port.upper() == bridge_com.upper():
                return WebCommandResult(
                    False,
                    "Bridge is running on this COM — stop the bridge first",
                    "running_guard",
                    "running",
                )
            ctx["baud"] = baud
            ctx["running"] = running
            return WebCommandResult(True, "", None, "running" if running else "stopped")

        prep = self._invoke_on_main(_prepare)
        if not prep.ok:
            return prep
        try:
            from port_release import probe_com_lock

            ctx["state"] = probe_com_lock(port, int(ctx["baud"]), timeout_s=1.5)
        except Exception as exc:
            return WebCommandResult(False, str(exc), "error")

        def _finish(win: Any) -> WebCommandResult:
            state = ctx["state"]
            self._apply_com_lock_state_on_main(win, state)
            ok = bool(state.last_attempt_ok)
            running = bool(ctx["running"])
            return WebCommandResult(
                ok,
                state.reason,
                None if ok else "probe_failed",
                "running" if running else "stopped",
            )

        return self._invoke_on_main(_finish)

    def _apply_com_lock_state_on_main(self, win: Any, state: Any) -> None:
        win._com_lock_state = state
        if hasattr(win, "_apply_com_lock_chrome_idle"):
            ok = bool(getattr(state, "last_attempt_ok", False))
            locked = bool(getattr(state, "locked", False))
            win._apply_com_lock_chrome_idle(
                available=ok and not locked,
                reason=str(getattr(state, "reason", "") or ""),
            )
        if hasattr(win, "_sync_run_button_state"):
            win._sync_run_button_state()
        fields = self._com_lock_fields_from_window(win)
        with self._lock:
            for key, value in fields.items():
                if hasattr(self._snapshot, key):
                    setattr(self._snapshot, key, value)
            self._snapshot.updated_mono = time.monotonic()

    def _com_lock_fields_from_window(self, win: Any) -> dict[str, Any]:
        from ui.connection_fields import parse_baud, read_baud_widget

        running = win._is_bridge_running()
        starting = bool(getattr(win, "_starting", False))
        com = win.com_cb.currentText().strip()
        if running or starting:
            display = com or "COM"
            return {
                "com_port_available": True,
                "com_port_lock_reason": f"{display}: bridge running on this port",
                "com_lock_checking": False,
            }
        if not com or com.startswith("("):
            return {
                "com_port_available": False,
                "com_port_lock_reason": "Select a COM port",
                "com_lock_checking": False,
            }
        baud = parse_baud(read_baud_widget(win.baud_edit)) or 115200
        key = (com, baud)
        inflight = getattr(win, "_com_lock_probe_inflight", ("", 0))
        worker = getattr(win, "_com_lock_worker", None)
        checking = bool(
            inflight == key and worker is not None and worker.isRunning()
        )
        if checking:
            return {
                "com_port_available": None,
                "com_port_lock_reason": f"{com}: checking availability…",
                "com_lock_checking": True,
            }
        state = getattr(win, "_com_lock_state", None)
        if state is None:
            return {
                "com_port_available": None,
                "com_port_lock_reason": "",
                "com_lock_checking": False,
            }
        locked = bool(getattr(state, "locked", False))
        last_ok = getattr(state, "last_attempt_ok", True)
        reason = str(getattr(state, "reason", "") or "")
        available = bool(last_ok) and not locked
        return {
            "com_port_available": available,
            "com_port_lock_reason": reason,
            "com_lock_checking": False,
        }

    # ------------------------------------------------------------------ live log (web dashboard)
    def set_log_paused(self, paused: bool, *, dropped: int = 0) -> None:
        with self._log_lock:
            self._log_paused = bool(paused)
            if dropped:
                self._log_paused_dropped = int(dropped)

    def append_log_lines(self, lines: List[str]) -> None:
        if not lines:
            return
        now = time.monotonic()
        with self._log_lock:
            for raw in lines:
                text = (raw or "").rstrip("\n")
                if not text:
                    continue
                self._log_seq += 1
                self._log_lines.append(
                    WebLogLine(
                        seq=self._log_seq,
                        text=text,
                        kind=classify_web_log_line(text),
                        mono=now,
                    )
                )

    def get_logs(self, after_seq: int = 0, limit: int = 150) -> WebLogPayload:
        cap = max(1, min(300, int(limit)))
        with self._log_lock:
            paused = self._log_paused
            dropped = self._log_paused_dropped
            latest = self._log_seq
            out = [ln for ln in self._log_lines if ln.seq > after_seq]
        if len(out) > cap:
            out = out[-cap:]
        return WebLogPayload(
            lines=out,
            latest_seq=latest,
            paused=paused,
            paused_dropped=dropped,
        )

    # ------------------------------------------------------------------ publish
    def publish_from_window(self, win: Any) -> None:
        """Called on Qt main thread from mixin stats tick."""
        from ui.connection_fields import parse_baud, read_baud_widget

        if self._window() is None:
            self.attach_window(win)
        running = win._is_bridge_running()
        merged = getattr(win, "_bridge_stats_cache", None) or {}
        baud = parse_baud(read_baud_widget(win.baud_edit)) or 115200
        nmea = "passthrough"
        try:
            nmea = win._selected_nmea_mode().value
        except Exception:
            pass
        try:
            port = int(win.udp_port.text().strip())
        except ValueError:
            port = 10110
        from ui.stats_line import queue_backlog

        d_n2s = int(merged.get("drops_n2s", 0) or 0)
        d_s2n = int(merged.get("drops_s2n", 0) or 0)
        r_n2s = int(merged.get("rej_n2s", 0) or 0)
        r_s2n = int(merged.get("rej_s2n", 0) or 0)
        q_n2s = int(merged.get("n2s_q", 0) or 0)
        q_s2n = int(merged.get("s2n_q", 0) or 0)
        transport_ok = not (
            d_n2s or d_s2n or r_n2s or r_s2n or queue_backlog(q_n2s, q_s2n)
        )
        hdop = merged.get("hdop")
        try:
            hdop_f = float(hdop) if hdop is not None else None
        except (TypeError, ValueError):
            hdop_f = None
        sats = merged.get("num_sats")
        try:
            sats_i = int(sats) if sats is not None else None
        except (TypeError, ValueError):
            sats_i = None
        configured_com = win.com_cb.currentText().strip()
        runtime_com = configured_com
        if running:
            bridge = getattr(win, "bridge", None)
            if bridge is not None:
                runtime_com = (getattr(bridge, "com", None) or "").strip() or configured_com
        com_lock = self._com_lock_fields_from_window(win)
        from ui.transport_status import web_transport_summary

        transport = web_transport_summary({**merged, "running": running})
        self.update_snapshot(
            running=running,
            com_port=runtime_com,
            configured_com_port=configured_com,
            baud=baud,
            udp_listen_host=win.udp_host.text().strip(),
            udp_listen_port=port,
            nmea_mode=nmea,
            hz_net_to_com=merged.get("hz_down"),
            hz_com_to_net=merged.get("hz_up"),
            hz_inject=merged.get("hz_gui"),
            drops=d_n2s + d_s2n,
            rejects=r_n2s + r_s2n,
            drops_net_to_com=d_n2s,
            drops_com_to_net=d_s2n,
            rejects_net_to_com=r_n2s,
            rejects_com_to_net=r_s2n,
            queue_net_to_com=q_n2s,
            queue_com_to_net=q_s2n,
            lines_net_to_com=int(merged.get("lines_down", 0) or 0),
            lines_com_to_net=int(merged.get("lines_up", 0) or 0),
            transport_ok=transport_ok,
            gnss_summary=str(merged.get("summary") or ""),
            gnss_fix=str(merged.get("fix_label") or ""),
            gnss_sats=sats_i,
            gnss_hdop=hdop_f,
            gnss_stale=bool(merged.get("nav_stale")),
            gnss_quality=_gnss_quality_code(merged),
            gnss_stream_idle=bool(merged.get("stream_idle")),
            position_lat=_position_float(merged.get("position_lat")),
            position_lon=_position_float(merged.get("position_lon")),
            position_source=str(merged.get("position_source") or ""),
            position_stale=bool(merged.get("position_stale", True)),
            last_error=self._last_facade_error,
            com_port_available=com_lock["com_port_available"],
            com_port_lock_reason=com_lock["com_port_lock_reason"],
            com_lock_checking=com_lock["com_lock_checking"],
            **transport,
        )


def _position_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _gnss_quality_code(merged: dict[str, Any]) -> Optional[int]:
    if bool(merged.get("stream_idle")) or bool(merged.get("nav_stale")):
        return 0
    q = merged.get("quality")
    if isinstance(q, int) and not isinstance(q, bool):
        return q
    try:
        return int(q) if q is not None else None
    except (TypeError, ValueError):
        return None

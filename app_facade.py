"""Thread-safe bridge UI façade for Web control plane (no bridge protocol here)."""
from __future__ import annotations

import threading
import time
import weakref
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional

from PySide6 import QtCore


@dataclass
class WebSessionState:
    running: bool = False
    com_port: str = ""
    baud: int = 115200
    udp_listen_host: str = "0.0.0.0"
    udp_listen_port: int = 10110
    nmea_mode: str = "passthrough"
    hz_net_to_com: Optional[float] = None
    hz_com_to_net: Optional[float] = None
    drops: int = 0
    rejects: int = 0
    last_error: Optional[str] = None
    updated_mono: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WebConfigPayload:
    com_port: str = ""
    baud: int = 115200
    udp_listen_host: str = "0.0.0.0"
    udp_listen_port: int = 10110
    nmea_mode: str = "passthrough"
    hub_device_id: Optional[str] = None
    manual_override: bool = False
    network_mode: str = "udp_listen"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WebCommandResult:
    ok: bool
    message: str
    error_code: Optional[str] = None
    state: str = "stopped"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "message": self.message,
            "error_code": self.error_code,
            "state": self.state,
        }


class BridgeAppFacade(QtCore.QObject):
    """Lives on Qt main thread; HTTP layer reads snapshot and queues commands here."""

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._window_ref: Optional[weakref.ReferenceType[Any]] = None
        self._lock = threading.Lock()
        self._snapshot = WebSessionState()
        self._command_lock = threading.Lock()
        self._last_facade_error: Optional[str] = None
        self._facade_publish_interval_s = 0.5
        self._last_publish_mono = 0.0

    def attach_window(self, window: Any) -> None:
        self._window_ref = weakref.ref(window)

    def _window(self) -> Any:
        if self._window_ref is None:
            return None
        return self._window_ref()

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
        win = self._window()
        if win is None:
            return WebConfigPayload()
        return self._read_config_from_window(win)

    def _read_config_from_window(self, win: Any) -> WebConfigPayload:
        from ui.connection_fields import parse_baud

        hub = getattr(win, "connection_hub", None)
        hub_id = hub.selected_device_id() if hub is not None else None
        manual = hub.manual_override_active() if hub is not None else False
        baud = parse_baud(win.baud_edit.text()) or 115200
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
        return WebConfigPayload(
            com_port=win.com_cb.currentText().strip(),
            baud=baud,
            udp_listen_host=win.udp_host.text().strip(),
            udp_listen_port=port,
            nmea_mode=nmea,
            hub_device_id=hub_id,
            manual_override=manual,
            network_mode=mode,
        )

    def apply_config(self, patch: dict[str, Any]) -> WebCommandResult:
        return self._invoke_on_main(lambda w: self._apply_config_on_main(w, patch))

    def request_start(self) -> WebCommandResult:
        return self._invoke_on_main(self._start_on_main)

    def request_stop(self) -> WebCommandResult:
        return self._invoke_on_main(self._stop_on_main)

    def _invoke_on_main(self, fn: Callable[[Any], WebCommandResult]) -> WebCommandResult:
        win = self._window()
        if win is None:
            return WebCommandResult(False, "Application window not available", "unavailable")
        if not self._command_lock.acquire(blocking=False):
            return WebCommandResult(False, "Another command is in progress", "busy")
        box: dict[str, WebCommandResult] = {}
        done = threading.Event()

        def work() -> None:
            try:
                box["result"] = fn(win)
            except Exception as exc:
                box["result"] = WebCommandResult(False, str(exc), "error")
            finally:
                self._command_lock.release()
                done.set()

        QtCore.QTimer.singleShot(0, work)
        if not done.wait(timeout=20.0):
            self._command_lock.release()
            return WebCommandResult(False, "Command timed out", "busy")
        return box.get("result", WebCommandResult(False, "No result", "error"))

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

        if "com_port" in patch:
            text = str(patch["com_port"]).strip()
            idx = win.com_cb.findText(text)
            if idx >= 0:
                win.com_cb.setCurrentIndex(idx)
            else:
                win.com_cb.setCurrentText(text)
        if "baud" in patch:
            win.baud_edit.setText(str(int(patch["baud"])))
        if "udp_listen_host" in patch:
            win.udp_host.setText(str(patch["udp_listen_host"]))
        if "udp_listen_port" in patch:
            win.udp_port.setText(str(int(patch["udp_listen_port"])))
        if "hub_device_id" in patch and patch["hub_device_id"]:
            hub = getattr(win, "connection_hub", None)
            if hub is not None:
                win._on_hub_selection(str(patch["hub_device_id"]))
        if "manual_override" in patch:
            hub = getattr(win, "connection_hub", None)
            if hub is not None:
                hub.set_manual_override(bool(patch["manual_override"]))

        return WebCommandResult(True, "Configuration updated", None, "running" if running else "stopped")

    def publish_from_window(self, win: Any) -> None:
        """Called on Qt main thread from mixin stats tick."""
        from ui.connection_fields import parse_baud

        running = win._is_bridge_running()
        merged = getattr(win, "_bridge_stats_cache", None) or {}
        baud = parse_baud(win.baud_edit.text()) or 115200
        nmea = "passthrough"
        try:
            nmea = win._selected_nmea_mode().value
        except Exception:
            pass
        try:
            port = int(win.udp_port.text().strip())
        except ValueError:
            port = 10110
        self.update_snapshot(
            running=running,
            com_port=win.com_cb.currentText().strip(),
            baud=baud,
            udp_listen_host=win.udp_host.text().strip(),
            udp_listen_port=port,
            nmea_mode=nmea,
            hz_net_to_com=merged.get("hz_down"),
            hz_com_to_net=merged.get("hz_up"),
            drops=int(merged.get("drops_n2s", 0) or 0) + int(merged.get("drops_s2n", 0) or 0),
            rejects=int(merged.get("rej_n2s", 0) or 0) + int(merged.get("rej_sn", 0) or 0),
            last_error=self._last_facade_error,
        )

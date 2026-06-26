"""Qt-free bridge façade for Linux headless + web dashboard."""
from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, List, Optional

from bridge_core import NetMode, SerialNetBridge
from discovery_service import (
    build_snapshot,
    resolve_network_bind_from_device_id,
)
from headless_bridge_runner import HeadlessBridgeRunner
from nmea_codec import NmeaFilter, NmeaMode
from port_release import hint_udp_listen_busy, probe_com_lock, smart_release_com
from ui.transport_status import web_transport_summary
from web_facade_types import (
    WEB_LOG_MAX_LINES,
    NetworkCardDto,
    SerialDeviceDto,
    WebCommandResult,
    WebConfigPayload,
    WebDiscoveryPayload,
    WebLogLine,
    WebLogPayload,
    WebSessionState,
    classify_web_log_line,
)

_NMEA_MODES = {
    "passthrough": NmeaMode.PASSTHROUGH,
    "strict": NmeaMode.STRICT,
    "raw": NmeaMode.RAW,
}

_NET_MODES = {
    "udp_listen": NetMode.UDP_LISTEN,
    "udp_remote": NetMode.UDP_REMOTE,
    "tcp_client": NetMode.TCP_CLIENT,
    "tcp_server": NetMode.TCP_SERVER,
}


class HeadlessBridgeFacade:
    """Thread-safe façade backing the existing FastAPI web control plane."""

    def __init__(self, config: Optional[WebConfigPayload] = None) -> None:
        self._lock = threading.RLock()
        self._config = config or WebConfigPayload()
        self._snapshot = WebSessionState()
        self._runner = HeadlessBridgeRunner()
        self._runner.on_log = self._on_bridge_log
        self._runner.on_stats = self._on_bridge_stats
        self._command_lock = threading.Lock()
        self._discovery_lock = threading.Lock()
        self._discovery_payload = WebDiscoveryPayload()
        self._serial_stable: dict[str, int] = {}
        self._log_lock = threading.Lock()
        self._log_seq = 0
        self._log_lines: Deque[WebLogLine] = deque(maxlen=WEB_LOG_MAX_LINES)
        self._log_paused = False
        self._log_paused_dropped = 0
        self._last_facade_error: Optional[str] = None
        self._site_config_path: Optional[Path] = None
        self._site_web_port: int = 8765
        self._site_lan_bind: bool = False
        self._site_token: str = ""
        self._site_autostart: bool = False
        self._seed_snapshot_from_config()
        self._refresh_discovery_locked()

    def _seed_snapshot_from_config(self) -> None:
        with self._lock:
            cfg = WebConfigPayload(**self._config.to_dict())
            self._snapshot.configured_com_port = cfg.com_port
            self._snapshot.com_port = cfg.com_port
            self._snapshot.baud = cfg.baud
            self._snapshot.udp_listen_host = cfg.udp_listen_host
            self._snapshot.udp_listen_port = cfg.udp_listen_port
            self._snapshot.nmea_mode = cfg.nmea_mode
            self._snapshot.net_mode = cfg.network_mode
            self._snapshot.updated_mono = time.monotonic()

    def commands_ready(self) -> bool:
        return True

    def set_site_context(
        self,
        *,
        config_path: Optional[Path],
        web_port: int,
        lan_bind: bool,
        token: str,
        autostart: bool,
    ) -> None:
        self._site_config_path = config_path
        self._site_web_port = int(web_port)
        self._site_lan_bind = bool(lan_bind)
        self._site_token = str(token or "").strip()
        self._site_autostart = bool(autostart)

    def persist_site_config(self) -> WebCommandResult:
        path = self._site_config_path
        if path is None:
            return WebCommandResult(
                False,
                "No site config path — set CONFIG_FILE or --config",
                "no_config_path",
            )
        with self._lock:
            if self._runner.bridge_running():
                return WebCommandResult(
                    False,
                    "Stop the bridge before saving boot defaults",
                    "running_guard",
                )
            cfg = WebConfigPayload(**self._config.to_dict())
        from headless_config import HeadlessRuntimeConfig, save_site_config

        runtime = HeadlessRuntimeConfig(
            config_path=path,
            serial=str(cfg.com_port).strip(),
            baud=int(cfg.baud),
            udp_host=str(cfg.udp_listen_host).strip() or "0.0.0.0",
            udp_port=int(cfg.udp_listen_port),
            network_mode=str(cfg.network_mode),
            remote_host=str(cfg.remote_host).strip(),
            remote_port=int(cfg.remote_port),
            nmea_mode=str(cfg.nmea_mode),
            web_host="0.0.0.0" if self._site_lan_bind else "127.0.0.1",
            web_port=int(self._site_web_port),
            lan_bind=bool(self._site_lan_bind),
            token=self._site_token,
            start_bridge=bool(self._site_autostart),
        )
        try:
            save_site_config(path, runtime)
        except OSError as exc:
            return WebCommandResult(False, f"Could not write config: {exc}", "io_error")
        return WebCommandResult(
            True,
            f"Saved boot defaults to {path}",
            None,
            "ok",
        )

    def get_status(self) -> WebSessionState:
        with self._lock:
            return WebSessionState(**self._snapshot.to_dict())

    def get_config(self) -> WebConfigPayload:
        with self._lock:
            return WebConfigPayload(**self._config.to_dict())

    def apply_config(self, patch: dict[str, Any]) -> WebCommandResult:
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
                    f"Setting '{key}' is not supported via Web in headless mode",
                    "unsupported",
                )
        with self._lock:
            running = self._runner.bridge_running()
            mutable_while_running = {"hub_device_id", "manual_override"}
            if running:
                for key in patch:
                    if key not in mutable_while_running:
                        return WebCommandResult(
                            False,
                            "Stop the bridge before changing serial or network bind",
                            "running_guard",
                        )
            cfg = WebConfigPayload(**self._config.to_dict())
            if "com_port" in patch:
                cfg.com_port = str(patch["com_port"]).strip()
            if "baud" in patch:
                try:
                    cfg.baud = int(patch["baud"])
                except (TypeError, ValueError):
                    return WebCommandResult(False, "Invalid baud", "validation")
            if "udp_listen_host" in patch:
                cfg.udp_listen_host = str(patch["udp_listen_host"]).strip() or "0.0.0.0"
            if "udp_listen_port" in patch:
                try:
                    cfg.udp_listen_port = int(patch["udp_listen_port"])
                except (TypeError, ValueError):
                    return WebCommandResult(False, "Invalid UDP port", "validation")
            if "nmea_mode" in patch:
                mode = str(patch["nmea_mode"]).strip().lower()
                if mode not in _NMEA_MODES:
                    return WebCommandResult(False, f"Unknown NMEA mode: {mode}", "validation")
                cfg.nmea_mode = mode
            if "network_mode" in patch:
                mode = str(patch["network_mode"]).strip()
                if mode not in _NET_MODES:
                    return WebCommandResult(False, f"Unknown network mode: {mode}", "validation")
                cfg.network_mode = mode
            if "remote_host" in patch:
                cfg.remote_host = str(patch["remote_host"]).strip()
            if "remote_port" in patch:
                try:
                    cfg.remote_port = int(patch["remote_port"])
                except (TypeError, ValueError):
                    return WebCommandResult(False, "Invalid remote port", "validation")
            if "hub_device_id" in patch and patch["hub_device_id"]:
                device_id = str(patch["hub_device_id"])
                cfg.hub_device_id = device_id
                if device_id.startswith("serial:"):
                    port = device_id.split(":", 1)[-1].strip()
                    if port and not port.startswith("serial"):
                        cfg.com_port = port
                bind = resolve_network_bind_from_device_id(device_id)
                if bind is not None:
                    host, port = bind
                    cfg.udp_listen_host = host
                    cfg.udp_listen_port = int(port)
                    cfg.network_mode = "udp_listen"
            if "manual_override" in patch:
                cfg.manual_override = bool(patch["manual_override"])
            self._config = cfg
            self._refresh_discovery_locked()
            return WebCommandResult(
                True,
                "Configuration updated",
                None,
                "running" if running else "stopped",
            )

    def request_start(self) -> WebCommandResult:
        if not self._command_lock.acquire(blocking=False):
            return WebCommandResult(False, "Another command is in progress", "busy")
        try:
            with self._lock:
                cfg = WebConfigPayload(**self._config.to_dict())
            err = self._validate_before_start(cfg)
            if err:
                self._last_facade_error = err
                return WebCommandResult(False, err, "validation", "stopped")
            if self._runner.bridge_running():
                return WebCommandResult(True, "Bridge already running", None, "running")
            if self._runner.is_alive():
                return WebCommandResult(False, "Bridge is starting or stopping", "busy")
            lock = probe_com_lock(cfg.com_port, cfg.baud, timeout_s=2.0)
            if not lock.last_attempt_ok:
                self._set_com_lock_fields(lock.reason, available=False)
                return WebCommandResult(False, lock.reason, "validation", "stopped")
            self._set_com_lock_fields(lock.reason, available=True)
            ok = self._runner.start(self._make_build_fn(cfg))
            if not ok:
                msg = self._last_facade_error or "Bridge failed to start"
                return WebCommandResult(False, msg, "error", "stopped")
            return WebCommandResult(True, "Bridge start requested", None, "running")
        finally:
            self._command_lock.release()

    def request_stop(self) -> WebCommandResult:
        if self._runner.is_alive() or self._runner.bridge_running():
            self._runner.stop()
            with self._lock:
                self._snapshot.running = False
            return WebCommandResult(True, "Bridge stop requested", None, "stopped")
        return WebCommandResult(True, "Bridge already stopped", None, "stopped")

    def get_discovery(self) -> WebDiscoveryPayload:
        with self._discovery_lock:
            return self._discovery_payload

    def set_discovery_scan_busy(self, busy: bool) -> None:
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
        self._refresh_discovery_locked(busy=True)
        self._refresh_discovery_locked(busy=False)
        return WebCommandResult(True, "Discovery refreshed", None, "ok")

    def request_refresh_serial_ports(self) -> WebCommandResult:
        self._refresh_discovery_locked(probe_serial=True)
        n = len(self.get_discovery().serial_devices)
        return WebCommandResult(
            True,
            f"Found {n} serial port(s)" if n else "No serial ports detected on this PC",
            None,
            "ok",
        )

    def request_unlock_ports(self) -> WebCommandResult:
        with self._lock:
            cfg = WebConfigPayload(**self._config.to_dict())
            running = self._runner.bridge_running()
            bridge_com = None
            if self._runner.bridge is not None:
                bridge_com = self._runner.bridge.com
        state = smart_release_com(
            cfg.com_port,
            cfg.baud,
            bridge_running=running,
            bridge_com=bridge_com,
        )
        messages = [state.reason]
        hint = hint_udp_listen_busy(cfg.udp_listen_host, int(cfg.udp_listen_port))
        if hint:
            messages.append(hint)
        self._refresh_discovery_locked(probe_serial=True)
        ok = bool(state.last_attempt_ok)
        return WebCommandResult(
            ok,
            " | ".join(messages),
            None if ok else "release_failed",
            "running" if running else "stopped",
        )

    def request_probe_com_port(self, com_port: str) -> WebCommandResult:
        port = str(com_port or "").strip()
        if not port:
            return WebCommandResult(False, "Choose a serial port first.", "validation")
        with self._lock:
            cfg = WebConfigPayload(**self._config.to_dict())
            running = self._runner.bridge_running()
            bridge_com = self._runner.bridge.com if self._runner.bridge else None
        if running and bridge_com and port == bridge_com:
            return WebCommandResult(
                False,
                "Bridge is running on this port — stop the bridge first",
                "running_guard",
                "running",
            )
        state = probe_com_lock(port, cfg.baud, timeout_s=1.5)
        self._set_com_lock_fields(state.reason, available=bool(state.last_attempt_ok))
        return WebCommandResult(
            bool(state.last_attempt_ok),
            state.reason,
            None if state.last_attempt_ok else "probe_failed",
            "running" if running else "stopped",
        )

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

    def shutdown(self) -> None:
        self._runner.stop()

    def _validate_before_start(self, cfg: WebConfigPayload) -> Optional[str]:
        com = (cfg.com_port or "").strip()
        if not com:
            return "Select a serial port before starting"
        if cfg.baud <= 0:
            return "Invalid baud rate"
        if cfg.network_mode == "udp_listen":
            if not (1 <= int(cfg.udp_listen_port) <= 65535):
                return "UDP listen port must be 1–65535"
        elif cfg.network_mode in ("udp_remote", "tcp_client"):
            if not (cfg.remote_host or "").strip():
                return "Remote host is required for this network mode"
            if not (1 <= int(cfg.remote_port) <= 65535):
                return "Remote port must be 1–65535"
        elif cfg.network_mode == "tcp_server":
            if not (1 <= int(cfg.remote_port) <= 65535):
                return "TCP listen port must be 1–65535"
        return None

    def _make_build_fn(self, cfg: WebConfigPayload):
        nmea_mode = _NMEA_MODES.get(cfg.nmea_mode, NmeaMode.PASSTHROUGH)
        net_mode = _NET_MODES.get(cfg.network_mode, NetMode.UDP_LISTEN)
        nmea_filter = NmeaFilter() if nmea_mode == NmeaMode.STRICT else None

        def build(loop: asyncio.AbstractEventLoop) -> SerialNetBridge:
            common = dict(
                loop=loop,
                ui_log=self._runner.on_log,
                ui_log_verbose=lambda: True,
                stats_cb=self._runner.on_stats,
                nmea_mode=nmea_mode,
                nmea_filter=nmea_filter,
                serial_auto_reconnect=True,
            )
            if net_mode == NetMode.TCP_SERVER:
                host = (cfg.remote_host or "0.0.0.0").strip() or "0.0.0.0"
                return SerialNetBridge(
                    cfg.com_port,
                    cfg.baud,
                    net_mode,
                    tcp_bind_host=host,
                    tcp_bind_port=int(cfg.remote_port or 4001),
                    **common,
                )
            if net_mode == NetMode.TCP_CLIENT:
                return SerialNetBridge(
                    cfg.com_port,
                    cfg.baud,
                    net_mode,
                    tcp_client_host=(cfg.remote_host or "127.0.0.1").strip(),
                    tcp_client_port=int(cfg.remote_port or 4001),
                    **common,
                )
            if net_mode == NetMode.UDP_REMOTE:
                return SerialNetBridge(
                    cfg.com_port,
                    cfg.baud,
                    net_mode,
                    udp_remote=(
                        (cfg.remote_host or "").strip(),
                        int(cfg.remote_port or 10110),
                    ),
                    **common,
                )
            return SerialNetBridge(
                cfg.com_port,
                cfg.baud,
                net_mode,
                udp_listen=(cfg.udp_listen_host.strip() or "0.0.0.0", int(cfg.udp_listen_port)),
                **common,
            )

        return build

    def _on_bridge_log(self, line: str) -> None:
        self.append_log_lines([line])

    def _on_bridge_stats(self, merged: dict) -> None:
        with self._lock:
            cfg = WebConfigPayload(**self._config.to_dict())
        running = bool(merged.get("running"))
        d_n2s = int(merged.get("drops_n2s", 0) or 0)
        d_s2n = int(merged.get("drops_s2n", 0) or 0)
        r_n2s = int(merged.get("rej_n2s", 0) or 0)
        r_s2n = int(merged.get("rej_s2n", 0) or 0)
        q_n2s = int(merged.get("n2s_q", 0) or 0)
        q_s2n = int(merged.get("s2n_q", 0) or 0)
        transport_ok = not (d_n2s or d_s2n or r_n2s or r_s2n or (q_n2s + q_s2n > 64))
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
        runtime_com = (merged.get("com") or cfg.com_port or "").strip()
        transport = web_transport_summary({**merged, "running": running})
        gnss_fix = str(merged.get("fix_quality_label") or merged.get("fix") or "")
        self.update_snapshot(
            running=running,
            com_port=runtime_com,
            configured_com_port=cfg.com_port,
            baud=cfg.baud,
            udp_listen_host=cfg.udp_listen_host,
            udp_listen_port=cfg.udp_listen_port,
            nmea_mode=cfg.nmea_mode,
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
            gnss_summary=str(merged.get("gnss_summary") or ""),
            gnss_fix=gnss_fix,
            gnss_sats=sats_i,
            gnss_hdop=hdop_f,
            gnss_stale=bool(merged.get("gnss_stale")),
            gnss_quality=merged.get("quality"),
            gnss_stream_idle=bool(merged.get("gnss_stream_idle")),
            position_lat=merged.get("lat"),
            position_lon=merged.get("lon"),
            position_source=str(merged.get("position_source") or ""),
            position_stale=bool(merged.get("position_stale", True)),
            last_error=self._last_facade_error,
            **transport,
        )
        if running:
            self._refresh_discovery_locked()

    def update_snapshot(self, **fields: Any) -> None:
        with self._lock:
            for key, value in fields.items():
                if hasattr(self._snapshot, key):
                    setattr(self._snapshot, key, value)
            self._snapshot.updated_mono = time.monotonic()

    def _set_com_lock_fields(self, reason: str, *, available: bool) -> None:
        self.update_snapshot(
            com_port_available=available,
            com_port_lock_reason=reason,
            com_lock_checking=False,
        )

    def _refresh_discovery_locked(
        self,
        *,
        busy: bool = False,
        probe_serial: bool = False,
    ) -> None:
        with self._lock:
            cfg = WebConfigPayload(**self._config.to_dict())
            running = self._runner.bridge_running()
            bridge_com = self._runner.bridge.com if self._runner.bridge else None
            stats = self._snapshot.to_dict() if running else None
        snap, self._serial_stable = build_snapshot(
            stable_counts=self._serial_stable,
            bridge_stats=stats,
            udp_host=cfg.udp_listen_host,
            udp_port=int(cfg.udp_listen_port),
            selected_port=cfg.com_port,
            probe_baud=cfg.baud,
            bridge_running=running,
            bridge_com=bridge_com,
            probe_serial_locks=probe_serial,
        )
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
                scan_note=snap.scan_note,
                scan_busy=busy,
                serial_devices=serials,
                network_cards=networks,
                errors=list(snap.errors),
            )

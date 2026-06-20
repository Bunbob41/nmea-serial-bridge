"""FleetSupervisor - owns stream workers."""
from __future__ import annotations

import time
from typing import Optional, Type

from PySide6 import QtCore

from bridge_core import NetMode
from discovery_service import probe_udp_port_available

from core.fleet.config import (
    FLEET_UDP_PORT_FIRST,
    FLEET_UDP_PORT_LAST,
    FleetConfig,
    StreamDefinition,
    load_fleet_config,
    save_fleet_config,
    stream_com_ports,
    stream_connection_key,
    validate_fleet_config,
    validate_fleet_config_for_start,
)
from core.fleet.stream_worker import StreamWorkerHost, ThreadStreamWorker
from core.fleet.types import StreamRuntimeState, WorkerState


class FleetSupervisor(QtCore.QObject):
    fleet_changed = QtCore.Signal()
    stream_state_changed = QtCore.Signal(str, object)

    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        *,
        worker_cls: Type[StreamWorkerHost] = ThreadStreamWorker,
    ) -> None:
        super().__init__(parent)
        self._worker_cls = worker_cls
        self._config = load_fleet_config()
        self._workers: dict[str, StreamWorkerHost] = {}

    def config(self) -> FleetConfig:
        return self._config

    def replace_config(self, config: FleetConfig) -> list[str]:
        errors = validate_fleet_config(config)
        if errors:
            return errors
        old_by_id = {s.id: s for s in self._config.streams}
        self._config = config
        save_fleet_config(self._config)
        for stream in self._config.streams:
            if not stream.enabled:
                self.stop_stream(stream.id)
                continue
            worker = self._workers.get(stream.id)
            if worker is None or not worker.is_active():
                continue
            old = old_by_id.get(stream.id)
            if old is None or stream_connection_key(old) != stream_connection_key(stream):
                self.restart_stream(stream.id)
        self.fleet_changed.emit()
        return []

    def listening_stream_for_udp(self, host: str, port: int, *, exclude_id: str | None = None) -> Optional[StreamDefinition]:
        host = (host or "0.0.0.0").strip() or "0.0.0.0"
        port = int(port)
        for stream in self._config.streams:
            if exclude_id and stream.id == exclude_id:
                continue
            if stream.net_mode != NetMode.UDP_LISTEN.value:
                continue
            sh = (stream.udp_host or "0.0.0.0").strip() or "0.0.0.0"
            if sh == host and int(stream.udp_port) == port:
                worker = self._workers.get(stream.id)
                if worker is not None and worker.is_active():
                    return stream
        return None

    def running_stream_for_com(self, com: str) -> Optional[StreamDefinition]:
        target = (com or "").strip().upper()
        if not target:
            return None
        for stream in self._config.streams:
            worker = self._workers.get(stream.id)
            if worker is None or not worker.is_active():
                continue
            live = worker.runtime_state().active_com or (stream.com or "").strip().upper()
            if target in stream_com_ports(stream):
                return stream
            live = worker.runtime_state().active_com or (stream.com or "").strip().upper()
            if live == target:
                return stream
        return None

    def validate(self) -> list[str]:
        return validate_fleet_config(self._config)

    def primary_stream_id(self) -> Optional[str]:
        return self._config.primary_stream_id()

    def set_primary(self, stream_id: str) -> None:
        self._config.set_primary(stream_id)
        save_fleet_config(self._config)
        self.fleet_changed.emit()

    def runtime_states(self) -> dict[str, StreamRuntimeState]:
        out: dict[str, StreamRuntimeState] = {}
        for stream in self._config.streams:
            worker = self._workers.get(stream.id)
            if worker is not None:
                out[stream.id] = worker.runtime_state()
            else:
                out[stream.id] = StreamRuntimeState(stream_id=stream.id)
        return out

    def running_primary_worker(self) -> Optional[StreamWorkerHost]:
        pid = self.primary_stream_id()
        if not pid:
            return None
        worker = self._workers.get(pid)
        if worker is not None and worker.is_running():
            return worker
        return None

    def start_all(self) -> list[str]:
        errors = validate_fleet_config_for_start(self._config)
        if errors:
            return errors
        start_errors: list[str] = []
        for stream in self._config.streams:
            if not stream.enabled:
                continue
            start_errors.extend(self.start_stream(stream.id))
            if stream.net_mode == NetMode.UDP_LISTEN.value:
                wait_err = self._wait_stream_start_outcome(stream.id)
                if wait_err:
                    start_errors.append(wait_err)
        return start_errors

    def stop_all(self) -> list[str]:
        errors: list[str] = []
        for stream_id in list(self._workers):
            errors.extend(self.stop_stream(stream_id))
        return errors


    def _wait_stream_start_outcome(self, stream_id: str, *, timeout_s: float = 10.0) -> Optional[str]:
        """After start(), wait until RUNNING/ERROR so the next UDP bind probe is accurate."""
        deadline = time.monotonic() + timeout_s
        stream = self._config.stream_by_id(stream_id)
        label = stream.label if stream else stream_id
        while time.monotonic() < deadline:
            worker = self._workers.get(stream_id)
            if worker is None:
                return None
            st = worker.runtime_state()
            if st.worker_state == WorkerState.RUNNING:
                return None
            if st.worker_state == WorkerState.ERROR:
                msg = st.error_message or "Start failed"
                return f"Stream {label}: {msg}"
            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(50, loop.quit)
            loop.exec()
        return f"Stream {label}: start timed out after {timeout_s:.0f}s"

    def _control_bridge_conflict(self, stream: StreamDefinition) -> Optional[str]:
        win = self.parent()
        if win is None or not hasattr(win, "_fleet_control_start_conflict"):
            return None
        return win._fleet_control_start_conflict(stream)

    def _udp_listen_preflight(self, stream: StreamDefinition) -> Optional[str]:
        if stream.net_mode != NetMode.UDP_LISTEN.value:
            return None
        host = (stream.udp_host or "0.0.0.0").strip() or "0.0.0.0"
        port = int(stream.udp_port)
        other = self.listening_stream_for_udp(host, port, exclude_id=stream.id)
        if other is not None:
            return (
                f"UDP listen {host}:{port} is already used by Fleet stream "
                f"«{other.label}». Give each stream its own listen port."
            )
        if not probe_udp_port_available(host, port):
            return (
                f"UDP listen {host}:{port} is busy - another bridge or app is already bound. "
                f"Pick another listen port (Fleet streams: {FLEET_UDP_PORT_FIRST}-{FLEET_UDP_PORT_LAST})."
            )
        return None

    def start_stream(self, stream_id: str) -> list[str]:
        stream = self._config.stream_by_id(stream_id)
        if stream is None:
            return [f"Unknown stream {stream_id}."]
        if not stream.enabled:
            return [f"Stream {stream.label} is disabled."]
        row_errors = validate_fleet_config_for_start(self._config, stream_id=stream_id)
        if row_errors:
            return row_errors
        worker = self._workers.get(stream_id)
        if worker is None:
            worker = self._worker_cls(stream_id, self)
            if isinstance(worker, ThreadStreamWorker):
                worker.state_changed.connect(self._on_worker_state)
            self._workers[stream_id] = worker
        elif worker.is_active():
            st = worker.runtime_state()
            if st.worker_state == WorkerState.STARTING:
                return [f"Stream {stream.label} is still starting."]
            if st.worker_state == WorkerState.STOPPING:
                return [f"Stream {stream.label} is still stopping."]
            live_key = st.connection_key
            if live_key and live_key == stream_connection_key(stream):
                return []
            return self.restart_stream(stream_id)
        control_err = self._control_bridge_conflict(stream)
        if control_err:
            if isinstance(worker, ThreadStreamWorker):
                worker.mark_error(control_err)
            return [f"Stream {stream.label}: {control_err}"]
        preflight = self._udp_listen_preflight(stream)
        if preflight:
            if isinstance(worker, ThreadStreamWorker):
                worker.mark_error(preflight)
            return [f"Stream {stream.label}: {preflight}"]
        worker.start(stream)
        return []

    def restart_stream(self, stream_id: str) -> list[str]:
        self.stop_stream(stream_id)
        return self.start_stream(stream_id)

    def stop_stream(self, stream_id: str) -> list[str]:
        worker = self._workers.get(stream_id)
        if worker is None:
            return []
        stream = self._config.stream_by_id(stream_id)
        label = stream.label if stream else stream_id
        worker.stop()
        st = worker.runtime_state()
        if st.worker_state == WorkerState.ERROR and st.error_message:
            return [f"Stream {label}: {st.error_message}"]
        return []

    def apply_auto_start_if_enabled(self) -> None:
        if self._config.auto_start_on_launch:
            QtCore.QTimer.singleShot(0, self._auto_start_all)

    def _auto_start_all(self) -> None:
        errors = self.start_all()
        if not errors:
            return
        msg = "; ".join(errors[:3])
        if len(errors) > 3:
            msg += "..."
        win = self.parent()
        if win is None:
            return
        if hasattr(win, "_log_ui"):
            win._log_ui(f"[Fleet] Auto-start failed: {msg}")
        panel = getattr(win, "_fleet_panel", None)
        if panel is not None and hasattr(panel, "_status"):
            panel._status.setText(f"Fleet auto-start failed: {msg}")
        self.fleet_changed.emit()

    def _on_worker_state(self, stream_id: str, state: object) -> None:
        self.stream_state_changed.emit(stream_id, state)

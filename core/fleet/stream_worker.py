"""ThreadStreamWorker - one BridgeAsyncThread per stream."""
from __future__ import annotations

import time
from typing import Optional, Protocol

from PySide6 import QtCore

from bridge_core import BridgeAsyncThread
from core.fleet.bridge_factory import make_bridge_builder
from core.fleet.config import StreamDefinition, stream_connection_key
from core.fleet.types import FLEET_QUEUE_BACKLOG_DEPTH, StreamRuntimeState, WorkerState

_ACTIVE_STATES = frozenset({WorkerState.STARTING, WorkerState.RUNNING, WorkerState.STOPPING})


class StreamWorkerHost(Protocol):
    stream_id: str

    def start(self, stream: StreamDefinition) -> None: ...
    def mark_error(self, msg: str) -> None: ...
    def stop(self) -> None: ...
    def is_running(self) -> bool: ...
    def is_active(self) -> bool: ...
    def runtime_state(self) -> StreamRuntimeState: ...


class ThreadStreamWorker(QtCore.QObject):
    state_changed = QtCore.Signal(str, object)

    def __init__(self, stream_id: str, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.stream_id = stream_id
        self._thread: Optional[BridgeAsyncThread] = None
        self._state = StreamRuntimeState(stream_id=stream_id)
        self._last_stats_ui_mono = 0.0
        self._last_stats_ui_key: tuple = ()

    def runtime_state(self) -> StreamRuntimeState:
        return self._state

    def is_running(self) -> bool:
        return self._state.worker_state == WorkerState.RUNNING

    def is_active(self) -> bool:
        return self._state.worker_state in _ACTIVE_STATES

    def start(self, stream: StreamDefinition) -> None:
        if self.is_active():
            return
        if self._thread is not None and self._thread.isRunning():
            self.stop()
        self._set_state(WorkerState.STARTING)
        self._state.active_com = (stream.com or "").strip().upper()
        self._state.connection_key = stream_connection_key(stream)
        thread = BridgeAsyncThread(make_bridge_builder(
            stream,
            ui_log=self._on_log,
            status_cb=lambda _a, _b: None,
            stats_cb=self._on_stats,
        ))
        thread.log_msg.connect(self._on_log)
        thread.start_done.connect(self._on_start_done)
        thread.stats_msg.connect(self._on_stats)
        self._thread = thread
        thread.start()

    def mark_error(self, msg: str) -> None:
        self._state.error_message = msg.strip()[:120]
        self._set_state(WorkerState.ERROR)
        self._forward_log(msg)

    def stop(self) -> None:
        thread = self._thread
        if thread is None:
            self._set_state(WorkerState.IDLE)
            return
        if thread.isRunning():
            self._set_state(WorkerState.STOPPING)
            thread.request_stop()
            if not thread.wait(8000):
                self._state.active_com = ""
                self._state.connection_key = ""
                self._state.error_message = (
                    "Stop timed out - COM or network may still be in use. "
                    "Try Stop all again or restart the app."
                )
                self._set_state(WorkerState.ERROR)
                return
        self._thread = None
        self._state.active_com = ""
        self._state.connection_key = ""
        self._state.error_message = ""
        self._set_state(WorkerState.IDLE)

    def _on_log(self, msg: str) -> None:
        low = msg.lower()
        if any(tok in low for tok in ("error", "failed", "already in use", "cannot open", "hint:", "busy")):
            self._state.error_message = msg.strip()[:120]
        self._forward_log(msg)

    def _forward_log(self, msg: str) -> None:
        sup = self.parent()
        if sup is None or not hasattr(sup, "config"):
            return
        stream = sup.config().stream_by_id(self.stream_id)
        label = stream.label.strip() if stream and stream.label.strip() else self.stream_id
        win = sup.parent()
        if win is not None and hasattr(win, "_log_ui"):
            win._log_ui(f"[Fleet {label}] {msg}")

    def _on_start_done(self, ok: bool) -> None:
        if ok:
            self._state.error_message = ""
            self._set_state(WorkerState.RUNNING)
        else:
            if not self._state.error_message:
                self._state.error_message = "Start failed"
            self._set_state(WorkerState.ERROR)

    def _ui_stats_key(self) -> tuple:
        s = self._state
        hz_bucket = 0
        if s.rate_hint is not None and s.rate_hint >= 1:
            hz_bucket = int(s.rate_hint)
        return (s.worker_state, s.backlog_line(), s.error_message, hz_bucket)

    def _stats_ui_urgent(self) -> bool:
        s = self._state
        if s.worker_state == WorkerState.ERROR:
            return True
        if s.drops_n2s or s.drops_s2n:
            return True
        return (
            s.queue_n2s >= FLEET_QUEUE_BACKLOG_DEPTH
            or s.queue_s2n >= FLEET_QUEUE_BACKLOG_DEPTH
        )

    def _maybe_emit_stats_ui(self) -> None:
        key = self._ui_stats_key()
        now = time.monotonic()
        if key == self._last_stats_ui_key and not self._stats_ui_urgent():
            if (now - self._last_stats_ui_mono) < 0.5:
                return
            if key == self._last_stats_ui_key:
                return
        if (
            not self._stats_ui_urgent()
            and key == self._last_stats_ui_key
            and (now - self._last_stats_ui_mono) < 0.5
        ):
            return
        self._last_stats_ui_mono = now
        self._last_stats_ui_key = key
        self.state_changed.emit(self.stream_id, self._state)

    def _on_stats(self, stats: dict) -> None:
        self._state.last_rx_monotonic = time.monotonic()
        self._state.bytes_rx = int(stats.get("bytes_rx", self._state.bytes_rx) or 0)
        self._state.bytes_tx = int(stats.get("bytes_tx", self._state.bytes_tx) or 0)
        self._state.drops_n2s = int(stats.get("drops_n2s") or 0)
        self._state.drops_s2n = int(stats.get("drops_s2n") or 0)
        self._state.drops = self._state.drops_n2s + self._state.drops_s2n
        self._state.queue_n2s = int(stats.get("n2s_q") or 0)
        self._state.queue_s2n = int(stats.get("s2n_q") or 0)
        hz = stats.get("hz_up") or stats.get("hz")
        if hz is not None:
            try:
                self._state.rate_hint = float(hz)
            except (TypeError, ValueError):
                pass
        self._maybe_emit_stats_ui()

    def _set_state(self, worker_state: WorkerState) -> None:
        self._state.worker_state = worker_state
        self._last_stats_ui_key = ()
        self.state_changed.emit(self.stream_id, self._state)
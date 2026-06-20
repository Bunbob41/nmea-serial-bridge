"""Fleet runtime types (ephemeral worker state)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

FLEET_QUEUE_BACKLOG_DEPTH = 12


class WorkerState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class StreamRuntimeState:
    stream_id: str
    worker_state: WorkerState = WorkerState.IDLE
    error_message: str = ""
    last_rx_monotonic: Optional[float] = None
    bytes_rx: int = 0
    bytes_tx: int = 0
    drops: int = 0
    rate_hint: Optional[float] = None
    active_com: str = ""
    connection_key: str = ""
    queue_n2s: int = 0
    queue_s2n: int = 0
    drops_n2s: int = 0
    drops_s2n: int = 0

    def backlog_line(self) -> str:
        if self.worker_state != WorkerState.RUNNING:
            return ""
        parts: list[str] = []
        total_drops = self.drops_n2s + self.drops_s2n
        if total_drops:
            parts.append(f"drop {total_drops}")
        if (
            self.queue_n2s >= FLEET_QUEUE_BACKLOG_DEPTH
            or self.queue_s2n >= FLEET_QUEUE_BACKLOG_DEPTH
        ):
            parts.append(f"q {self.queue_n2s}+{self.queue_s2n}")
        return "ok" if not parts else " ".join(parts)

    def activity_token(self) -> str:
        if self.worker_state == WorkerState.ERROR and self.error_message:
            return self.error_message[:96]
        if self.worker_state != WorkerState.RUNNING:
            return self.worker_state.value
        if self.rate_hint is not None and self.rate_hint > 0:
            if self.rate_hint >= 1:
                return f"{self.rate_hint:.0f} Hz"
            return f"{self.rate_hint:.0f} B/s"
        return "running"

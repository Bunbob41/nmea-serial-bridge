"""In-memory mission session telemetry for post-stop Mission Review."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

HealthTick = Literal["ok", "warn", "bad"]

BUCKET_INTERVAL_S = 5.0


@dataclass
class MissionSessionRecord:
    """Frozen view of one backup-enabled bridge session."""

    started_mono: float
    ended_mono: float
    duration_s: float
    backup_path: str
    total_bytes: int
    total_dropped: int
    avg_hz_up: float
    throughput_buckets: list[int] = field(default_factory=list)
    health_ticks: list[HealthTick] = field(default_factory=list)
    error: str = ""
    com: str = ""
    baud: int = 0

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "duration_s": self.duration_s,
            "avg_hz_up": self.avg_hz_up,
            "bytes": self.total_bytes,
            "dropped": self.total_dropped,
            "path": self.backup_path,
            "error": self.error,
            "com": self.com,
            "baud": self.baud,
        }


class MissionSessionRecorder:
    """Sample backup throughput + health while the bridge is running."""

    def __init__(self, *, bucket_s: float = BUCKET_INTERVAL_S) -> None:
        self._bucket_s = max(1.0, float(bucket_s))
        self._active = False
        self._started_mono = 0.0
        self._bucket_start_mono = 0.0
        self._bytes_at_bucket_start = 0
        self._last_backup_bytes = 0
        self._last_dropped = 0
        self._throughput_buckets: list[int] = []
        self._health_ticks: list[HealthTick] = []
        self._hz_samples: list[float] = []
        self._last_error = ""
        self._com = ""
        self._baud = 0
        self._dropped_at_bucket_start = 0

    @property
    def active(self) -> bool:
        return self._active

    def start(self, *, mono: float | None = None, com: str = "", baud: int = 0) -> None:
        now = mono if mono is not None else time.monotonic()
        self._active = True
        self._started_mono = now
        self._bucket_start_mono = now
        self._bytes_at_bucket_start = 0
        self._last_backup_bytes = 0
        self._last_dropped = 0
        self._throughput_buckets = []
        self._health_ticks = []
        self._hz_samples = []
        self._last_error = ""
        self._com = com
        self._baud = baud
        self._dropped_at_bucket_start = 0

    def sample(self, stats: dict, *, mono: float | None = None) -> None:
        if not self._active:
            return
        now = mono if mono is not None else time.monotonic()
        backup_bytes = int(stats.get("local_backup_bytes") or 0)
        dropped = int(stats.get("local_backup_dropped") or 0)
        hz_up = float(stats.get("hz_up") or 0.0)
        err = str(stats.get("local_backup_error") or "").strip()
        if err:
            self._last_error = err
        self._hz_samples.append(hz_up)
        self._last_backup_bytes = backup_bytes
        self._last_dropped = dropped

        while now - self._bucket_start_mono >= self._bucket_s:
            self._close_bucket(
                backup_bytes=backup_bytes,
                dropped=dropped,
                hz_up=hz_up,
                err=err,
            )
            self._bucket_start_mono += self._bucket_s

    def finalize(
        self,
        summary: dict[str, object],
        *,
        mono: float | None = None,
    ) -> MissionSessionRecord:
        now = mono if mono is not None else time.monotonic()
        if self._active:
            self._close_bucket(
                backup_bytes=int(summary.get("bytes") or self._last_backup_bytes),
                dropped=int(summary.get("dropped") or self._last_dropped),
                hz_up=self._hz_samples[-1] if self._hz_samples else 0.0,
                err=str(summary.get("error") or self._last_error),
                partial=True,
            )
            self._active = False
        duration = max(0.0, now - self._started_mono) if self._started_mono else 0.0
        hz_vals = [h for h in self._hz_samples if h > 0]
        avg_hz = sum(hz_vals) / len(hz_vals) if hz_vals else 0.0
        return MissionSessionRecord(
            started_mono=self._started_mono,
            ended_mono=now,
            duration_s=duration,
            backup_path=str(summary.get("path") or ""),
            total_bytes=int(summary.get("bytes") or 0),
            total_dropped=int(summary.get("dropped") or 0),
            avg_hz_up=avg_hz,
            throughput_buckets=list(self._throughput_buckets),
            health_ticks=list(self._health_ticks),
            error=str(summary.get("error") or self._last_error),
            com=self._com,
            baud=self._baud,
        )

    def _close_bucket(
        self,
        *,
        backup_bytes: int,
        dropped: int,
        hz_up: float,
        err: str,
        partial: bool = False,
    ) -> None:
        bucket_bytes = max(0, backup_bytes - self._bytes_at_bucket_start)
        self._throughput_buckets.append(bucket_bytes)
        self._bytes_at_bucket_start = backup_bytes
        drop_delta = max(0, dropped - self._dropped_at_bucket_start)
        self._dropped_at_bucket_start = dropped

        if err or drop_delta > 0:
            tick: HealthTick = "bad"
        elif bucket_bytes == 0 and hz_up >= 1.0:
            tick = "bad"
        elif bucket_bytes == 0 and hz_up > 0.2:
            tick = "warn"
        else:
            tick = "ok"
        self._health_ticks.append(tick)

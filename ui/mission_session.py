"""In-memory mission session telemetry for post-stop Mission Review."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal, Optional

HealthTick = Literal["ok", "warn", "bad"]

BUCKET_INTERVAL_S = 5.0


def compute_depth_session_metrics(
    soundings: list[dict[str, object]],
    *,
    depth_stats: dict[str, object] | None = None,
) -> dict[str, object]:
    """Derive Mission Review depth fields from mux buffer + live bridge stats."""
    stats = depth_stats or {}
    depths: list[float] = []
    last_nonzero: Optional[float] = None
    last_source = ""
    for row in soundings:
        try:
            depth = float(row.get("depth_m"))
        except (TypeError, ValueError):
            continue
        if depth >= 0:
            depths.append(depth)
        src = row.get("depth_source")
        if src:
            last_source = str(src)
    for row in reversed(soundings):
        try:
            depth = float(row.get("depth_m"))
        except (TypeError, ValueError):
            continue
        if depth > 0:
            last_nonzero = depth
            last_source = str(row.get("depth_source") or last_source)
            break
    avg_depth = sum(depths) / len(depths) if depths else None
    rate_hz = float(stats.get("depth_rate_hz") or 0.0)
    last_from_stats = stats.get("last_depth_m")
    last_depth: Optional[float] = last_nonzero
    if last_depth is None and last_from_stats is not None:
        try:
            last_depth = float(last_from_stats)
        except (TypeError, ValueError):
            last_depth = None
    return {
        "depth_enabled": bool(stats.get("depth_enabled")),
        "depth_port": str(stats.get("depth_port") or ""),
        "depth_rate_hz": rate_hz,
        "last_depth_m": last_depth,
        "avg_depth_m": avg_depth,
        "depth_source": last_source or str(stats.get("last_depth_source") or ""),
        "sounding_count": int(stats.get("sounding_count") or len(soundings)),
    }


def apply_depth_metrics_to_record(
    record: "MissionSessionRecord",
    soundings: list[dict[str, object]],
    *,
    depth_stats: dict[str, object] | None = None,
    avg_depth_rate_hz: float = 0.0,
) -> None:
    metrics = compute_depth_session_metrics(soundings, depth_stats=depth_stats)
    record.depth_enabled = bool(metrics.get("depth_enabled"))
    record.depth_port = str(metrics.get("depth_port") or "")
    record.depth_rate_hz = float(metrics.get("depth_rate_hz") or 0.0)
    record.avg_depth_rate_hz = float(avg_depth_rate_hz)
    last_depth = metrics.get("last_depth_m")
    record.last_depth_m = float(last_depth) if last_depth is not None else None
    avg_depth = metrics.get("avg_depth_m")
    record.avg_depth_m = float(avg_depth) if avg_depth is not None else None
    record.depth_source = str(metrics.get("depth_source") or "")
    record.sounding_count = int(metrics.get("sounding_count") or 0)
    record.soundings = list(soundings)


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
    com_active_s: float = 0.0
    last_com_to_net_age_s: Optional[float] = None
    udp_peer_count: int = 0
    soundings: list[dict[str, object]] = field(default_factory=list)
    depth_enabled: bool = False
    depth_port: str = ""
    depth_rate_hz: float = 0.0
    avg_depth_rate_hz: float = 0.0
    last_depth_m: Optional[float] = None
    avg_depth_m: Optional[float] = None
    depth_source: str = ""
    sounding_count: int = 0

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
            "com_active_s": self.com_active_s,
            "last_com_to_net_age_s": self.last_com_to_net_age_s,
            "udp_peer_count": self.udp_peer_count,
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
        self._depth_hz_samples: list[float] = []
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
        self._depth_hz_samples = []
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
        if stats.get("depth_enabled"):
            depth_hz = float(stats.get("depth_rate_hz") or 0.0)
            self._depth_hz_samples.append(depth_hz)
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
        depth_hz_vals = [h for h in self._depth_hz_samples if h > 0]
        avg_depth_hz = (
            sum(depth_hz_vals) / len(depth_hz_vals) if depth_hz_vals else 0.0
        )
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
            avg_depth_rate_hz=avg_depth_hz,
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

"""Mission Review timeline — scrub math and duration formatting."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ui.mission_session import BUCKET_INTERVAL_S, HealthTick, MissionSessionRecord


def format_mission_duration_hms(seconds: float) -> str:
    total = max(0, int(round(float(seconds))))
    hours, rem = divmod(total, 3600)
    mins, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}h {mins:02d}m {secs:02d}s"
    if mins > 0:
        return f"{mins:02d}m {secs:02d}s"
    return f"{secs:02d}s"


def format_scrub_clock(seconds: float) -> str:
    total = max(0, int(round(float(seconds))))
    hours, rem = divmod(total, 3600)
    mins, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:d}:{mins:02d}:{secs:02d}"
    return f"{mins:d}:{secs:02d}"


def timeline_bucket_count(record: MissionSessionRecord) -> int:
    ticks = record.health_ticks
    buckets = record.throughput_buckets
    if ticks:
        return len(ticks)
    if buckets:
        return len(buckets)
    if record.duration_s > 0:
        return max(1, int(record.duration_s // BUCKET_INTERVAL_S) + 1)
    return 1


def mission_error_rate_pct(
    record: MissionSessionRecord,
    *,
    through_bucket: Optional[int] = None,
) -> float:
    ticks = record.health_ticks
    if not ticks:
        return 100.0 if record.total_dropped > 0 else 0.0
    end = len(ticks) if through_bucket is None else min(len(ticks), through_bucket + 1)
    if end <= 0:
        return 0.0
    window = ticks[:end]
    bad = sum(1 for t in window if t == "bad")
    warn = sum(1 for t in window if t == "warn")
    return (bad + warn) * 100.0 / len(window)


@dataclass(frozen=True)
class MissionScrubSnapshot:
    bucket_index: int
    bucket_count: int
    elapsed_s: float
    cumulative_bytes: int
    error_rate_pct: float
    health_tick: Optional[HealthTick]
    elapsed_label: str
    end_label: str


def scrub_snapshot(record: MissionSessionRecord, bucket_index: int) -> MissionScrubSnapshot:
    n = timeline_bucket_count(record)
    idx = max(0, min(int(bucket_index), max(0, n - 1)))
    elapsed = min(record.duration_s, (idx + 1) * BUCKET_INTERVAL_S)
    buckets = record.throughput_buckets
    if buckets:
        cumulative = sum(buckets[: idx + 1])
    else:
        cumulative = int(record.total_bytes * (idx + 1) / max(n, 1))
    cumulative = min(record.total_bytes, max(0, cumulative))
    tick = record.health_ticks[idx] if record.health_ticks and idx < len(record.health_ticks) else None
    return MissionScrubSnapshot(
        bucket_index=idx,
        bucket_count=n,
        elapsed_s=elapsed,
        cumulative_bytes=cumulative,
        error_rate_pct=mission_error_rate_pct(record, through_bucket=idx),
        health_tick=tick,
        elapsed_label=format_scrub_clock(elapsed),
        end_label=format_scrub_clock(record.duration_s),
    )


def integrity_note_for_scrub(
    record: MissionSessionRecord, snap: MissionScrubSnapshot
) -> tuple[str, str]:
    at_end = snap.bucket_index >= snap.bucket_count - 1
    tick = snap.health_tick
    if tick == "bad":
        return ("Critical window — backup drops or write stress in this 5 s slice.", "#f87171")
    if tick == "warn":
        return ("Caution window — low backup throughput while COM was active.", "#fbbf24")
    if at_end and record.total_dropped <= 0 and mission_error_rate_pct(record) <= 0:
        return ("Data health timeline looks clean — ready for Quick Export.", "#94a3b8")
    if at_end:
        bad = sum(1 for t in record.health_ticks if t == "bad")
        warn_n = sum(1 for t in record.health_ticks if t == "warn")
        if bad > 0:
            return (f"Timeline shows {bad} critical window(s). Review before post-processing.", "#fbbf24")
        if warn_n > 0:
            return (f"{warn_n} caution window(s) — spot-check before export.", "#fbbf24")
    return (
        f"Scrubbing t={snap.elapsed_label} — green = continuous, red ticks = faults.",
        "#94a3b8",
    )
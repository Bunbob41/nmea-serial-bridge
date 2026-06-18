"""Quick Export — zip raw backup + mission_summary.txt for survey office handoff."""
from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

from ui.backup_status import _human_bytes
from ui.mission_session import MissionSessionRecord


def default_export_dir() -> Path:
    from ui.ui_prefs import effective_local_backup_base_dir

    return effective_local_backup_base_dir() / "exports"


def build_mission_summary_text(record: MissionSessionRecord) -> str:
    """Plain-text handoff manifest for the survey office."""
    mins = int(record.duration_s // 60)
    secs = int(record.duration_s % 60)
    lines = [
        "Serial Link — Mission Summary",
        f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}Z",
        "",
        f"Duration: {mins}m {secs}s ({record.duration_s:.1f} s)",
        f"Average COM→net Hz: {record.avg_hz_up:.2f}",
        f"Total backup bytes: {record.total_bytes:,} ({_human_bytes(record.total_bytes)})",
        f"Backup chunks dropped: {record.total_dropped:,}",
        f"Backup path: {record.backup_path or '(none)'}",
    ]
    if record.com:
        lines.append(f"Serial: {record.com} @ {record.baud}")
    if record.error:
        lines.append(f"Backup error: {record.error}")
    bad = sum(1 for t in record.health_ticks if t == "bad")
    warn = sum(1 for t in record.health_ticks if t == "warn")
    if record.health_ticks:
        lines.extend(
            [
                "",
                f"Data health timeline: {len(record.health_ticks)} windows "
                f"({bad} critical, {warn} caution)",
            ]
        )
    if record.throughput_buckets:
        peak = max(record.throughput_buckets)
        lines.append(f"Peak 5s backup throughput: {_human_bytes(peak)}")
    return "\n".join(lines) + "\n"


def quick_export_mission(
    record: MissionSessionRecord,
    *,
    dest_dir: Path | None = None,
) -> Path:
    """Package .raw backup and mission_summary.txt into a timestamped zip."""
    raw_path = Path(record.backup_path) if record.backup_path else None
    if raw_path is None or not raw_path.is_file():
        raise FileNotFoundError(
            record.backup_path or "No backup .raw file path recorded for this session."
        )

    out_dir = dest_dir or default_export_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = out_dir / f"mission_{stamp}.zip"

    summary_name = "mission_summary.txt"
    summary_body = build_mission_summary_text(record)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(summary_name, summary_body)
        zf.write(raw_path, arcname=raw_path.name)

    return zip_path

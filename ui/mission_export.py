"""Mission export — save-as handoff for survey office / GIS tools."""
from __future__ import annotations

import csv
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from core.local_logger import LOCAL_BACKUP_EXT, LOCAL_BACKUP_LEGACY_EXT
from nmea_codec import nmea_sentence_type
from ui.backup_status import _human_bytes
from ui.mission_session import MissionSessionRecord
from nmea_position import parse_nmea_position

SESSION_BACKUP_SUFFIXES = (LOCAL_BACKUP_EXT, LOCAL_BACKUP_LEGACY_EXT, ".log", ".txt")

QUICK_EXPORT_SAVE_FILTER = (
    "NMEA / log (*.nmea *.log *.txt);;NMEA files (*.nmea);;"
    "Log files (*.log);;Text files (*.txt);;All files (*)"
)
CSV_EXPORT_FILTER = "CSV files (*.csv);;All files (*)"
KML_EXPORT_FILTER = "KML files (*.kml);;All files (*)"
TXT_EXPORT_FILTER = "Text files (*.txt);;All files (*)"


def default_export_dir() -> Path:
    from ui.ui_prefs import effective_local_backup_base_dir

    return effective_local_backup_base_dir() / "exports"


def resolve_session_backup_path(record: MissionSessionRecord) -> Path:
    """Return on-disk session backup (.nmea preferred; legacy .raw accepted)."""
    raw = (record.backup_path or "").strip()
    if not raw:
        raise FileNotFoundError("No session backup path recorded for this mission.")
    path = Path(raw)
    if path.is_file():
        return path
    raise FileNotFoundError(f"Session backup file not found:\n{path}")


def suggest_quick_export_path(
    record: MissionSessionRecord,
    *,
    dest_dir: Path | None = None,
    default_ext: str = ".nmea",
) -> Path:
    """Default save-as path for Quick Export (survey-office friendly extension)."""
    source = resolve_session_backup_path(record)
    out_dir = dest_dir or default_export_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = default_ext if default_ext.startswith(".") else f".{default_ext}"
    return out_dir / f"{source.stem}{ext}"


def export_session_backup_copy(source: Path, dest: Path) -> Path:
    """Copy session backup bytes to operator-chosen .nmea / .log / .txt path."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return dest


def export_session_nmea_csv(source: Path, dest: Path) -> Path:
    """Parse session backup lines into a survey-office CSV."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[int, str, str, str]] = []
    with source.open("r", encoding="utf-8", errors="replace") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line.startswith("$"):
                continue
            st = nmea_sentence_type(line) or ""
            rows.append((line_no, "", st, line))
    with dest.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(("line", "utc", "sentence_type", "raw_nmea"))
        writer.writerows(rows)
    return dest


def export_session_track_kml(
    source: Path,
    dest: Path,
    *,
    track_name: str = "Mission track",
) -> Path:
    """Build a simple KML track from GGA/RMC fixes in the session backup."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    coords: list[tuple[float, float]] = []
    with source.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line.startswith("$"):
                continue
            pos = parse_nmea_position(line)
            if pos is None:
                continue
            coords.append((pos.lon, pos.lat))
    if not coords:
        raise ValueError("No GGA/RMC positions found in the session backup for KML export.")
    coord_text = " ".join(f"{lon:.6f},{lat:.6f},0" for lon, lat in coords)
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        "  <Document>\n"
        f"    <name>{track_name}</name>\n"
        "    <Placemark>\n"
        f"      <name>{track_name}</name>\n"
        "      <LineString>\n"
        "        <tessellate>1</tessellate>\n"
        f"        <coordinates>{coord_text}</coordinates>\n"
        "      </LineString>\n"
        "    </Placemark>\n"
        "  </Document>\n"
        "</kml>\n"
    )
    dest.write_text(body, encoding="utf-8")
    return dest


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


def quick_export_mission_zip(
    record: MissionSessionRecord,
    *,
    dest_dir: Path | None = None,
) -> Path:
    """Package session backup and mission_summary.txt into a timestamped zip."""
    backup_path = resolve_session_backup_path(record)
    out_dir = dest_dir or default_export_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = out_dir / f"mission_{stamp}.zip"

    summary_name = "mission_summary.txt"
    summary_body = build_mission_summary_text(record)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(summary_name, summary_body)
        zf.write(backup_path, arcname=backup_path.name)

    return zip_path


# Back-compat alias for tests and older call sites.
quick_export_mission = quick_export_mission_zip

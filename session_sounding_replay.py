"""Replay muxed soundings from a session NMEA backup (export-quality path)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from depth_codec import DepthSample, parse_depth_line
from nmea_codec import nmea_sentence_type
from nmea_position import parse_nmea_position


def _nmea_payload(raw: str) -> str:
    """Extract the NMEA sentence from a raw backup/log line."""
    line = (raw or "").strip()
    if not line:
        return ""
    if line.startswith("$") or line.startswith("!"):
        return line
    if "|" in line:
        tail = line.split("|")[-1].strip()
        if tail.startswith("$") or tail.startswith("!"):
            return tail
    idx = line.find("$")
    if idx >= 0:
        return line[idx:].strip()
    idx = line.find("!")
    if idx >= 0:
        return line[idx:].strip()
    return ""


def _parse_hms_field(time_hhmmss: str) -> Optional[tuple[int, int, float]]:
    raw = (time_hhmmss or "").strip()
    if len(raw) < 6:
        return None
    try:
        hours = int(raw[0:2])
        minutes = int(raw[2:4])
        seconds = float(raw[4:])
    except ValueError:
        return None
    if not (0 <= hours < 24 and 0 <= minutes < 60 and 0.0 <= seconds < 60.0):
        return None
    return hours, minutes, seconds


def nmea_utc_to_epoch(date_ddmmyy: str, time_hhmmss: str) -> Optional[float]:
    """Combine RMC/ZDA date (DDMMYY) with HHMMSS.ss into UTC epoch seconds."""
    hms = _parse_hms_field(time_hhmmss)
    if hms is None:
        return None
    hours, minutes, seconds = hms
    sec_int = int(seconds)
    micro = int(round((seconds - sec_int) * 1_000_000))
    date_raw = (date_ddmmyy or "").strip()
    if len(date_raw) >= 6:
        try:
            day = int(date_raw[0:2])
            month = int(date_raw[2:4])
            year = int(date_raw[4:6])
        except ValueError:
            return None
        year += 2000 if year < 80 else 1900
        try:
            dt = datetime(
                year,
                month,
                day,
                hours,
                minutes,
                sec_int,
                micro,
                tzinfo=timezone.utc,
            )
        except ValueError:
            return None
        return dt.timestamp()
    return None


def format_export_timestamp(
    utc_time: str,
    *,
    utc_date: str = "",
    epoch: Optional[float] = None,
) -> str:
    """CSV-friendly UTC label; ISO when date+time are complete."""
    if epoch is not None:
        dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    time_raw = (utc_time or "").strip()
    date_raw = (utc_date or "").strip()
    if time_raw and date_raw and len(date_raw) >= 6:
        return f"{date_raw[4:6]}{date_raw[2:4]}{date_raw[0:2]} {time_raw} UTC"
    if time_raw:
        return time_raw
    return ""


@dataclass(frozen=True)
class _FixContext:
    lat: float
    lon: float
    source: str
    utc_time: str
    utc_date: str
    epoch: Optional[float]
    line_no: int


def _fix_context_from_line(line: str, *, line_no: int, carry_date: str) -> Optional[_FixContext]:
    pos = parse_nmea_position(line)
    if pos is None:
        return None
    st = nmea_sentence_type(line) or ""
    parts = line.split(",")
    utc_time = ""
    utc_date = carry_date
    if st == "GGA" and len(parts) >= 2:
        utc_time = (parts[1] or "").strip()
    elif st == "RMC" and len(parts) >= 10:
        utc_time = (parts[1] or "").strip()
        rmc_date = (parts[9] or "").strip()
        if rmc_date:
            utc_date = rmc_date
    epoch = nmea_utc_to_epoch(utc_date, utc_time) if utc_time else None
    return _FixContext(
        lat=float(pos.lat),
        lon=float(pos.lon),
        source=str(pos.source or st.lower()),
        utc_time=utc_time,
        utc_date=utc_date,
        epoch=epoch,
        line_no=line_no,
    )


def _depth_row(sample: DepthSample, fix: _FixContext) -> dict[str, Any]:
    return {
        "timestamp": format_export_timestamp(
            fix.utc_time,
            utc_date=fix.utc_date,
            epoch=fix.epoch,
        ),
        "lat": fix.lat,
        "lon": fix.lon,
        "depth_m": float(sample.depth_m),
        "fix_stale": False,
        "depth_source": sample.source,
        "fix_age_ms": max(0, (fix.line_no - int(sample.received_mono)) * 1000),
    }


def _assign_pending_depths(
    pending: list[DepthSample],
    fix: _FixContext,
    out: list[dict[str, Any]],
) -> None:
    for sample in pending:
        out.append(_depth_row(sample, fix))
    pending.clear()


def replay_soundings_from_lines(lines: list[str]) -> list[dict[str, Any]]:
    """Walk backup lines in order; bind each depth to the next GGA/RMC block fix."""
    out: list[dict[str, Any]] = []
    pending: list[DepthSample] = []
    last_fix: Optional[_FixContext] = None
    carry_date = ""

    for line_no, raw in enumerate(lines, start=1):
        line = _nmea_payload(raw)
        if not line:
            continue

        fix = _fix_context_from_line(line, line_no=line_no, carry_date=carry_date)
        if fix is not None:
            if fix.utc_date:
                carry_date = fix.utc_date
            if pending:
                _assign_pending_depths(pending, fix, out)
            last_fix = fix
            continue

        sample = parse_depth_line(line)
        if sample is not None:
            pending.append(
                DepthSample(
                    depth_m=sample.depth_m,
                    source=sample.source,
                    raw_line=sample.raw_line,
                    received_mono=float(line_no),
                )
            )

    if pending and last_fix is not None:
        _assign_pending_depths(pending, last_fix, out)
    return out


def replay_soundings_from_backup(path: Path) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    rows = replay_soundings_from_lines(text.splitlines())
    return [row for row in rows if row.get("lat") is not None and row.get("lon") is not None]


def backup_has_depth_sentences(path: Path) -> bool:
    with Path(path).open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = _nmea_payload(raw)
            if line and parse_depth_line(line) is not None:
                return True
    return False

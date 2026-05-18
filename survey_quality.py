"""Live GNSS quality hints from NMEA GGA (survey accuracy principles).

Thresholds align with Applanix POSPac MMS Ch.16 (Solution Quality Assessment):
  - HDOP/PDOP: ideal < 2.5, acceptable < 4.0 (GGA reports HDOP).
  - Satellites: 5+ recommended for missions; 7+ with HDOP < 3 for reliable fix.
  - Fix quality: RTK fixed preferred; autonomous GPS is survey-weak until differential/RTK.

Bridge transport (drops, rejects, gaps) is separate — see ui.stats_line.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from nmea_codec import nmea_sentence_type


class NavQualityLevel(str, Enum):
    GOOD = "good"
    OK = "ok"
    WARN = "warn"
    BAD = "bad"
    UNKNOWN = "unknown"


# NMEA GGA fix quality (field 6)
GGA_FIX_LABELS: dict[int, str] = {
    0: "No fix",
    1: "GPS",
    2: "DGPS",
    3: "PPS",
    4: "RTK fixed",
    5: "RTK float",
    6: "Estimated",
    7: "Manual",
    8: "Simulation",
}

HDOP_IDEAL = 2.5
HDOP_ACCEPT = 4.0
SATS_MIN_MISSION = 5
SATS_RELIABLE = 7
HDOP_RELIABLE = 3.0
NAV_STALE_S = 3.0


@dataclass(frozen=True)
class GgaFields:
    quality: int
    num_sats: int
    hdop: float
    utc_time: str = ""


@dataclass(frozen=True)
class NavAssessment:
    level: NavQualityLevel
    fix_label: str
    num_sats: int
    hdop: float
    summary: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "fix_label": self.fix_label,
            "quality": self._quality_code(),
            "num_sats": self.num_sats,
            "hdop": self.hdop,
            "summary": self.summary,
            "detail": self.detail,
            "mono": time.monotonic(),
        }

    def _quality_code(self) -> int:
        for code, label in GGA_FIX_LABELS.items():
            if label == self.fix_label:
                return code
        return -1


def parse_gga_fields(line: str) -> Optional[GgaFields]:
    """Parse $xxGGA fix quality, satellite count, and HDOP."""
    s = line.strip()
    if nmea_sentence_type(s) != "GGA":
        return None
    parts = s.split(",")
    if len(parts) < 9:
        return None
    try:
        quality = int(parts[6] or "0")
    except ValueError:
        quality = 0
    try:
        num_sats = int(parts[7] or "0")
    except ValueError:
        num_sats = 0
    try:
        hdop = float(parts[8] or "0")
    except ValueError:
        hdop = 0.0
    utc_time = (parts[1] or "").strip()
    return GgaFields(quality=quality, num_sats=num_sats, hdop=hdop, utc_time=utc_time)


def _level_rank(level: NavQualityLevel) -> int:
    order = {
        NavQualityLevel.UNKNOWN: 0,
        NavQualityLevel.GOOD: 1,
        NavQualityLevel.OK: 2,
        NavQualityLevel.WARN: 3,
        NavQualityLevel.BAD: 4,
    }
    return order.get(level, 0)


def _max_level(a: NavQualityLevel, b: NavQualityLevel) -> NavQualityLevel:
    return a if _level_rank(a) >= _level_rank(b) else b


def assess_navigation_quality(fields: GgaFields) -> NavAssessment:
    """Score one GGA epoch using POSPac-style live survey rules."""
    fix = fields.quality
    sats = fields.num_sats
    hdop = fields.hdop
    fix_label = GGA_FIX_LABELS.get(fix, f"fix {fix}")
    issues: list[str] = []
    level = NavQualityLevel.GOOD

    if fix == 0:
        return NavAssessment(
            NavQualityLevel.BAD,
            fix_label,
            sats,
            hdop,
            "No GPS fix",
            "Wait for fix before surveying; check antenna and corrections.",
        )

    if fix == 5:
        level = NavQualityLevel.WARN
        issues.append("RTK float — not fixed integer")
    elif fix == 6:
        level = NavQualityLevel.WARN
        issues.append("Estimated fix")
    elif fix == 8:
        level = NavQualityLevel.BAD
        issues.append("Simulation mode")
    elif fix == 1:
        level = NavQualityLevel.OK
        issues.append("Autonomous GPS — use DGPS/RTK for survey grade")
    elif fix == 2:
        level = NavQualityLevel.OK
    elif fix == 4:
        level = NavQualityLevel.GOOD

    if hdop >= HDOP_ACCEPT:
        level = _max_level(level, NavQualityLevel.BAD)
        issues.append(f"HDOP {hdop:.1f} ≥ {HDOP_ACCEPT} (not acceptable)")
    elif hdop >= HDOP_IDEAL:
        level = _max_level(level, NavQualityLevel.OK)
        issues.append(f"HDOP {hdop:.1f} elevated (ideal < {HDOP_IDEAL})")
    elif hdop >= HDOP_RELIABLE and sats < SATS_RELIABLE:
        level = _max_level(level, NavQualityLevel.WARN)
        issues.append(f"HDOP {hdop:.1f} with only {sats} sats (prefer {SATS_RELIABLE}+ & HDOP < {HDOP_RELIABLE})")

    if sats < SATS_MIN_MISSION:
        level = _max_level(level, NavQualityLevel.WARN)
        issues.append(f"{sats} satellites (< {SATS_MIN_MISSION} mission minimum)")
    elif sats < SATS_RELIABLE and hdop < HDOP_RELIABLE and fix in (2, 4):
        level = _max_level(level, NavQualityLevel.OK)
        issues.append(f"{sats} sats (POSPac: {SATS_RELIABLE}+ with low DOP is more reliable)")

    if level == NavQualityLevel.GOOD and not issues:
        summary = f"{fix_label} · {sats} sats · HDOP {hdop:.1f}"
    else:
        summary = f"{fix_label} · {sats} sats · HDOP {hdop:.1f}"
    detail = "; ".join(issues) if issues else "Meets live GGA survey hints (POSPac Ch.16)."
    return NavAssessment(level, fix_label, sats, hdop, summary, detail)


def update_nav_quality_from_line(line: str) -> Optional[dict[str, Any]]:
    fields = parse_gga_fields(line)
    if fields is None:
        return None
    return assess_navigation_quality(fields).to_dict()


def feed_nmea_navigation_quality(lines: list[bytes], state: list[Optional[dict[str, Any]]]) -> None:
    """Keep latest GGA assessment in state[0] (same pattern as UTC time)."""
    for chunk in lines:
        try:
            text = chunk.decode(errors="replace")
        except Exception:
            continue
        for line in text.splitlines():
            snap = update_nav_quality_from_line(line)
            if snap is not None:
                state[0] = snap


def nav_quality_stale(nav: Optional[dict[str, Any]], *, now: Optional[float] = None) -> bool:
    if not nav:
        return True
    mono = nav.get("mono")
    if mono is None:
        return True
    t = now if now is not None else time.monotonic()
    try:
        return (t - float(mono)) > NAV_STALE_S
    except (TypeError, ValueError):
        return True


def format_gnss_status_chip(
    nav: Optional[dict[str, Any]],
    *,
    running: bool,
    raw_mode: bool = False,
) -> str:
    if not running:
        return "GNSS: —"
    if raw_mode:
        return "GNSS: n/a (raw)"
    if not nav or nav_quality_stale(nav):
        return "GNSS: no recent GGA"
    level = str(nav.get("level", ""))
    summary = str(nav.get("summary", "—"))
    if level == NavQualityLevel.BAD.value:
        return f"GNSS: {summary}"
    if level == NavQualityLevel.WARN.value:
        return f"GNSS: caution · {summary}"
    return f"GNSS: {summary}"


def format_gnss_stats_segment(nav: Optional[dict[str, Any]]) -> str:
    if not nav:
        return ""
    stale = bool(nav.get("nav_stale"))
    if not stale and "nav_stale" not in nav:
        stale = nav_quality_stale(nav)
    if stale:
        return " · GNSS: no recent GGA (>3 s)"
    level = str(nav.get("level", ""))
    summary = str(nav.get("summary", ""))
    if level in (NavQualityLevel.WARN.value, NavQualityLevel.BAD.value):
        return f" · GNSS: {summary} ({level})"
    return f" · GNSS: {summary}"

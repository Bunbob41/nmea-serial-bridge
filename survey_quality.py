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
NAV_STALE_S = 2.0


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


def nav_quality_stale(
    nav: Optional[dict[str, Any]],
    *,
    now: Optional[float] = None,
    stale_s: Optional[float] = None,
) -> bool:
    if not nav:
        return True
    mono = nav.get("mono")
    if mono is None:
        return True
    t = now if now is not None else time.monotonic()
    limit = NAV_STALE_S if stale_s is None else stale_s
    try:
        return (t - float(mono)) > limit
    except (TypeError, ValueError):
        return True


def nav_quality_stream_idle_snapshot() -> dict[str, Any]:
    """Reset GNSS HUD fields when NMEA traffic or GGA parsing has stopped."""
    return {
        "level": NavQualityLevel.BAD.value,
        "fix_label": GGA_FIX_LABELS[0],
        "quality": 0,
        "num_sats": 0,
        "hdop": 0.0,
        "summary": "No Data Stream",
        "detail": "No NMEA traffic or GGA in the last 2 s.",
        "nav_stale": True,
        "stream_idle": True,
    }


def nav_metrics_should_reset(
    *,
    traffic_hz: float,
    nav: Optional[dict[str, Any]],
    last_nmea_mono: Optional[float] = None,
    running: bool = True,
    now: Optional[float] = None,
) -> bool:
    """True when live GNSS metrics should clear (0 Hz or no fresh GGA/NMEA)."""
    if not running:
        return False
    if traffic_hz <= 0.0:
        return True
    t = now if now is not None else time.monotonic()
    if last_nmea_mono is not None:
        try:
            if (t - float(last_nmea_mono)) > NAV_STALE_S:
                return True
        except (TypeError, ValueError):
            return True
    return nav_quality_stale(nav, now=t)


_GNSS_BADGE_STYLE = "padding: 6px; border-radius: 4px; font-weight: bold;"
_GNSS_BADGE_STYLE_HUD = "padding: 0px 4px; border-radius: 3px; font-weight: bold;"

# Compact HUD tile labels (Corner / horizontal strip); full text in tooltip.
_GNSS_FIX_HUD_SHORT: dict[str, str] = {
    "No fix": "No fix",
    "GPS": "GPS",
    "DGPS": "DGPS",
    "PPS": "PPS",
    "RTK fixed": "RTK-F",
    "RTK float": "RTK-FL",
    "Estimated": "Est.",
    "Manual": "Man.",
    "Simulation": "Sim.",
}


def gnss_fix_label_hud_display(fix_label: str, *, narrow: bool) -> str:
    """Survey HUD GNSS badge text — short form when the tile is too narrow."""
    label = (fix_label or "—").strip()
    if not narrow:
        return label
    return _GNSS_FIX_HUD_SHORT.get(label, label[:10] if len(label) > 10 else label)


def gnss_status_hud_badge_text(
    *,
    stream_idle: bool = False,
    nav_stale: bool = False,
    fix_label: str = "",
    narrow: bool = False,
) -> str:
    """Survey HUD GNSS value — short idle/stale labels; hover tooltip has full detail."""
    if stream_idle:
        return "Idle"
    if nav_stale:
        return "Stale"
    return gnss_fix_label_hud_display(fix_label, narrow=narrow)


def gnss_status_badge_quality(
    nav: Optional[dict[str, Any]],
    *,
    running: bool,
    raw_mode: bool = False,
) -> Optional[int]:
    """NMEA GGA quality for status-badge coloring; None = no badge (stopped/raw)."""
    if not running or raw_mode:
        return None
    if not nav:
        return 0
    if (
        nav.get("stream_idle")
        or nav.get("nav_stale")
        or str(nav.get("summary", "")) == "No Data Stream"
    ):
        return 0
    if nav_quality_stale(nav):
        return 0
    q = nav.get("quality")
    if isinstance(q, int) and not isinstance(q, bool):
        return q
    try:
        return int(q)
    except (TypeError, ValueError):
        return 0


def gnss_status_badge_stylesheet(quality: Optional[int], *, hud: bool = False) -> str:
    """Polished status-bar / HUD badge colors from NMEA fix quality."""
    if quality is None:
        return ""
    frame = _GNSS_BADGE_STYLE_HUD if hud else _GNSS_BADGE_STYLE
    if quality in (4, 5):
        if hud:
            return f"background-color: #2d5a38; color: #d8f5e0; {frame}"
        return f"background-color: #D4EDDA; color: #155724; {frame}"
    if quality in (1, 2):
        if hud:
            return f"background-color: #1e3f66; color: #d6ebff; {frame}"
        return f"background-color: #CCE5FF; color: #004085; {frame}"
    if hud:
        return f"background-color: #5c2a32; color: #fce8ea; {frame}"
    return f"background-color: #F8D7DA; color: #721C24; {frame}"


def format_gnss_status_tooltip(
    nav: Optional[dict[str, Any]],
    *,
    running: bool = True,
    raw_mode: bool = False,
) -> str:
    """Full GNSS status for hover (HUD tile, status bar chip) when the label is clipped."""
    if not running:
        return "GNSS quality appears while the bridge is Running."
    if raw_mode:
        return (
            "Raw binary mode — no GGA parsing.\n"
            "Use Passthrough or Strict for live fix, satellites, and HDOP."
        )
    if not nav:
        return "No GGA in the last ~2 seconds.\nCheck INS output, cable, and NMEA filter."
    if nav.get("stream_idle") or str(nav.get("summary", "")) == "No Data Stream":
        return "No NMEA stream on the wire.\nStart the bridge and confirm traffic on Connect / Log."
    if nav_quality_stale(nav):
        return (
            f"No fresh GGA in the last ~{NAV_STALE_S:.0f} s.\n"
            "Check INS output and that strict mode is not dropping all sentences."
        )
    fix = str(nav.get("fix_label") or GGA_FIX_LABELS.get(int(nav.get("quality", -1)), "—"))
    lines = [f"Fix: {fix}"]
    sats = nav.get("num_sats")
    if sats is not None:
        lines.append(f"Satellites: {sats}")
    hdop = nav.get("hdop")
    if hdop is not None:
        try:
            lines.append(f"HDOP: {float(hdop):.1f}")
        except (TypeError, ValueError):
            lines.append(f"HDOP: {hdop}")
    summary = str(nav.get("summary") or "").strip()
    if summary:
        lines.append(summary)
    detail = str(nav.get("detail") or "").strip()
    if detail and detail not in lines:
        lines.append(detail)
    level = str(nav.get("level") or "").strip()
    if level and level not in ("good", ""):
        lines.append(f"Assessment: {level}")
    return "\n".join(lines)


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
    if not nav:
        return "GNSS: no recent GGA"
    if nav.get("stream_idle") or str(nav.get("summary", "")) == "No Data Stream":
        return "GNSS: No Data Stream"
    if nav_quality_stale(nav):
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
    if nav.get("stream_idle") or str(nav.get("summary", "")) == "No Data Stream":
        return " · GNSS: No Data Stream"
    if stale:
        return f" · GNSS: no recent GGA (>{NAV_STALE_S:.0f} s)"
    level = str(nav.get("level", ""))
    summary = str(nav.get("summary", ""))
    if level in (NavQualityLevel.WARN.value, NavQualityLevel.BAD.value):
        return f" · GNSS: {summary} ({level})"
    return f" · GNSS: {summary}"

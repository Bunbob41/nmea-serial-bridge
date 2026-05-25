"""WGS84 position from NMEA GGA/RMC (bridge + web map; Survey HUD may consume same fields)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

from nmea_codec import nmea_sentence_type


@dataclass(frozen=True)
class NmeaPosition:
    lat: float
    lon: float
    source: str  # "gga" | "rmc"

    def to_dict(self) -> dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "source": self.source,
            "mono": time.monotonic(),
        }


def nmea_dm_to_decimal(dm: str, hemisphere: str) -> Optional[float]:
    """Convert NMEA DDMM.mmmm (+ hemisphere) to signed decimal degrees."""
    raw = (dm or "").strip()
    hemi = (hemisphere or "").strip().upper()
    if not raw or not hemi:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    degrees = int(value // 100)
    minutes = value - degrees * 100
    decimal = degrees + minutes / 60.0
    if hemi in ("S", "W"):
        decimal = -decimal
    elif hemi not in ("N", "E"):
        return None
    return decimal


def parse_gga_position(line: str) -> Optional[NmeaPosition]:
    """Parse latitude/longitude from a $xxGGA sentence."""
    s = line.strip()
    if nmea_sentence_type(s) != "GGA":
        return None
    parts = s.split(",")
    if len(parts) < 7:
        return None
    lat = nmea_dm_to_decimal(parts[2], parts[3])
    lon = nmea_dm_to_decimal(parts[4], parts[5])
    if lat is None or lon is None:
        return None
    if abs(lat) > 90.0 or abs(lon) > 180.0:
        return None
    return NmeaPosition(lat=lat, lon=lon, source="gga")


def parse_rmc_position(line: str) -> Optional[NmeaPosition]:
    """Parse latitude/longitude from a $xxRMC sentence when status is valid."""
    s = line.strip()
    if nmea_sentence_type(s) != "RMC":
        return None
    parts = s.split(",")
    if len(parts) < 8:
        return None
    status = (parts[2] or "").strip().upper()
    if status not in ("A", "D"):
        return None
    lat = nmea_dm_to_decimal(parts[3], parts[4])
    lon = nmea_dm_to_decimal(parts[5], parts[6])
    if lat is None or lon is None:
        return None
    if abs(lat) > 90.0 or abs(lon) > 180.0:
        return None
    return NmeaPosition(lat=lat, lon=lon, source="rmc")


def parse_nmea_position(line: str) -> Optional[NmeaPosition]:
    """Prefer GGA, then RMC, for a single NMEA line."""
    pos = parse_gga_position(line)
    if pos is not None:
        return pos
    return parse_rmc_position(line)


def feed_nmea_position(lines: list[bytes], state: list[Optional[dict[str, Any]]]) -> None:
    """Keep latest fix in state[0] (parallel to UTC and nav-quality state)."""
    for chunk in lines:
        try:
            text = chunk.decode(errors="replace")
        except Exception:
            continue
        for line in text.splitlines():
            pos = parse_nmea_position(line)
            if pos is not None:
                state[0] = pos.to_dict()

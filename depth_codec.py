"""Parse single-beam depth sentences (GUI-free)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

from nmea_codec import nmea_checksum_ok, nmea_sentence_type

_FEET_TO_M = 0.3048


@dataclass(frozen=True)
class DepthSample:
    depth_m: float
    source: str
    raw_line: str
    received_mono: float


def _parse_float(field: str) -> Optional[float]:
    raw = (field or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_nmea_depth(line: str) -> Optional[DepthSample]:
    text = line.strip()
    if not text.startswith("$"):
        return None
    if "*" in text and not nmea_checksum_ok(text):
        return None
    st = nmea_sentence_type(text)
    body = text.split("*", 1)[0]
    parts = body.split(",")
    if not parts:
        return None
    tag = parts[0].lstrip("$").upper()
    now = time.monotonic()
    if st == "DPT" or tag.endswith("DPT"):
        if len(parts) < 2:
            return None
        depth = _parse_float(parts[1])
        if depth is None or depth < 0:
            return None
        return DepthSample(depth_m=depth, source="sddpt", raw_line=text, received_mono=now)
    if st == "DBT" or tag.endswith("DBT"):
        if len(parts) < 4:
            return None
        depth_m = _parse_float(parts[3])
        if depth_m is not None and depth_m >= 0:
            return DepthSample(depth_m=depth_m, source="sddbt", raw_line=text, received_mono=now)
        depth_ft = _parse_float(parts[1])
        if depth_ft is None or depth_ft < 0:
            return None
        return DepthSample(depth_m=depth_ft * _FEET_TO_M, source="sddbt", raw_line=text, received_mono=now)
    return None


def _parse_sonarmite_ascii(line: str) -> Optional[DepthSample]:
    text = line.strip()
    if text.startswith("$"):
        return None
    if not re.match(r"^[\d.\s+-]+$", text):
        return None
    parts = text.split()
    if len(parts) < 6:
        return None
    depth = _parse_float(parts[5])
    if depth is None or depth < 0:
        return None
    return DepthSample(depth_m=depth, source="sonarmite_ascii", raw_line=text, received_mono=time.monotonic())


def depth_display_field(sample: DepthSample) -> str:
    """Original depth field text from the source sentence (preserves decimal places)."""
    raw = (sample.raw_line or "").strip()
    if sample.source == "sonarmite_ascii":
        parts = raw.split()
        if len(parts) >= 6 and parts[5].strip():
            return parts[5].strip()
    if raw.startswith("$"):
        body = raw.split("*", 1)[0]
        parts = body.split(",")
        tag = parts[0].lstrip("$").upper() if parts else ""
        if (tag.endswith("DPT") or tag == "DPT") and len(parts) >= 2 and parts[1].strip():
            return parts[1].strip()
        if (tag.endswith("DBT") or tag == "DBT") and len(parts) >= 4:
            if parts[3].strip():
                return parts[3].strip()
            if len(parts) >= 2 and parts[1].strip():
                return parts[1].strip()
    return f"{sample.depth_m:.2f}"


def parse_depth_line(line: str) -> Optional[DepthSample]:
    if not line or not str(line).strip():
        return None
    try:
        text = str(line).strip()
        nmea = _parse_nmea_depth(text)
        if nmea is not None:
            return nmea
        return _parse_sonarmite_ascii(text)
    except Exception:
        return None
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


#: Ohmex SonarMite ASCII layouts by field count, from Ohmex's own manuals:
#:   SM3hardware.pdf, http://www.ohmex.com/SM3hardware.pdf, 1,103,999 bytes,
#:     SHA-256 232ff5cdad69a7c2d04a9c1b6b1106bb47d3f4d873c97d3b66d10764fe26b30c, p.16;
#:   BTXhardware.pdf, http://www.ohmex.com/BTXhardware.pdf, 800,981 bytes,
#:     SHA-256 13a6f9acfcc224b745a771978451ac79a52d287df12a4d7ebfa5a349b6ccc2ef, p.23;
#:   DFXhardware.pdf, http://www.ohmex.com/DFXhardware.pdf, 2,530,854 bytes,
#:     SHA-256 3042c54c5e628e518d4998215ce65bcc558703ecc378e32ef2dbc349f48057aa, p.19 (DRAFT).
#:   8 fields: Old (SM3/BTX Format 0, DFX Format 8): "id depth roll pitch heave battery qa flags"
#:   6 fields: DFX (Format 0): "id hdepth ldepth wtemp battery flags", flags bit 1 = high
#:             frequency seen
#:   5 fields: New (SM3/BTX Format 8): id depth battery qa flags (inferred from the manuals'
#:             samples; no field list is printed for it)
#: The depth is FIELD 1 (0-based) in every layout (DFX: the high-frequency depth). This code
#: previously read field 5, which is the BATTERY voltage in the Old layout and the seen-bitmask
#: in DFX's: the manual's own sample "1 0.48 0 0 0 8.9 115 0" is 0.48 m, not 8.9.
#: Any other field count is not read: a layout is never guessed.
#: NO READING (SM3 p.16, BTX p.23: no transducer seen or qa below 5 (out of water) gives a
#: string of nulls; DFX p.19: "ID+5 nulls"). Every form of no reading gives None, never 0.0:
#: a depth of 0 or less, a qa under 5 (Old field 6, New field 3), and a DFX line whose
#: high-frequency seen bit (flags & 1) is clear.
SONARMITE_FIELD_COUNTS = (5, 6, 8)
SONARMITE_DEPTH_FIELD = 1
SONARMITE_QA_FIELD = {8: 6, 5: 3}
SONARMITE_QA_MIN = 5
SONARMITE_DFX_FLAGS_FIELD = 5


def _parse_sonarmite_ascii(line: str) -> Optional[DepthSample]:
    text = line.strip()
    if text.startswith("$"):
        return None
    if not re.match(r"^[\d.\s+-]+$", text):
        return None
    parts = text.split()
    if len(parts) not in SONARMITE_FIELD_COUNTS:
        return None
    depth = _parse_float(parts[SONARMITE_DEPTH_FIELD])
    if depth is None or depth <= 0:
        return None
    qa_field = SONARMITE_QA_FIELD.get(len(parts))
    if qa_field is not None:
        qa = _parse_float(parts[qa_field])
        if qa is None or qa < SONARMITE_QA_MIN:
            return None
    else:  # DFX: no quality field; the high-frequency depth must have been seen
        seen = _parse_float(parts[SONARMITE_DFX_FLAGS_FIELD])
        if seen is None or not (int(seen) & 1):
            return None
    return DepthSample(depth_m=depth, source="sonarmite_ascii", raw_line=text, received_mono=time.monotonic())


def depth_display_field(sample: DepthSample) -> str:
    """Original depth field text from the source sentence (preserves decimal places)."""
    raw = (sample.raw_line or "").strip()
    if sample.source == "sonarmite_ascii":
        parts = raw.split()
        if len(parts) in SONARMITE_FIELD_COUNTS and parts[SONARMITE_DEPTH_FIELD].strip():
            return parts[SONARMITE_DEPTH_FIELD].strip()
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
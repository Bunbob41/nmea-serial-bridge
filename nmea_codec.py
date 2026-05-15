# nmea_codec.py — line assembly, optional checksum validation, strict vs passthrough
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple


class NmeaMode(str, Enum):
    PASSTHROUGH = "passthrough"
    STRICT = "strict"


NMEA_SENTENCE_TYPES: tuple[str, ...] = (
    "GGA",
    "RMC",
    "ZDA",
    "VTG",
    "GSA",
    "GSV",
    "GLL",
    "HDT",
    "HDG",
    "DTM",
    "GBS",
    "GST",
)


@dataclass
class NmeaFilter:
    """When enabled_types is empty, all sentence types are allowed."""

    enabled_types: Set[str] = field(default_factory=set)

    def allows_sentence(self, line: str) -> bool:
        if not self.enabled_types:
            return True
        st = nmea_sentence_type(line)
        if st is None:
            return False
        return st in self.enabled_types


def nmea_sentence_type(line: str) -> Optional[str]:
    s = line.strip()
    if len(s) < 6 or s[0] not in ("$", "!"):
        return None
    if s[0] == "$":
        return s[3:6].upper()
    return s[2:5].upper()


# NMEA 0183 max sentence length 82 chars; allow headroom for buffering mistakes
MAX_NMEA_LINE_LEN = 256
MAX_ASSEMBLER_BUFFER = 64 * 1024


@dataclass
class ProcessResult:
    forward: List[bytes] = field(default_factory=list)
    rejected: List[str] = field(default_factory=list)


def parse_nmea_utc(line: str) -> Optional[str]:
    """Return a short UTC hint from RMC or ZDA, or None."""
    s = line.strip()
    if len(s) < 10 or s[0] != "$":
        return None
    parts = s.split(",")
    if len(parts) < 2:
        return None
    head = parts[0]
    if len(head) >= 6 and "RMC" in head:
        if len(parts) >= 10 and parts[1] and parts[9]:
            return f"{parts[9]} {parts[1]} UTC (RMC)"
        return None
    if "ZDA" in head:
        if len(parts) >= 5 and parts[1] and parts[2] and parts[3] and parts[4]:
            return f"{parts[4]}-{parts[2].zfill(2)}-{parts[3].zfill(2)} {parts[1]} UTC (ZDA)"
        return None
    return None


def nmea_checksum_ok(line: str) -> bool:
    """Validate NMEA/AIS XOR checksum when *HH present."""
    s = line.strip()
    if not s or s[0] not in ("$", "!"):
        return True
    star = s.rfind("*")
    if star < 0:
        return False
    if star + 3 > len(s):
        return False
    try:
        expected = int(s[star + 1 : star + 3], 16)
    except ValueError:
        return False
    body = s[1:star]
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return cs == expected


def _line_to_wire(line: str) -> bytes:
    text = line.strip("\r\n")
    if not text:
        return b""
    return (text + "\r\n").encode("utf-8", errors="replace")


def _find_line_end(buf: bytearray) -> Optional[int]:
    for sep in (b"\r\n", b"\n", b"\r"):
        i = buf.find(sep)
        if i >= 0:
            return i + len(sep)
    return None


def _classify_strict(line: str, nmea_filter: Optional[NmeaFilter] = None) -> Tuple[bool, str]:
    s = line.strip()
    if not s:
        return False, "empty line"
    if s[0] in ("$", "!"):
        if not nmea_checksum_ok(s):
            return False, f"bad checksum: {s[:72]}"
        if nmea_filter is not None and not nmea_filter.allows_sentence(s):
            st = nmea_sentence_type(s) or "?"
            return False, f"sentence type {st} not enabled"
        return True, ""
    return False, f"not NMEA (strict): {s[:72]}"


class NmeaLineAssembler:
    """Accumulate bytes and emit complete lines (handles TCP fragmentation)."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def reset(self) -> None:
        self._buf.clear()

    def feed(
        self, data: bytes, mode: NmeaMode, nmea_filter: Optional[NmeaFilter] = None
    ) -> ProcessResult:
        out = ProcessResult()
        if not data:
            return out
        self._buf.extend(data)
        if len(self._buf) > MAX_ASSEMBLER_BUFFER:
            out.rejected.append(f"assembler overflow ({len(self._buf)} bytes), buffer cleared")
            self._buf.clear()
            return out

        while True:
            end = _find_line_end(self._buf)
            if end is None:
                break
            raw = bytes(self._buf[:end])
            del self._buf[:end]
            try:
                line = raw.decode("utf-8", errors="replace").strip("\r\n")
            except Exception:
                line = raw.decode(errors="replace").strip("\r\n")
            if not line:
                continue
            if len(line) > MAX_NMEA_LINE_LEN:
                out.rejected.append(f"line too long ({len(line)} chars), dropped")
                continue

            if mode == NmeaMode.STRICT:
                ok, reason = _classify_strict(line, nmea_filter)
                if not ok:
                    out.rejected.append(reason)
                    continue

            wire = _line_to_wire(line)
            if wire:
                out.forward.append(wire)

        return out

    @property
    def pending_bytes(self) -> int:
        return len(self._buf)


def feed_nmea_times_from_lines(lines: List[bytes], state: list) -> None:
    for chunk in lines:
        try:
            text = chunk.decode(errors="replace")
        except Exception:
            continue
        for line in text.splitlines():
            u = parse_nmea_utc(line)
            if u:
                state[0] = u

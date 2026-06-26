"""Mux depth samples with latest GNSS fix (GUI-free)."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Optional

from depth_codec import DepthSample

DISPLAY_CAP = 5000
STALE_MS = 3000
RECENT_API_CAP = 50


@dataclass(frozen=True)
class FixSnapshot:
    lat: float
    lon: float
    fix_type: Optional[int]
    hdop: Optional[float]
    source: str
    fix_mono: float


@dataclass(frozen=True)
class Sounding:
    depth_m: float
    lat: Optional[float]
    lon: Optional[float]
    fix_age_ms: int
    stale: bool
    depth_source: str
    wall_time: Optional[float]
    hdop: Optional[float]
    fix_type: Optional[int]

    def to_export_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "depth_m": self.depth_m,
            "fix_stale": self.stale,
            "depth_source": self.depth_source,
            "fix_age_ms": self.fix_age_ms,
        }
        if self.wall_time is not None:
            out["timestamp"] = self.wall_time
        if self.lat is not None and self.lon is not None:
            out["lat"] = self.lat
            out["lon"] = self.lon
        if self.hdop is not None:
            out["hdop"] = self.hdop
        if self.fix_type is not None:
            out["fix_type"] = self.fix_type
        return out

    def to_map_dict(self) -> dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "depth_m": self.depth_m,
            "stale": self.stale,
            "depth_source": self.depth_source,
        }


def mux_depth(
    depth: DepthSample,
    fix: Optional[FixSnapshot],
    *,
    stale_ms: int = STALE_MS,
    wall_time: Optional[float] = None,
) -> Sounding:
    if fix is None:
        return Sounding(
            depth_m=depth.depth_m,
            lat=None,
            lon=None,
            fix_age_ms=0,
            stale=True,
            depth_source=depth.source,
            wall_time=wall_time,
            hdop=None,
            fix_type=None,
        )
    age_ms = max(0, int((depth.received_mono - fix.fix_mono) * 1000))
    stale = age_ms > stale_ms
    return Sounding(
        depth_m=depth.depth_m,
        lat=fix.lat,
        lon=fix.lon,
        fix_age_ms=age_ms,
        stale=stale,
        depth_source=depth.source,
        wall_time=wall_time,
        hdop=fix.hdop,
        fix_type=fix.fix_type,
    )


class SoundingBuffer:
    def __init__(self, *, cap: int = DISPLAY_CAP) -> None:
        self._cap = max(1, int(cap))
        self._items: Deque[Sounding] = deque(maxlen=self._cap)

    def clear(self) -> None:
        self._items.clear()

    def append(self, sounding: Sounding) -> None:
        self._items.append(sounding)

    def __len__(self) -> int:
        return len(self._items)

    def session_soundings(self) -> list[dict[str, Any]]:
        return [s.to_export_dict() for s in self._items]

    def recent_for_map(self, max_points: int = 500) -> list[dict[str, Any]]:
        cap = max(1, int(max_points))
        items = list(self._items)
        if len(items) <= cap:
            return [s.to_map_dict() for s in items if s.lat is not None and s.lon is not None]
        step = max(1, len(items) // cap)
        out = [s.to_map_dict() for i, s in enumerate(items) if i % step == 0 and s.lat is not None]
        last = items[-1]
        if last.lat is not None:
            md = last.to_map_dict()
            if not out or out[-1] != md:
                out.append(md)
        return out[-cap:]

    def recent_for_api(self, max_items: int = RECENT_API_CAP) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for s in list(self._items)[-max(1, int(max_items)) :]:
            if s.lat is None or s.lon is None:
                continue
            out.append(s.to_map_dict())
        return out

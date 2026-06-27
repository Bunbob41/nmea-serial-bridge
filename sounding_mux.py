"""Mux depth samples with GNSS fix track (GUI-free)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Optional

from depth_codec import DepthSample

DISPLAY_CAP = 5000
STALE_MS = 3000
RECENT_API_CAP = 50
PENDING_DEPTH_CAP = 512
_EXTRAP_MAX_SPAN = 1.25


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


def _map_ready(sounding: Sounding) -> bool:
    return sounding.lat is not None and sounding.lon is not None


def _same_coords(a: FixSnapshot, b: FixSnapshot) -> bool:
    return abs(a.lat - b.lat) < 1e-9 and abs(a.lon - b.lon) < 1e-9


def interpolate_position(
    prev: Optional[FixSnapshot],
    cur: Optional[FixSnapshot],
    depth_mono: float,
    *,
    extrap_max_span: float = _EXTRAP_MAX_SPAN,
) -> Optional[tuple[float, float]]:
    """Linear position along prev→cur; slight extrapolation after cur until next fix."""
    if cur is None:
        return None
    if prev is None or cur.fix_mono <= prev.fix_mono:
        return cur.lat, cur.lon
    span = cur.fix_mono - prev.fix_mono
    if span <= 1e-6:
        return cur.lat, cur.lon
    t = (depth_mono - prev.fix_mono) / span
    t = max(0.0, min(extrap_max_span, t))
    lat = prev.lat + (cur.lat - prev.lat) * t
    lon = prev.lon + (cur.lon - prev.lon) * t
    return lat, lon


def _make_sounding(
    depth: DepthSample,
    lat: Optional[float],
    lon: Optional[float],
    ref_fix: Optional[FixSnapshot],
    *,
    stale_ms: int = STALE_MS,
    wall_time: Optional[float] = None,
    force_stale: bool = False,
) -> Sounding:
    if ref_fix is None or lat is None or lon is None:
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
    age_ms = max(0, int((depth.received_mono - ref_fix.fix_mono) * 1000))
    stale = force_stale or age_ms > stale_ms
    return Sounding(
        depth_m=depth.depth_m,
        lat=lat,
        lon=lon,
        fix_age_ms=age_ms,
        stale=stale,
        depth_source=depth.source,
        wall_time=wall_time,
        hdop=ref_fix.hdop,
        fix_type=ref_fix.fix_type,
    )


def mux_depth(
    depth: DepthSample,
    fix: Optional[FixSnapshot],
    *,
    stale_ms: int = STALE_MS,
    wall_time: Optional[float] = None,
) -> Sounding:
    """Legacy single-fix mux (tests / direct calls)."""
    if fix is None:
        return _make_sounding(depth, None, None, None, stale_ms=stale_ms, wall_time=wall_time)
    lat_lon = interpolate_position(fix, fix, depth.received_mono)
    if lat_lon is None:
        return _make_sounding(depth, None, None, None, stale_ms=stale_ms, wall_time=wall_time)
    lat, lon = lat_lon
    return _make_sounding(depth, lat, lon, fix, stale_ms=stale_ms, wall_time=wall_time)


class DepthFixBinder:
    """Bind high-rate depth to the active fix segment or the subsequent GGA/RMC."""

    def __init__(self, *, pending_cap: int = PENDING_DEPTH_CAP) -> None:
        self._pending_cap = max(1, int(pending_cap))
        self.clear()

    def clear(self) -> None:
        self._prev: Optional[FixSnapshot] = None
        self._cur: Optional[FixSnapshot] = None
        self._pending: list[DepthSample] = []

    def on_fix(self, snap: FixSnapshot) -> list[Sounding]:
        """Record a new positional sentence; release depths waiting for this subsequent fix."""
        released: list[Sounding] = []
        if self._cur is not None and self._pending:
            released = self._release_pending(self._cur, snap)
        elif self._cur is None and self._pending:
            for depth in self._pending:
                released.append(
                    _make_sounding(depth, snap.lat, snap.lon, snap, force_stale=False)
                )
            self._pending.clear()

        if self._cur is None:
            self._cur = snap
        elif _same_coords(self._cur, snap):
            self._cur = snap
        else:
            self._prev = self._cur
            self._cur = snap
        return released

    def bind_depth(
        self,
        depth: DepthSample,
        *,
        stale_ms: int = STALE_MS,
        wall_time: Optional[float] = None,
    ) -> list[Sounding]:
        if self._cur is None:
            return [_make_sounding(depth, None, None, None, stale_ms=stale_ms, wall_time=wall_time)]

        if (
            self._prev is not None
            and depth.received_mono <= self._cur.fix_mono
        ):
            lat_lon = interpolate_position(self._prev, self._cur, depth.received_mono)
            if lat_lon is None:
                return [
                    _make_sounding(depth, None, None, None, stale_ms=stale_ms, wall_time=wall_time)
                ]
            lat, lon = lat_lon
            return [
                _make_sounding(
                    depth, lat, lon, self._cur, stale_ms=stale_ms, wall_time=wall_time
                )
            ]

        if depth.received_mono > self._cur.fix_mono:
            if len(self._pending) < self._pending_cap:
                self._pending.append(depth)
                return []
            lat_lon = interpolate_position(self._prev, self._cur, depth.received_mono)
            if lat_lon is None:
                lat, lon = self._cur.lat, self._cur.lon
            else:
                lat, lon = lat_lon
            return [
                _make_sounding(
                    depth,
                    lat,
                    lon,
                    self._cur,
                    stale_ms=stale_ms,
                    wall_time=wall_time,
                    force_stale=True,
                )
            ]

        return [
            _make_sounding(
                depth,
                self._cur.lat,
                self._cur.lon,
                self._cur,
                stale_ms=stale_ms,
                wall_time=wall_time,
            )
        ]

    def flush_pending(
        self,
        *,
        stale_ms: int = STALE_MS,
        wall_time: Optional[float] = None,
    ) -> list[Sounding]:
        if not self._pending:
            return []
        if self._cur is None:
            out = [
                _make_sounding(d, None, None, None, stale_ms=stale_ms, wall_time=wall_time)
                for d in self._pending
            ]
            self._pending.clear()
            return out
        out = [
            _make_sounding(
                d,
                self._cur.lat,
                self._cur.lon,
                self._cur,
                stale_ms=stale_ms,
                wall_time=wall_time,
                force_stale=True,
            )
            for d in self._pending
        ]
        self._pending.clear()
        return out

    def _release_pending(
        self,
        prev_fix: FixSnapshot,
        next_fix: FixSnapshot,
    ) -> list[Sounding]:
        pending = self._pending
        self._pending = []
        n = len(pending)
        if n <= 0:
            return []
        out: list[Sounding] = []
        for i, depth in enumerate(pending, start=1):
            t = i / (n + 1)
            lat = prev_fix.lat + (next_fix.lat - prev_fix.lat) * t
            lon = prev_fix.lon + (next_fix.lon - prev_fix.lon) * t
            out.append(_make_sounding(depth, lat, lon, next_fix, force_stale=False))
        return out


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
            return [s.to_map_dict() for s in items if _map_ready(s)]
        step = max(1, len(items) // cap)
        out = [
            s.to_map_dict()
            for i, s in enumerate(items)
            if i % step == 0 and _map_ready(s)
        ]
        last = items[-1]
        if _map_ready(last):
            md = last.to_map_dict()
            if not out or out[-1] != md:
                out.append(md)
        return out[-cap:]

    def recent_for_api(self, max_items: int = RECENT_API_CAP) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for s in list(self._items)[-max(1, int(max_items)) :]:
            if not _map_ready(s):
                continue
            out.append(s.to_map_dict())
        return out

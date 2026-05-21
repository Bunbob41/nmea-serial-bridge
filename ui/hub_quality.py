"""Traffic quality mapping for Connection Hub cards (no Qt)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrafficQualitySnapshot:
    state: str
    hz_up: float
    hz_down: float
    drops_s2n: int
    drops_n2s: int
    rej_s2n: int
    rej_n2s: int
    nav_stale: bool
    summary: str


def quality_from_bridge_stats(stats: dict) -> TrafficQualitySnapshot:
    running = bool(stats.get("running"))
    if not running:
        return TrafficQualitySnapshot(
            state="idle",
            hz_up=0.0,
            hz_down=0.0,
            drops_s2n=0,
            drops_n2s=0,
            rej_s2n=0,
            rej_n2s=0,
            nav_stale=False,
            summary="Stopped",
        )
    hz_up = float(stats.get("hz_up") or 0.0)
    hz_down = float(stats.get("hz_down") or 0.0)
    drops_s2n = int(stats.get("drops_s2n") or 0)
    drops_n2s = int(stats.get("drops_n2s") or 0)
    rej_s2n = int(stats.get("rej_s2n") or 0)
    rej_n2s = int(stats.get("rej_n2s") or 0)
    nav = stats.get("nav_quality") or {}
    nav_stale = bool(nav.get("stale")) if isinstance(nav, dict) else False
    warn = drops_s2n or drops_n2s or rej_s2n or rej_n2s or nav_stale
    parts = [f"↑{hz_up:.1f} Hz"]
    if drops_s2n or rej_s2n:
        parts.append(f"{drops_s2n} drop / {rej_s2n} rej")
    state = "warn" if warn else ("ok" if hz_up >= 0.3 else "warn")
    return TrafficQualitySnapshot(
        state=state,
        hz_up=hz_up,
        hz_down=hz_down,
        drops_s2n=drops_s2n,
        drops_n2s=drops_n2s,
        rej_s2n=rej_s2n,
        rej_n2s=rej_n2s,
        nav_stale=nav_stale,
        summary=" · ".join(parts),
    )

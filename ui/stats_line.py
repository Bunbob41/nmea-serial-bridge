"""Human-readable live stats for the status bar (no decorative 0/0)."""
from __future__ import annotations

from typing import Any, Optional

from survey_quality import format_gnss_stats_segment

# Transient depth while pumps catch up is normal; match bench_capacity_probe backlog heuristic.
QUEUE_BACKLOG_DEPTH = 12


def queue_backlog(q_ns: int, q_sn: int) -> bool:
    """True when either write queue shows sustained pressure, not pipelining of a few chunks."""
    return q_ns >= QUEUE_BACKLOG_DEPTH or q_sn >= QUEUE_BACKLOG_DEPTH


def _fmt_k(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 10_000:
        return f"{n / 1000:.1f}k"
    if n >= 1000:
        return f"{n / 1000:.2f}k"
    return str(n)


def format_live_stats_line(d: dict) -> str:
    """Build one status-bar sentence from bridge counter snapshot.

    Omits drop/reject/queue segments when there is nothing to report, so the
    bar does not show meaningless ``0/0`` pairs.
    """
    hz_d = float(d.get("hz_down", 0.0))
    hz_i = float(d.get("hz_gui", 0.0))
    hz_u = float(d.get("hz_up", 0.0))
    ld = int(d.get("lines_down", 0))
    lu = int(d.get("lines_up", 0))

    d_ns = int(d.get("drops_n2s", 0))
    d_sn = int(d.get("drops_s2n", 0))
    r_ns = int(d.get("rej_n2s", 0))
    r_sn = int(d.get("rej_s2n", 0))
    q_ns = int(d.get("n2s_q", 0))
    q_sn = int(d.get("s2n_q", 0))

    parts: list[str] = [f"↓{hz_d:.1f} ↑{hz_u:.1f} Hz wire"]
    if hz_i >= 0.05:
        parts.append(f" · inject {hz_i:.1f} Hz")

    alerts: list[str] = []
    if d_ns and d_sn:
        alerts.append(f"drops {d_ns}+{d_sn} (net→COM and COM→net queues full)")
    elif d_ns:
        alerts.append(f"drops {d_ns} (net→COM queue full)")
    elif d_sn:
        alerts.append(f"drops {d_sn} (COM→net queue full)")

    if r_ns and r_sn:
        alerts.append(f"rejects {r_ns}+{r_sn} (both directions)")
    elif r_ns:
        alerts.append(f"rejects {r_ns} (toward COM)")
    elif r_sn:
        alerts.append(f"rejects {r_sn} (from COM)")

    q_hi_ns = q_ns >= QUEUE_BACKLOG_DEPTH
    q_hi_sn = q_sn >= QUEUE_BACKLOG_DEPTH
    if q_hi_ns and q_hi_sn:
        alerts.append(f"queues {q_ns}+{q_sn} chunks waiting (backlog)")
    elif q_hi_ns:
        alerts.append(f"queue {q_ns} chunks net→COM (backlog)")
    elif q_hi_sn:
        alerts.append(f"queue {q_sn} chunks COM→net (backlog)")

    if alerts:
        parts.append(" · " + " · ".join(alerts))
    else:
        parts.append(" · transport OK")

    if ld == 0 and lu == 0:
        parts.append(" · session: no sentences counted yet")
    else:
        com = _fmt_k(ld) if ld else "none"
        net = _fmt_k(lu) if lu else "none"
        parts.append(f" · session: {com} sentences→COM, {net} →net")

    nav_seg = format_gnss_stats_segment(_nav_from_stats(d))
    if nav_seg:
        parts.append(nav_seg)

    return "".join(parts)


def stats_snapshot_from_merged(merged: dict[str, Any]) -> dict[str, float | int]:
    """Normalize bridge stats dict keys for clipboard / export (Copy stats)."""
    return {
        "hz_down": float(merged.get("hz_down", 0.0)),
        "hz_up": float(merged.get("hz_up", 0.0)),
        "hz_gui": float(merged.get("hz_gui", 0.0)),
        "drops_n2s": int(merged.get("drops_n2s", 0)),
        "drops_s2n": int(merged.get("drops_s2n", 0)),
        "rej_n2s": int(merged.get("rej_n2s", 0)),
        "rej_sn": int(merged.get("rej_s2n", 0)),
        "lines_down": int(merged.get("lines_down", 0)),
        "lines_up": int(merged.get("lines_up", 0)),
    }


def _nav_from_stats(d: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not d.get("summary") and d.get("fix_label") is None:
        return None
    return {
        "level": d.get("level"),
        "summary": d.get("summary"),
        "detail": d.get("detail"),
        "fix_label": d.get("fix_label"),
        "num_sats": d.get("num_sats"),
        "hdop": d.get("hdop"),
        "nav_stale": bool(d.get("nav_stale")),
    }

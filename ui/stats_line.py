"""Human-readable live stats for the status bar (no decorative 0/0)."""
from __future__ import annotations

from typing import Any, Optional

from survey_quality import format_gnss_stats_segment

# Transient depth while pumps catch up is normal; match bench_capacity_probe backlog heuristic.
QUEUE_BACKLOG_DEPTH = 12


def queue_backlog(q_ns: int, q_sn: int) -> bool:
    """True when either write queue shows sustained pressure, not pipelining of a few chunks."""
    return q_ns >= QUEUE_BACKLOG_DEPTH or q_sn >= QUEUE_BACKLOG_DEPTH


def transport_alert_active(d: dict) -> bool:
    """True when transport health should be surfaced as a visible warning."""
    d_ns = int(d.get("drops_n2s", 0))
    d_sn = int(d.get("drops_s2n", 0))
    r_ns = int(d.get("rej_n2s", 0))
    r_sn = int(d.get("rej_s2n", 0))
    q_ns = int(d.get("n2s_q", 0))
    q_sn = int(d.get("s2n_q", 0))
    return bool(d_ns or d_sn or r_ns or r_sn or queue_backlog(q_ns, q_sn))


def backpressure_alert_kind(d: dict) -> str:
    """Header chip severity: error when bytes were dropped, else warn."""
    if int(d.get("drops_n2s", 0)) or int(d.get("drops_s2n", 0)):
        return "error"
    return "warn"


def format_backpressure_chip(d: dict) -> tuple[str, str]:
    """Compact Modern header chip text and alertKind (warn | error)."""
    d_ns = int(d.get("drops_n2s", 0))
    d_sn = int(d.get("drops_s2n", 0))
    r_ns = int(d.get("rej_n2s", 0))
    r_sn = int(d.get("rej_s2n", 0))
    q_ns = int(d.get("n2s_q", 0))
    q_sn = int(d.get("s2n_q", 0))

    parts: list[str] = []
    drop_total = d_ns + d_sn
    rej_total = r_ns + r_sn
    if drop_total:
        parts.append(f"{drop_total} drop{'s' if drop_total != 1 else ''}")
    if rej_total:
        parts.append(f"{rej_total} rej")
    q_hi_ns = q_ns >= QUEUE_BACKLOG_DEPTH
    q_hi_sn = q_sn >= QUEUE_BACKLOG_DEPTH
    if q_hi_ns and q_hi_sn:
        parts.append(f"Q {q_ns}+{q_sn}")
    elif q_hi_ns:
        parts.append(f"Q net {q_ns}")
    elif q_hi_sn:
        parts.append(f"Q COM {q_sn}")

    prefix = "⚠ " if drop_total else "▲ "
    label = prefix + (" · ".join(parts) if parts else "Backpressure")
    return label, backpressure_alert_kind(d)


def format_backpressure_tooltip(d: dict) -> str:
    """Hover/click hint for the backpressure header chip."""
    return format_backpressure_detail(d)


def format_backpressure_detail(d: dict) -> str:
    """Plain-language breakdown of drops, rejects, and queue backlog."""
    d_ns = int(d.get("drops_n2s", 0))
    d_sn = int(d.get("drops_s2n", 0))
    r_ns = int(d.get("rej_n2s", 0))
    r_sn = int(d.get("rej_s2n", 0))
    q_ns = int(d.get("n2s_q", 0))
    q_sn = int(d.get("s2n_q", 0))
    lines: list[str] = []

    if d_ns or d_sn:
        if d_ns and d_sn:
            lines.append(
                f"Dropped {d_ns} net→COM and {d_sn} COM→net chunks (queue full — data lost)."
            )
        elif d_ns:
            lines.append(f"Dropped {d_ns} net→COM chunk(s) — UDP/TCP input queue was full.")
        else:
            lines.append(f"Dropped {d_sn} COM→net chunk(s) — serial read queue was full.")

    if r_ns or r_sn:
        if r_ns and r_sn:
            lines.append(
                f"Rejected {r_ns} toward COM and {r_sn} from COM "
                f"(strict NMEA filter, bad checksum, or incomplete sentence)."
            )
        elif r_ns:
            lines.append(
                f"Rejected {r_ns} toward COM — strict NMEA filter, bad checksum, "
                f"or incomplete sentence on the network→serial path."
            )
        else:
            lines.append(
                f"Rejected {r_sn} from COM toward the network "
                f"(line did not pass outbound filtering)."
            )

    q_hi_ns = q_ns >= QUEUE_BACKLOG_DEPTH
    q_hi_sn = q_sn >= QUEUE_BACKLOG_DEPTH
    if q_hi_ns or q_hi_sn:
        if q_hi_ns and q_hi_sn:
            lines.append(f"Queue backlog: {q_ns} net→COM + {q_sn} COM→net chunks waiting.")
        elif q_hi_ns:
            lines.append(f"Queue backlog: {q_ns} net→COM chunks waiting (consumer slow).")
        else:
            lines.append(f"Queue backlog: {q_sn} COM→net chunks waiting (consumer slow).")

    if not lines:
        return "Transport healthy — no drops, rejects, or queue backlog."
    lines.append("")
    lines.append("Click Activity → filter Reject for live reject lines.")
    return "\n".join(lines)


def format_running_hz_chip(d: dict) -> tuple[str, str]:
    """Compact GNSS fix-rate pill for Modern header (GGA/RMC updates per second)."""
    fix_d = float(d.get("hz_fix_down", 0.0))
    fix_u = float(d.get("hz_fix_up", 0.0))
    sent_d = float(d.get("hz_down", 0.0))
    sent_u = float(d.get("hz_up", 0.0))
    hz_i = float(d.get("hz_gui", 0.0))
    if fix_d > 0.0 or fix_u > 0.0:
        text = f"GNSS {fix_d:.1f} Hz"
        if sent_d >= 0.5:
            text += f" · {sent_d:.0f} msg/s"
        if fix_u >= 0.05:
            text += f" · COM {fix_u:.1f} Hz"
    else:
        text = f"net {sent_d:.1f}/s"
        if sent_u >= 0.05:
            text += f" · COM {sent_u:.1f}/s"
    if hz_i >= 0.05:
        text += f" · inj {hz_i:.1f}"
    tip = (
        "GGA position fix rate (rolling 1 s). "
        f"All sentences received: {sent_d:.1f} net→COM, {sent_u:.1f} COM→net. "
        + format_live_stats_line(d)
    )
    return text, tip


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
    fix_d = float(d.get("hz_fix_down", 0.0))
    fix_u = float(d.get("hz_fix_up", 0.0))
    ld = int(d.get("lines_down", 0))
    lu = int(d.get("lines_up", 0))

    d_ns = int(d.get("drops_n2s", 0))
    d_sn = int(d.get("drops_s2n", 0))
    r_ns = int(d.get("rej_n2s", 0))
    r_sn = int(d.get("rej_s2n", 0))
    q_ns = int(d.get("n2s_q", 0))
    q_sn = int(d.get("s2n_q", 0))

    if fix_d > 0.0 or fix_u > 0.0:
        parts: list[str] = [f"GNSS {fix_d:.1f} Hz"]
        if fix_u >= 0.05:
            parts.append(f" · COM fixes {fix_u:.1f} Hz")
        if hz_d >= 0.5 or hz_u >= 0.05:
            parts.append(f" · net {hz_d:.1f}/s · COM {hz_u:.1f}/s")
    else:
        parts = [f"net {hz_d:.1f}/s"]
        if hz_u >= 0.05:
            parts.append(f" · COM {hz_u:.1f}/s")
    if hz_i >= 0.05:
        parts.append(f" · inject {hz_i:.1f} msg/s")

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
        alerts.append(f"queue net→COM {q_ns} chunks (backlog)")
    elif q_hi_sn:
        alerts.append(f"queue COM→net {q_sn} chunks (backlog)")

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

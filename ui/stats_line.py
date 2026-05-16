"""Human-readable live stats for the status bar (no decorative 0/0)."""
from __future__ import annotations


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

    parts: list[str] = [f"↓{hz_d:.1f} ↑{hz_u:.1f} Hz"]
    if hz_i >= 0.05:
        parts.append(f" · Send→COM {hz_i:.1f}/s")

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

    if q_ns and q_sn:
        alerts.append(f"queues {q_ns}+{q_sn} chunks waiting")
    elif q_ns:
        alerts.append(f"queue {q_ns} chunks net→COM (not written yet)")
    elif q_sn:
        alerts.append(f"queue {q_sn} chunks COM→net (not sent yet)")

    if alerts:
        parts.append(" · " + " · ".join(alerts))
    else:
        parts.append(" · transport OK")

    if ld == 0 and lu == 0:
        parts.append(" · session: no sentences counted yet")
    else:
        com = _fmt_k(ld) if ld else "none"
        net = _fmt_k(lu) if lu else "none"
        parts.append(f" · session: {com} →COM, {net} →net")

    return "".join(parts)

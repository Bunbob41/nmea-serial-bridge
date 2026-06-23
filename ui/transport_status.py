"""Transport truth — format COM/UDP/session timing for UI and web."""
from __future__ import annotations

from typing import Any, Literal, Optional

TransportKind = Literal["ok", "warn", "idle", "error"]

UDP_PEER_STALE_S = 60.0
COM_DATA_STALE_S = 60.0


def format_age_s(age: Optional[float], *, none_label: str = "never") -> str:
    if age is None:
        return none_label
    age = max(0.0, float(age))
    if age < 1.0:
        return "<1s"
    if age < 60.0:
        return f"{int(age)}s"
    mins = int(age // 60)
    secs = int(age % 60)
    if mins < 60:
        return f"{mins}m" if secs == 0 else f"{mins}m {secs}s"
    hours = mins // 60
    mins = mins % 60
    return f"{hours}h {mins}m"


def format_duration_s(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    if mins >= 60:
        hours = mins // 60
        mins = mins % 60
        return f"{hours}h {mins}m {secs}s"
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def _com_kind(stats: dict[str, Any]) -> TransportKind:
    state = str(stats.get("serial_link_state") or "closed")
    if state == "reconnecting":
        return "warn"
    if state != "open":
        return "idle" if not stats.get("running") else "warn"
    age = stats.get("last_com_to_net_age_s")
    if age is None:
        return "warn" if stats.get("running") else "idle"
    if float(age) > COM_DATA_STALE_S:
        return "warn"
    return "ok"


def _udp_kind(stats: dict[str, Any]) -> TransportKind:
    mode = str(stats.get("net_mode") or "")
    if mode == "udp_remote":
        return "ok" if stats.get("running") else "idle"
    if mode not in ("udp_listen", ""):
        return "idle"
    peers = stats.get("udp_peer_details") or []
    if not peers:
        return "warn" if stats.get("running") else "idle"
    if any(not p.get("stale") for p in peers):
        return "ok"
    return "warn"


def activity_transport_labels(
    stats: dict[str, Any],
) -> tuple[str, str, TransportKind, str, str, TransportKind, str, str]:
    """Serial pill, serial tip, serial kind, UDP pill, UDP tip, UDP kind, session, session tip."""
    running = bool(stats.get("running"))
    serial_state = str(stats.get("serial_link_state") or "closed")
    com_age = stats.get("last_com_to_net_age_s")
    com_kind = _com_kind(stats)

    if not running:
        serial_text = "Serial — stopped"
        serial_tip = "COM link idle while bridge is stopped."
    elif serial_state == "reconnecting":
        serial_text = "Serial ● reconnecting…"
        serial_tip = "COM port dropped — auto-reconnect in progress."
    elif serial_state != "open":
        serial_text = "Serial ● closed"
        serial_tip = "Serial port is not open."
    elif com_age is None:
        serial_text = "Serial ● no COM data yet"
        serial_tip = "No bytes from COM toward the network this session."
    else:
        label = format_age_s(com_age)
        mark = " ⚠" if com_kind == "warn" else ""
        serial_text = f"Serial ● COM {label} ago{mark}"
        serial_tip = (
            "Time since the last COM→network byte. "
            "If this grows while Running, fix Bluetooth/COM before UDP."
        )

    mode = str(stats.get("net_mode") or "")
    udp_kind = _udp_kind(stats)
    peers = list(stats.get("udp_peer_details") or [])
    fanout = bool(stats.get("udp_fanout", True))

    if mode == "udp_remote":
        host = str(stats.get("udp_remote_host") or "")
        port = stats.get("udp_remote_port")
        target = f"{host}:{port}" if host and port else "remote"
        udp_text = f"UDP ● → {target}"
        udp_tip = "UDP remote mode pushes COM→network to a fixed target (no inbound peer register)."
    elif mode == "tcp_server":
        n = int(stats.get("tcp_sink_clients") or 0)
        udp_text = f"TCP ● {n} client(s)"
        udp_tip = "TCP server mode — clients connect to receive COM→network bytes."
    elif not running:
        udp_text = "UDP — stopped"
        udp_tip = "Network transport idle while bridge is stopped."
    elif not peers:
        udp_text = "UDP ● no peers yet"
        udp_tip = (
            "UDP listen mode: send one datagram from your tablet/app to register as a peer. "
            "After sleep or Wi‑Fi change, send again."
        )
    elif len(peers) == 1 or not fanout:
        p = peers[0]
        addr = str(p.get("addr") or "")
        age = format_age_s(p.get("last_in_s"))
        mark = " ⚠" if p.get("stale") else ""
        udp_text = f"UDP ● {addr} · in {age}{mark}"
        udp_tip = _peer_popover_text(peers, fanout=fanout)
    else:
        fresh = sum(1 for p in peers if not p.get("stale"))
        newest = min(
            (float(p["last_in_s"]) for p in peers if p.get("last_in_s") is not None),
            default=None,
        )
        age = format_age_s(newest)
        mark = "" if fresh else " ⚠"
        udp_text = f"UDP ● {len(peers)} peers · newest {age}{mark}"
        udp_tip = _peer_popover_text(peers, fanout=fanout)

    session_s = float(stats.get("session_running_s") or 0.0)
    active_s = float(stats.get("com_active_total_s") or 0.0)
    session_text = f"Session {format_duration_s(session_s)}"
    session_tip = (
        f"Bridge Running for {format_duration_s(session_s)}.\n"
        f"COM data active ~{format_duration_s(active_s)} "
        "(time with serial bytes toward the network).\n"
        "Running time ≠ link quality."
    )
    return serial_text, serial_tip, com_kind, udp_text, udp_tip, udp_kind, session_text, session_tip


def _peer_popover_text(peers: list[dict[str, Any]], *, fanout: bool) -> str:
    lines = [
        "UDP peer last seen = last inbound datagram from that address.",
        "Does not guarantee the tablet is still receiving sonar.",
    ]
    if fanout:
        lines.append("Fan-out: all listed peers receive COM→network copies.")
    for p in peers:
        addr = str(p.get("addr") or "?")
        age = format_age_s(p.get("last_in_s"))
        stale = "stale" if p.get("stale") else "live"
        primary = " · last sender" if p.get("is_last_sender") else ""
        lines.append(f"  {addr}  in {age}  ({stale}){primary}")
    return "\n".join(lines)


def connection_health_transport_suffix(stats: dict[str, Any]) -> tuple[str, str]:
    """Extra chip segment + tooltip lines when bridge is running."""
    if not stats.get("running"):
        return "", ""
    com_age = stats.get("last_com_to_net_age_s")
    peers = list(stats.get("udp_peer_details") or [])
    parts: list[str] = []
    tips: list[str] = []

    if com_age is None:
        parts.append("COM idle")
        tips.append("COM: no data toward network yet")
    else:
        label = format_age_s(com_age)
        parts.append(f"COM {label}")
        tips.append(f"COM data age: {label}")
        if float(com_age) > COM_DATA_STALE_S:
            parts[-1] += " ⚠"

    mode = str(stats.get("net_mode") or "")
    if mode == "udp_listen":
        if not peers:
            parts.append("UDP none")
            tips.append("UDP: no peer registered — tablet must send inbound")
        else:
            newest = min(
                (float(p["last_in_s"]) for p in peers if p.get("last_in_s") is not None),
                default=None,
            )
            parts.append(f"UDP {format_age_s(newest)}")
            tips.append(f"UDP peer newest inbound: {format_age_s(newest)}")
            if all(p.get("stale") for p in peers):
                parts[-1] += " ⚠"
    elif mode == "udp_remote":
        host = stats.get("udp_remote_host")
        port = stats.get("udp_remote_port")
        parts.append(f"UDP→{host}:{port}")
        tips.append("UDP remote push target")

    if not parts:
        return "", ""
    return " · " + " · ".join(parts), "\n".join(tips)


def format_transport_stop_summary(stats: dict[str, Any]) -> str:
    """Multi-line log block after Stop."""
    running = format_duration_s(float(stats.get("session_running_s") or 0.0))
    active = format_duration_s(float(stats.get("com_active_total_s") or 0.0))
    com_age = stats.get("last_com_to_net_age_s")
    com_tail = format_age_s(com_age, none_label="never") if com_age is not None else "never"
    peers = list(stats.get("udp_peer_details") or [])
    lines = [
        "[Transport] Session summary",
        f"  Running: {running}",
        f"  COM data active: {active}",
        f"  Last COM→net byte: {com_tail} before Stop",
        f"  Lines COM→net: {int(stats.get('lines_up') or 0)}",
    ]
    if peers:
        lines.append(f"  UDP peers registered: {len(peers)}")
        for p in peers[:5]:
            addr = str(p.get("addr") or "?")
            age = format_age_s(p.get("last_in_s"))
            lines.append(f"    {addr}  last inbound {age}")
    else:
        mode = str(stats.get("net_mode") or "")
        if mode == "udp_listen":
            lines.append("  UDP peers: none registered this session")
        elif mode == "udp_remote":
            lines.append(
                f"  UDP remote → {stats.get('udp_remote_host')}:{stats.get('udp_remote_port')}"
            )
    return "\n".join(lines)


def web_transport_summary(stats: dict[str, Any]) -> dict[str, Any]:
    """Compact fields for web dashboard / API."""
    peers = list(stats.get("udp_peer_details") or [])
    newest_udp = None
    if peers:
        newest_udp = min(
            (float(p["last_in_s"]) for p in peers if p.get("last_in_s") is not None),
            default=None,
        )
    return {
        "session_running_s": float(stats.get("session_running_s") or 0.0),
        "com_active_total_s": float(stats.get("com_active_total_s") or 0.0),
        "last_com_to_net_age_s": stats.get("last_com_to_net_age_s"),
        "serial_link_state": str(stats.get("serial_link_state") or "closed"),
        "udp_peer_count": len(peers),
        "udp_peer_newest_in_s": newest_udp,
        "udp_peer_stale": bool(peers) and all(p.get("stale") for p in peers),
        "udp_peer_details": peers,
        "net_mode": str(stats.get("net_mode") or ""),
    }

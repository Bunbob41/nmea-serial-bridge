"""Session stats snapshot — clipboard text and CSV export for HUD counters."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

from ui.stats_line import stats_snapshot_from_merged


def gather_session_stats_snapshot(host: Any) -> dict[str, Any]:
    """Collect bridge + UI counters from a BridgeLogicMixin host window."""
    mode = "udp_listen"
    if host.chk_advanced_net.isChecked():
        if host.rb_udp_remote.isChecked():
            mode = "udp_remote"
        elif host.rb_tcp_server.isChecked():
            mode = "tcp_server"
        elif host.rb_tcp_client.isChecked():
            mode = "tcp_client"
    from ui.connection_fields import read_baud_widget
    from bench_config import last_preset_name

    com = host.com_cb.currentText().strip() or "?"
    baud = read_baud_widget(host.baud_edit) or "?"
    udp_host = host.udp_host.text().strip() or "0.0.0.0"
    udp_port = host.udp_port.text().strip() or "10110"
    if mode == "udp_remote":
        net_detail = (
            f"{host.remote_host.text().strip() or '?'}:"
            f"{host.remote_port.text().strip() or '?'}"
        )
    elif mode == "tcp_server":
        net_detail = (
            f"{host.tcp_srv_host.text().strip() or '0.0.0.0'}:"
            f"{host.tcp_srv_port.text().strip() or '4001'}"
        )
    elif mode == "tcp_client":
        net_detail = (
            f"{host.tcp_cli_host.text().strip() or '127.0.0.1'}:"
            f"{host.tcp_cli_port.text().strip() or '4001'}"
        )
    else:
        net_detail = f"{udp_host}:{udp_port}"

    running = host.bridge is not None
    merged = host._merge_bridge_stats({}) if running else {}
    snap = stats_snapshot_from_merged(merged)
    nav = merged if running else {}

    status_gnss_lbl = getattr(host, "status_gnss", None)
    stats_lbl = getattr(host, "lbl_stats", None)
    preset = (getattr(host, "_active_preset_name", "") or "").strip() or last_preset_name()
    state = "running" if running else ("starting" if getattr(host, "_starting", False) else "stopped")

    return {
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state": state,
        "preset": preset,
        "com": com,
        "baud": baud,
        "network_mode": mode,
        "network_target": net_detail,
        "nmea_mode": host._nmea_mode_label(),
        "status_serial": (host.status_serial.text() or "").strip(),
        "status_network": (host.status_network.text() or "").strip(),
        "status_nmea": (host.status_nmea.text() or "").strip(),
        "status_gnss": (status_gnss_lbl.text() if status_gnss_lbl is not None else "").strip(),
        "stats_line": (stats_lbl.text() if stats_lbl is not None else "").strip(),
        "hz_down": float(snap["hz_down"]),
        "hz_up": float(snap["hz_up"]),
        "hz_gui": float(snap["hz_gui"]),
        "drops_n2s": int(snap["drops_n2s"]),
        "drops_s2n": int(snap["drops_s2n"]),
        "rej_n2s": int(snap["rej_n2s"]),
        "rej_s2n": int(snap["rej_sn"]),
        "lines_down": int(snap["lines_down"]),
        "lines_up": int(snap["lines_up"]),
        "n2s_q": int(merged.get("n2s_q", 0)),
        "s2n_q": int(merged.get("s2n_q", 0)),
        "gnss_summary": str(nav.get("summary") or "—"),
        "gnss_fix": str(nav.get("fix_label") or "—"),
        "gnss_sats": nav.get("num_sats"),
        "gnss_hdop": nav.get("hdop"),
    }


def format_stats_clipboard_text(snapshot: dict[str, Any]) -> str:
    """Plain-text block (legacy Copy stats format)."""
    return (
        "Serial Link stats snapshot\n"
        f"exported_at: {snapshot.get('exported_at', '')}\n"
        f"state: {snapshot.get('state', '')}\n"
        f"preset: {snapshot.get('preset', '')}\n"
        f"serial: {snapshot.get('com', '?')} @ {snapshot.get('baud', '?')}\n"
        f"network_mode: {snapshot.get('network_mode', '')}\n"
        f"network_target: {snapshot.get('network_target', '')}\n"
        f"nmea_mode: {snapshot.get('nmea_mode', '')}\n"
        f"status_serial: {snapshot.get('status_serial', '')}\n"
        f"status_network: {snapshot.get('status_network', '')}\n"
        f"status_nmea: {snapshot.get('status_nmea', '')}\n"
        f"status_gnss: {snapshot.get('status_gnss', '')}\n"
        f"wire_hz_down: {float(snapshot.get('hz_down', 0.0)):.2f}\n"
        f"wire_hz_up: {float(snapshot.get('hz_up', 0.0)):.2f}\n"
        f"inject_hz: {float(snapshot.get('hz_gui', 0.0)):.2f}\n"
        f"drops_down: {int(snapshot.get('drops_n2s', 0))}\n"
        f"drops_up: {int(snapshot.get('drops_s2n', 0))}\n"
        f"rejects_down: {int(snapshot.get('rej_n2s', 0))}\n"
        f"rejects_up: {int(snapshot.get('rej_s2n', 0))}\n"
        f"queue_n2s: {int(snapshot.get('n2s_q', 0))}\n"
        f"queue_s2n: {int(snapshot.get('s2n_q', 0))}\n"
        f"session_down: {int(snapshot.get('lines_down', 0))}\n"
        f"session_up: {int(snapshot.get('lines_up', 0))}\n"
        f"gnss_summary: {snapshot.get('gnss_summary', '—')}\n"
        f"stats_line: {snapshot.get('stats_line', '')}"
    ).strip()


def stats_csv_rows(snapshot: dict[str, Any]) -> list[tuple[str, str]]:
    """Metric/value rows for CSV export."""
    rows: list[tuple[str, str]] = [("metric", "value")]
    for key in (
        "exported_at",
        "state",
        "preset",
        "com",
        "baud",
        "network_mode",
        "network_target",
        "nmea_mode",
        "status_serial",
        "status_network",
        "status_nmea",
        "status_gnss",
        "hz_down",
        "hz_up",
        "hz_gui",
        "drops_n2s",
        "drops_s2n",
        "rej_n2s",
        "rej_s2n",
        "n2s_q",
        "s2n_q",
        "lines_down",
        "lines_up",
        "gnss_summary",
        "gnss_fix",
        "stats_line",
    ):
        val = snapshot.get(key, "")
        if isinstance(val, float):
            rows.append((key, f"{val:.2f}"))
        else:
            rows.append((key, str(val)))
    sats = snapshot.get("gnss_sats")
    if sats is not None:
        rows.append(("gnss_sats", str(sats)))
    hdop = snapshot.get("gnss_hdop")
    if hdop is not None:
        rows.append(("gnss_hdop", str(hdop)))
    return rows


def format_stats_csv(snapshot: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in stats_csv_rows(snapshot):
        writer.writerow(row)
    return buf.getvalue()


def default_stats_csv_name(snapshot: dict[str, Any]) -> str:
    stamp = str(snapshot.get("exported_at", "")).replace(":", "").replace("-", "")[:15]
    state = str(snapshot.get("state", "session"))
    com = str(snapshot.get("com", "COM")).replace(":", "")
    return f"serial_link_stats_{state}_{com}_{stamp or 'export'}.csv"

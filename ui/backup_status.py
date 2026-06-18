"""Compact status-bar copy for the local black-box backup chip."""
from __future__ import annotations


def _human_bytes(n: int) -> str:
    n = max(0, int(n))
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


def format_backup_status(
    *,
    enabled: bool,
    running: bool,
    active: bool,
    error: str,
    path: str,
    nbytes: int,
    dropped: int,
    queue_depth: int = 0,
    queue_max: int = 0,
) -> tuple[str, str]:
    """Return (status_bar_text, tooltip) for lbl_backup_status."""
    if not enabled:
        return ("Backup: off", "Local black-box backup disabled in Diagnostics.")
    err = (error or "").strip()
    if err:
        return ("Backup: error", err)
    if active:
        human = _human_bytes(nbytes)
        bar = f"Backup: {human}"
        if dropped > 0:
            bar = f"Backup: {human} ⚠"
        tip = f"Writing raw COM data to {path}\n{human} ({nbytes:,} bytes) on disk"
        if dropped > 0:
            tip += f"\n{dropped:,} serial chunks dropped (backup queue saturated)"
        if queue_max > 0:
            tip += f"\nQueue depth: {queue_depth}/{queue_max}"
        return (bar, tip)
    if running:
        if enabled:
            return (
                "Backup: failed",
                "Backup was enabled but no writer opened for this session (disk/path error). "
                "Check the live log and logs/ permissions.",
            )
        return ("Backup: starting…", "Opening local .raw backup file for this session.")
    return (
        "Backup: ready",
        "Enabled — a new logs/backup_YYYYMMDD_HHMM.raw file opens on the next Start.",
    )


def format_black_box_page_status(
    *,
    enabled: bool,
    running: bool,
    active: bool,
    error: str,
    path: str,
    nbytes: int,
    dropped: int,
) -> tuple[str, str]:
    """Return (line, tooltip) for Tools → Black box live status."""
    if not enabled:
        return (
            "Not enabled",
            "Turn on black-box backup to capture raw COM data on the next bridge Start.",
        )
    err = (error or "").strip()
    if err:
        return ("Recording error", err)
    if active:
        human = _human_bytes(nbytes)
        line = f"Recording to {path}" if path else "Recording raw COM data"
        if dropped > 0:
            line = f"{line} ({human}, {dropped:,} drops)"
        else:
            line = f"{line} ({human})"
        tip = f"Writing every COM read to {path or 'logs/backup_*.raw'}"
        if dropped > 0:
            tip += f"\n{dropped:,} chunks dropped (backup queue saturated)"
        return (line, tip)
    if running:
        return (
            "Backup failed to open",
            "Black box was enabled but no .raw writer opened — check logs/ permissions.",
        )
    return (
        "Ready — new .raw file on Start",
        "Enabled. A new logs/backup_YYYYMMDD_HHMM.raw file opens when you Start.",
    )


def format_file_log_page_status(
    *,
    enabled: bool,
    running: bool,
    active: bool,
    path: str,
) -> tuple[str, str]:
    """Return (line, tooltip) for Tools → File log live status."""
    dest = (path or "").strip() or "(set path below)"
    if not enabled:
        return (
            "Not enabled",
            "Turn on file log to append bridged NMEA lines to disk on the next Start.",
        )
    if active and running:
        return (
            f"Recording to {dest}",
            f"Appending PC time | GPS UTC | direction | NMEA to this file while running.",
        )
    if running and enabled and not active:
        return (
            "Logging failed to open",
            f"Could not open {dest}. Check the folder exists and is writable.",
        )
    return (
        f"Ready — logs to {dest} on Start",
        "Enabled. Rotating file log begins when you Start the bridge.",
    )


def format_preset_stored_summary(data: dict) -> str:
    """One-line summary of a preset file (COM, NMEA, network)."""
    com = str(data.get("com") or "COM?").strip()
    baud = str(data.get("baud") or "?").strip()
    from ui.nmea_display import nmea_mode_display_label

    nmea = nmea_mode_display_label(str(data.get("nmea_mode") or "passthrough"))
    udp_host = str(data.get("udp_host") or "0.0.0.0").strip()
    udp_port = str(data.get("udp_port") or "?").strip()
    parts = [f"{com} @ {baud}", nmea, f"UDP listen {udp_host}:{udp_port}"]
    if not bool(data.get("udp_fanout", True)):
        parts.append("fan-out off")
    pc_ip = str(data.get("pc_ip") or "").strip()
    if pc_ip:
        parts.append(f"survey PC {pc_ip}")
    ins_ip = str(data.get("ins_ip") or "").strip()
    if ins_ip:
        parts.append(f"INS {ins_ip}")
    return " · ".join(parts)


def format_presets_page_status(parent: QtWidgets.QWidget) -> tuple[str, str, str]:
    """Return (line, tooltip, summaryKind) for Tools → Presets live summary."""
    active = (getattr(parent, "_active_preset_name", None) or "").strip()
    sel_fn = getattr(parent, "_selected_preset_name", None)
    selected = (sel_fn() or "").strip() if callable(sel_fn) else ""

    if active and selected == active:
        try:
            from bench_config import load_preset

            data = load_preset(active)
            session = format_preset_stored_summary(data)
        except KeyError:
            session = _format_presets_session_ui(parent)
        return (
            f"Loaded: «{active}» · {session}",
            "This preset is applied to Control. Save updates the selected preset.",
            "ok",
        )

    if selected:
        data: dict = {}
        try:
            from bench_config import load_preset

            data = load_preset(selected)
            summary = format_preset_stored_summary(data)
        except KeyError:
            summary = "(preset not found)"
        if active:
            headline = f"Preview «{selected}» (loaded: «{active}»)"
        else:
            headline = f"Preview «{selected}»"
        tip = (
            "Shows what this preset file stores. Load (or double-click) applies it to Control."
        )
        notes = str(data.get("notes") or "").strip()
        if notes:
            tip = f"{tip}\n\nNotes: {notes}"
        return (f"{headline}: {summary}", tip, "warn")

    if active:
        try:
            from bench_config import load_preset

            data = load_preset(active)
            session = format_preset_stored_summary(data)
        except KeyError:
            session = _format_presets_session_ui(parent)
        return (
            f"Loaded: «{active}» · {session}",
            "Load applies COM, network, and NMEA from the preset. Save updates the selected preset.",
            "ok",
        )

    session = _format_presets_session_ui(parent)
    return (
        f"Session UI: {session} · no preset loaded",
        "Save or Save as… to store the current Control + NMEA setup under a name.",
        "idle",
    )


def _format_presets_session_ui(parent: QtWidgets.QWidget) -> str:
    com_cb = getattr(parent, "com_cb", None)
    com = com_cb.currentText().strip() if com_cb is not None else ""
    com = com or "COM?"
    baud = "?"
    try:
        from ui.connection_fields import read_baud_widget

        baud_edit = getattr(parent, "baud_edit", None)
        if baud_edit is not None:
            baud = read_baud_widget(baud_edit)
    except Exception:
        pass
    nmea_fn = getattr(parent, "_nmea_mode_label", None)
    nmea_raw = nmea_fn() if callable(nmea_fn) else "passthrough"
    from ui.nmea_display import nmea_mode_display_label

    nmea = nmea_mode_display_label(nmea_raw)
    net = "UDP listen"
    adv = getattr(parent, "chk_advanced_net", None)
    if adv is not None and adv.isChecked():
        if getattr(parent, "rb_tcp_server", None) and parent.rb_tcp_server.isChecked():
            net = "TCP server"
        elif getattr(parent, "rb_tcp_client", None) and parent.rb_tcp_client.isChecked():
            net = "TCP client"
        elif getattr(parent, "rb_udp_remote", None) and parent.rb_udp_remote.isChecked():
            net = "UDP remote"
    return f"{com} @ {baud} · {nmea} · {net}"


def format_activity_page_status(parent: QtWidgets.QWidget) -> tuple[str, str, str]:
    """Return (line, tooltip, summaryKind) for Tools → Activity live summary."""
    panel = getattr(parent, "bridge_terminal", None)
    running = bool(getattr(parent, "_is_bridge_running", lambda: False)())
    if panel is None:
        return (
            "Activity panel not ready",
            "Open the Activity main tab to watch live bridge traffic.",
            "idle",
        )
    view = getattr(panel, "_view", None)
    blocks = 0
    if view is not None:
        try:
            blocks = max(0, view.document().blockCount() - 1)
        except Exception:
            blocks = 0
    if running:
        if blocks <= 0:
            return (
                "Running — waiting for traffic on the wire",
                "NET→COM and COM→NET lines appear on the Activity tab and here.",
                "ready",
            )
        return (
            f"Running · {blocks} line(s) in Activity panel",
            "Clear removes on-screen lines only — file log and black box are unchanged.",
            "recording",
        )
    if blocks <= 0:
        return (
            "Stopped · Activity panel empty",
            "Start the bridge to see live traffic. Clear resets the on-screen view only.",
            "idle",
        )
    return (
        f"Stopped · {blocks} line(s) retained in Activity panel",
        "Clear removes on-screen lines only — does not delete disk logs.",
        "ready",
    )

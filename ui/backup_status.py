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

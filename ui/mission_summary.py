"""Post-stop mission summary for local black-box backup sessions."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.backup_status import _human_bytes


def verify_backup_on_disk(summary: dict[str, object]) -> tuple[int, bool, str]:
    """Return (bytes_on_disk, needs_warning, warning_detail)."""
    reported = int(summary.get("bytes") or 0)
    dropped = int(summary.get("dropped") or 0)
    err = str(summary.get("error") or "").strip()
    path_s = str(summary.get("path") or "").strip()
    if err:
        return reported, True, err
    if reported <= 0:
        return 0, True, "Backup writer recorded 0 bytes for this session."
    if not path_s:
        return reported, True, "No backup file path was recorded."
    path = Path(path_s)
    if not path.is_file():
        return reported, True, f"Backup file not found on disk: {path_s}"
    try:
        on_disk = path.stat().st_size
    except OSError as exc:
        return reported, True, f"Could not read backup file size: {exc}"
    if on_disk <= 0:
        return 0, True, "Backup file exists but is empty (0 bytes on disk)."
    return on_disk, False, ""


def _elide_path_middle(path: str, *, max_chars: int = 52) -> str:
    """Keep folder head and filename tail for dense summary lines."""
    text = str(path or "").strip()
    if len(text) <= max_chars:
        return text
    keep = max(8, (max_chars - 3) // 2)
    return f"{text[:keep]}…{text[-keep:]}"


def format_mission_summary_line(summary: dict[str, object]) -> str:
    """Single-line integrity report for the dialog."""
    nbytes = int(summary.get("bytes") or 0)
    dropped = int(summary.get("dropped") or 0)
    path = str(summary.get("path") or "").strip() or "(unknown)"
    path = _elide_path_middle(path)
    return (
        f"Mission Data Safeguarded: {_human_bytes(nbytes)} | "
        f"{dropped:,} Dropped | Path: {path}"
    )


def present_mission_summary(
    parent: QtWidgets.QWidget,
    summary: dict[str, object],
) -> None:
    """Non-modal post-stop dialog — does not block bridge teardown."""
    _on_disk, warn, detail = verify_backup_on_disk(summary)
    line = format_mission_summary_line(summary)

    box = QtWidgets.QMessageBox(parent)
    box.setModal(False)
    box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
    if warn:
        box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        box.setWindowTitle("Warning: No data written")
        body = f"{line}\n\n{detail}"
        if int(summary.get("dropped") or 0) > 0:
            body += (
                "\n\nSome serial chunks were dropped before reaching the backup file. "
                "Check disk space and storage speed."
            )
        box.setText(body)
    else:
        box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        box.setWindowTitle("Mission Summary")
        dropped = int(summary.get("dropped") or 0)
        extra = ""
        if dropped > 0:
            extra = (
                f"\n\nNote: {dropped:,} serial chunks were dropped from the backup queue "
                "during this run (network bridge was unaffected)."
            )
        box.setText(f"{line}{extra}")
    box.setWindowModality(QtCore.Qt.WindowModality.NonModal)
    box.show()
    box.raise_()
    box.activateWindow()

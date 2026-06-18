"""Shared Modern tools live-status label styling (Presets, Control preset strip, logging)."""
from __future__ import annotations

from PySide6 import QtWidgets


def summary_kind_to_status_kind(summary_kind: str) -> str:
    """Map Presets/tools summaryKind to modernToolsLiveStatus statusKind."""
    kind = (summary_kind or "").strip().lower()
    mapping = {
        "ok": "ok",
        "warn": "warn",
        "idle": "idle",
        "ready": "ready",
        "recording": "recording",
        "error": "error",
    }
    return mapping.get(kind, kind or "idle")


def create_modern_live_status_label() -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel("—")
    lbl.setWordWrap(True)
    lbl.setObjectName("modernToolsLiveStatus")
    return lbl


def apply_modern_live_status(
    lbl: QtWidgets.QLabel,
    line: str,
    tip: str,
    *,
    summary_kind: str | None = None,
    status_kind: str | None = None,
) -> None:
    """Apply text, tooltip, and dynamic kind properties; refresh stylesheet."""
    lbl.setText(line)
    lbl.setToolTip(tip)
    sk = (summary_kind or status_kind or "idle").strip().lower()
    tk = (status_kind or summary_kind_to_status_kind(sk)).strip().lower()
    lbl.setProperty("summaryKind", sk)
    lbl.setProperty("statusKind", tk)
    style = lbl.style()
    if style is not None:
        style.unpolish(lbl)
        style.polish(lbl)

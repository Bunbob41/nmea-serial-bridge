"""NMEA settings ↔ named preset comparison and copy helpers."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from PySide6 import QtWidgets


def extract_nmea_snapshot(data: dict) -> tuple[str, frozenset[str]]:
    mode = str(data.get("nmea_mode", "passthrough")).strip().lower()
    if mode not in ("passthrough", "strict", "raw"):
        mode = "passthrough"
    types: frozenset[str] = frozenset()
    raw = data.get("nmea_types")
    if mode == "strict" and isinstance(raw, list):
        types = frozenset(str(t).strip().upper() for t in raw if str(t).strip())
    return mode, types


def nmea_snapshot_from_parent(parent: QtWidgets.QWidget) -> tuple[str, frozenset[str]]:
    mode_fn = getattr(parent, "_nmea_mode_label", None)
    mode = mode_fn() if callable(mode_fn) else "passthrough"
    if mode not in ("passthrough", "strict", "raw"):
        mode = "passthrough"
    types: frozenset[str] = frozenset()
    if mode == "strict":
        checks = getattr(parent, "_nmea_type_checks", None) or {}
        types = frozenset(st for st, cb in checks.items() if cb.isChecked())
    return mode, types


def describe_nmea_snapshot(mode: str, types: frozenset[str]) -> str:
    from ui.nmea_display import nmea_mode_display_label

    label = nmea_mode_display_label(mode)
    if mode != "strict":
        return label
    if types:
        return f"{label} · {', '.join(sorted(types))}"
    return f"{label} · checksum only (no type filter)"


def format_nmea_preset_link(parent: QtWidgets.QWidget) -> tuple[str, str, str]:
    """Return (line, tooltip, summaryKind) for Tools → NMEA preset strip."""
    target_fn = getattr(parent, "_nmea_target_preset_name", None)
    target = target_fn() if callable(target_fn) else None
    target = (target or "").strip()
    ui_mode, ui_types = nmea_snapshot_from_parent(parent)
    ui_desc = describe_nmea_snapshot(ui_mode, ui_types)
    active = (getattr(parent, "_active_preset_name", None) or "").strip()
    sel_fn = getattr(parent, "_selected_preset_name", None)
    selected = (sel_fn() or "").strip() if callable(sel_fn) else ""

    if not target:
        return (
            "No preset linked — pick one on Presets or use Save as…",
            "Named presets store NMEA mode and strict sentence types with COM and network.",
            "idle",
        )

    try:
        from bench_config import load_preset

        stored_mode, stored_types = extract_nmea_snapshot(load_preset(target))
    except KeyError:
        return (
            f"Preset «{target}» not found on disk",
            "The preset may have been deleted. Refresh the Presets list.",
            "warn",
        )

    stored_desc = describe_nmea_snapshot(stored_mode, stored_types)
    matches = (ui_mode, ui_types) == (stored_mode, stored_types)

    if active == target:
        if matches:
            return (
                f"Stored in loaded preset «{target}» · {ui_desc}",
                f"Current NMEA matches the saved preset ({stored_desc}).",
                "ok",
            )
        return (
            f"Loaded «{target}» · NMEA changed — not saved ({ui_desc})",
            f"Preset file still has: {stored_desc}. Use Save NMEA to preset to update it.",
            "warn",
        )

    if selected == target:
        if matches:
            return (
                f"Matches preset «{target}» · {ui_desc}",
                f"Current NMEA matches what is stored in this preset.",
                "ok",
            )
        return (
            f"Differs from preset «{target}» · now {ui_desc}",
            f"Preset file has: {stored_desc}. Load from preset or Save to update the file.",
            "warn",
        )

    return (
        f"Preset «{target}» on file: {stored_desc}",
        "Load from preset to apply stored NMEA, or Save to write current settings.",
        "ready" if not matches else "ok",
    )


def strict_checksum_only_start(parent: QtWidgets.QWidget) -> bool:
    """True when Strict is on with zero sentence types enabled (checksum-only)."""
    mode_fn = getattr(parent, "_nmea_mode_label", None)
    if not callable(mode_fn) or mode_fn() != "strict":
        return False
    checks = getattr(parent, "_nmea_type_checks", None) or {}
    return not any(cb.isChecked() for cb in checks.values())

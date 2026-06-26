"""Serial COM disconnect — tray toast + Modern Control card chrome."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtWidgets

if TYPE_CHECKING:
    from ui.mixin import BridgeLogicMixin

SERIAL_DISCONNECT_TRAY_COOLDOWN_S = 90.0


def serial_disconnect_edge(prev_state: str, cur_state: str) -> bool:
    """True when the link drops from healthy open to auto-reconnect retry."""
    return prev_state == "open" and cur_state == "reconnecting"


def should_tray_notify_serial_disconnect(win: QtWidgets.QWidget) -> bool:
    """Tray toast when the operator may not see the Control serial card."""
    if not win.isVisible() or win.isMinimized():
        return True
    sid_fn = getattr(win, "_modern_current_section_sid", None)
    if callable(sid_fn):
        try:
            return str(sid_fn() or "") != "control"
        except Exception:
            return True
    return False


def reset_serial_link_alert_state(win: BridgeLogicMixin) -> None:
    win._last_serial_link_state = "closed"  # type: ignore[attr-defined]
    win._serial_disconnect_notify_mono = 0.0  # type: ignore[attr-defined]
    sync_serial_control_card(win, "closed")


def sync_serial_control_card(
    win: QtWidgets.QWidget,
    serial_state: str,
    *,
    com: str = "",
) -> None:
    """Highlight Modern Control → Serial link while COM auto-reconnect runs."""
    card = getattr(win, "_serial_control_card", None)
    badge = getattr(win, "_serial_link_status_badge", None)
    state = str(serial_state or "closed")
    if card is not None:
        card.setProperty("serialLinkState", state)
        style = card.style()
        if style is not None:
            style.unpolish(card)
            style.polish(card)
    if badge is None:
        return
    if state == "reconnecting":
        port = (com or "").strip() or "COM"
        badge.setText("Reconnecting…")
        badge.setToolTip(
            f"{port} dropped — auto-reconnect is retrying. "
            "Check the cable or USB hub; use Refresh if the port name changed."
        )
        badge.show()
    else:
        badge.hide()


def maybe_notify_serial_disconnect_tray(
    win: BridgeLogicMixin,
    *,
    prev_state: str,
    cur_state: str,
    com: str,
) -> None:
    if not serial_disconnect_edge(prev_state, cur_state):
        return
    if not should_tray_notify_serial_disconnect(win):
        return
    tray = getattr(win, "_tray_icon", None)
    if tray is None:
        return
    now = time.monotonic()
    last = float(getattr(win, "_serial_disconnect_notify_mono", 0.0) or 0.0)
    if now - last < SERIAL_DISCONNECT_TRAY_COOLDOWN_S:
        return
    win._serial_disconnect_notify_mono = now  # type: ignore[attr-defined]
    port = (com or "").strip() or "COM"
    tray.showMessage(
        "Serial Link — COM disconnected",
        f"{port} lost — auto-reconnect is retrying. Click to open Control.",
        QtWidgets.QSystemTrayIcon.MessageIcon.Warning,
        6000,
    )


def sync_serial_link_alerts(win: BridgeLogicMixin, stats: dict) -> None:
    """Apply card chrome and optional tray toast from transport stats."""
    cur = str(stats.get("serial_link_state") or "closed")
    prev = str(getattr(win, "_last_serial_link_state", "closed") or "closed")
    com = ""
    bridge = getattr(win, "bridge", None)
    if bridge is not None:
        com = str(getattr(bridge, "com", "") or "")
    sync_serial_control_card(win, cur, com=com)
    maybe_notify_serial_disconnect_tray(
        win,
        prev_state=prev,
        cur_state=cur,
        com=com,
    )
    win._last_serial_link_state = cur  # type: ignore[attr-defined]

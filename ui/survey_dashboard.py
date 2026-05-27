"""Survey Dashboard — bridge trust & reliability (opens with Survey HUD)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.app_icon import apply_app_icon
from ui.stats_line import queue_backlog, transport_alert_active
from ui.styles import hud_stylesheet

P0Status = Literal["ok", "warn", "idle", "info"]


@dataclass(frozen=True)
class P0CharterRow:
    item_id: str
    title: str
    status: P0Status
    detail: str
    tooltip: str


@dataclass(frozen=True)
class TrustVerdict:
    headline: str
    subline: str
    alert: bool


def evaluate_p0_charter(
    d: dict[str, Any],
    *,
    serial_line: str,
    network_line: str,
    running: bool,
    nmea_mode: str,
    udp_fanout: bool,
    serial_auto_reconnect: bool,
) -> list[P0CharterRow]:
    """Reliability checklist rows for Dashboard (unit-tested)."""
    serial_l = (serial_line or "").lower()
    network_l = (network_line or "").lower()
    rows: list[P0CharterRow] = []

    if not running:
        rows.append(
            P0CharterRow(
                "transport",
                "Data path healthy",
                "idle",
                "Start the bridge to watch drops, rejects, and queues.",
                "Matches the status-bar transport warning when Running.",
            )
        )
    else:
        alert = transport_alert_active(d)
        d_ns = int(d.get("drops_n2s", 0))
        d_sn = int(d.get("drops_s2n", 0))
        r_ns = int(d.get("rej_n2s", 0))
        r_sn = int(d.get("rej_s2n", 0))
        q_ns = int(d.get("n2s_q", 0))
        q_sn = int(d.get("s2n_q", 0))
        if alert:
            parts = []
            if d_ns or d_sn:
                parts.append(f"drops {d_ns}+{d_sn}")
            if r_ns or r_sn:
                parts.append(f"rejects {r_ns}+{r_sn}")
            if queue_backlog(q_ns, q_sn):
                parts.append(f"queues {q_ns}/{q_sn}")
            detail = " · ".join(parts) if parts else "transport pressure"
            rows.append(
                P0CharterRow(
                    "transport",
                    "Data path healthy",
                    "warn",
                    detail,
                    "Queues full or lines dropped — check consumer on COM or network.",
                )
            )
        else:
            rows.append(
                P0CharterRow(
                    "transport",
                    "Data path healthy",
                    "ok",
                    f"transport OK · queues {q_ns}/{q_sn}",
                    "No drops, rejects, or backlog on either bridge queue.",
                )
            )

    if not running:
        com_status: P0Status = "idle"
        com_detail = "Stopped — Start runs COM preflight before opening the port."
    elif "cannot open" in serial_l or "in use" in serial_l or "busy" in serial_l:
        com_status = "warn"
        com_detail = "COM blocked — close other apps, Unlock, Refresh, replug USB."
    elif "retry" in serial_l or "disconnected" in serial_l:
        com_status = "warn"
        com_detail = "Serial retrying — wait until open again."
    elif "open" in serial_l:
        com_status = "ok"
        com_detail = "COM open — exclusivity checks passed at Start."
    else:
        com_status = "info"
        com_detail = serial_line.strip() or "Serial status pending…"
    rows.append(
        P0CharterRow(
            "com",
            "COM port ready",
            com_status,
            com_detail,
            "Start blocks when the port is busy and lists recovery steps.",
        )
    )

    if not running:
        recon_status: P0Status = "idle"
        recon_detail = "Auto-reconnect applies while Running."
    elif not serial_auto_reconnect:
        recon_status = "info"
        recon_detail = "Auto-reconnect OFF on Connect."
    elif "retry" in serial_l or "disconnected" in serial_l:
        recon_status = "warn"
        recon_detail = "Reconnect active — buffers reset on reopen."
    else:
        recon_status = "ok"
        recon_detail = "Serial session stable · auto-reconnect armed."
    rows.append(
        P0CharterRow(
            "reconnect",
            "Serial auto-reconnect",
            recon_status,
            recon_detail,
            "Partial NMEA buffers clear after COM drop/reopen.",
        )
    )

    peers = int(d.get("udp_peers", 0) or 0)
    if not running:
        net_status: P0Status = "idle"
        net_detail = "Network idle — see OPERATOR_GUIDE §6.4 for INS UDP wiring."
    elif "listen" in network_l or "peer" in network_l or "tcp" in network_l:
        fan = "Fan-out ON" if udp_fanout else "last sender only"
        net_status = "ok"
        net_detail = fan
        if peers:
            net_detail += f" · {peers} UDP peer(s)"
        if "tcp" in network_l:
            net_detail += " · TCP path active"
    else:
        net_status = "info"
        net_detail = network_line.strip() or "Network starting…"
    rows.append(
        P0CharterRow(
            "network",
            "Network path",
            net_status,
            net_detail,
            "UDP listen direction, fan-out, firewall, TCP reconnect.",
        )
    )

    mode = (nmea_mode or "passthrough").strip().lower()
    if mode == "raw":
        raw_status: P0Status = "ok"
        raw_detail = "RAW binary — bytes forwarded without NMEA assembly."
    elif mode == "strict":
        raw_status = "info"
        raw_detail = "Strict NMEA — checksum/type filter active."
    else:
        raw_status = "info"
        raw_detail = "Passthrough NMEA — default survey path."
    rows.append(
        P0CharterRow(
            "raw",
            "NMEA / binary mode",
            raw_status,
            raw_detail,
            "RAW mode keeps RTCM/binary bytes intact (automated tests).",
        )
    )

    rows.append(
        P0CharterRow(
            "bench",
            "Bench automation",
            "ok",
            "network + fan-out scripts in verify_all / Diagnostics",
            "bench_network_automation.py · bench_fanout_automation.py",
        )
    )
    return rows


def compute_trust_verdict(
    rows: list[P0CharterRow],
    d: dict[str, Any],
    *,
    running: bool,
) -> TrustVerdict:
    if not running:
        return TrustVerdict("Stopped", "Start the bridge to see field-ready status.", False)

    warns = [r for r in rows if r.status == "warn"]
    if warns:
        return TrustVerdict("Caution", warns[0].detail, True)

    hz_d = float(d.get("hz_down", 0.0))
    hz_u = float(d.get("hz_up", 0.0))
    peers = int(d.get("udp_peers", 0) or 0)
    peer_bit = f" · {peers} UDP peer(s)" if peers else ""
    return TrustVerdict(
        "Ready",
        f"Into COM {hz_d:.1f} Hz · From COM {hz_u:.1f} Hz · transport OK{peer_bit}",
        False,
    )


def _status_badge_text(status: P0Status) -> str:
    return {"ok": "OK", "warn": "!", "idle": "—", "info": "i"}.get(status, "?")


class _ChecklistRow(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("surveyDashboardCheckRow")
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(8)
        self._badge = QtWidgets.QLabel("—")
        self._badge.setObjectName("surveyDashboardCheckBadge")
        self._badge.setFixedWidth(36)
        self._badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._title = QtWidgets.QLabel("")
        self._title.setObjectName("surveyDashboardCheckTitle")
        self._detail = QtWidgets.QLabel("")
        self._detail.setObjectName("surveyDashboardCheckDetail")
        self._detail.setWordWrap(True)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(self._title)
        col.addWidget(self._detail)
        lay.addWidget(self._badge)
        lay.addLayout(col, 1)

    def apply(self, row: P0CharterRow) -> None:
        self._title.setText(row.title)
        self._detail.setText(row.detail)
        self.setToolTip(row.tooltip)
        self._badge.setText(_status_badge_text(row.status))
        colors = {
            "ok": ("#14532d", "#bbf7d0"),
            "warn": ("#7f1d1d", "#fecaca"),
            "idle": ("#374151", "#d1d5db"),
            "info": ("#1e3a5f", "#bfdbfe"),
        }
        bg, fg = colors.get(row.status, colors["idle"])
        self._badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 4px; font-weight: 600;"
        )


class _HealthChip(QtWidgets.QLabel):
    def __init__(self, label: str, tooltip: str) -> None:
        super().__init__(label)
        self.setObjectName("surveyDashboardHealthChip")
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(72)
        self.setToolTip(tooltip)
        self._base_label = label

    def set_state(self, text: str, *, alert: bool = False) -> None:
        self.setText(f"{self._base_label}: {text}")
        if alert:
            self.setStyleSheet(
                "background-color: #7f1d1d; color: #fff3f3; "
                "border: 1px solid #ef9a9a; border-radius: 6px; padding: 4px 8px;"
            )
        else:
            self.setStyleSheet(
                "background-color: #1f2937; color: #e5e7eb; "
                "border: 1px solid #4b5563; border-radius: 6px; padding: 4px 8px;"
            )


class SurveyDashboard(QtWidgets.QWidget):
    """Bridge trust panel — Hz and GNSS detail stay on Survey HUD."""

    def __init__(self, bridge_window: QtWidgets.QWidget) -> None:
        flags = QtCore.Qt.WindowType.Window | QtCore.Qt.WindowType.WindowStaysOnTopHint
        super().__init__(None, flags)
        self._bridge = bridge_window
        theme_id = getattr(bridge_window, "_theme_id", "maroon_classic")
        self.setObjectName("SurveyDashboard")
        self.setWindowTitle("Dashboard — bridge trust")
        self.setMinimumSize(440, 320)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        apply_app_icon(self)
        self.setStyleSheet(
            hud_stylesheet(theme_id)
            + """
            QFrame#surveyDashboardHero {
                background-color: #1e293b;
                border: 1px solid #475569;
                border-radius: 8px;
            }
            QLabel#surveyDashboardHeroHeadline {
                font-size: 22px;
                font-weight: 700;
                color: #f8fafc;
            }
            QLabel#surveyDashboardHeroSub {
                color: #cbd5e1;
            }
            QLabel#surveyDashboardHeroHeadline[alert="true"] {
                color: #fecaca;
            }
            QLabel#surveyDashboardAllOk {
                color: #86efac;
                font-weight: 600;
            }
            """
        )

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        hero = QtWidgets.QFrame()
        hero.setObjectName("surveyDashboardHero")
        hl = QtWidgets.QVBoxLayout(hero)
        hl.setContentsMargins(10, 8, 10, 8)
        self._hero_head = QtWidgets.QLabel("Stopped")
        self._hero_head.setObjectName("surveyDashboardHeroHeadline")
        self._hero_sub = QtWidgets.QLabel("Start the bridge to see field-ready status.")
        self._hero_sub.setObjectName("surveyDashboardHeroSub")
        self._hero_sub.setWordWrap(True)
        hl.addWidget(self._hero_head)
        hl.addWidget(self._hero_sub)
        root.addWidget(hero)

        chip_row = QtWidgets.QHBoxLayout()
        chip_row.setSpacing(6)
        self._chip_serial = _HealthChip("Serial", "COM open / retry / blocked")
        self._chip_network = _HealthChip("Network", "UDP listen / TCP / peers")
        self._chip_nmea = _HealthChip("NMEA", "Passthrough / strict / raw")
        self._chip_run = _HealthChip("Bridge", "Running or stopped")
        for c in (self._chip_serial, self._chip_network, self._chip_nmea, self._chip_run):
            chip_row.addWidget(c, 1)
        root.addLayout(chip_row)

        checks_head = QtWidgets.QHBoxLayout()
        checks_head.addWidget(QtWidgets.QLabel("Reliability checks"))
        checks_head.addStretch(1)
        self._chk_show_all = QtWidgets.QCheckBox("Show all")
        self._chk_show_all.setToolTip("Show passed checks; by default only issues are listed.")
        checks_head.addWidget(self._chk_show_all)
        root.addLayout(checks_head)

        self._all_ok = QtWidgets.QLabel("All checks passed.")
        self._all_ok.setObjectName("surveyDashboardAllOk")
        self._all_ok.setVisible(False)
        root.addWidget(self._all_ok)

        self._p0_rows: dict[str, _ChecklistRow] = {}
        self._issues_host = QtWidgets.QWidget()
        issues_lay = QtWidgets.QVBoxLayout(self._issues_host)
        issues_lay.setContentsMargins(0, 0, 0, 0)
        issues_lay.setSpacing(2)
        for item_id in ("transport", "com", "reconnect", "network", "raw", "bench"):
            row = _ChecklistRow()
            self._p0_rows[item_id] = row
            issues_lay.addWidget(row)
        root.addWidget(self._issues_host)

        hint = QtWidgets.QLabel(
            "Survey HUD (opened with HUD) shows Hz, GNSS, and session totals."
        )
        hint.setObjectName("surveyHudFootLine")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._chk_show_all.toggled.connect(lambda _on: self._apply_row_visibility())
        self.apply_snapshot({}, "", "", running=False)

    def _bridge_alive(self) -> bool:
        w = self._bridge
        if w is None:
            return False
        try:
            from shiboken6 import isValid

            return bool(isValid(w))
        except Exception:
            try:
                w.isVisible()
                return True
            except RuntimeError:
                return False

    def _bridge_context(self) -> dict[str, Any]:
        w = self._bridge
        mode = "passthrough"
        fanout = True
        auto = True
        if not self._bridge_alive():
            return {
                "nmea_mode": mode,
                "udp_fanout": fanout,
                "serial_auto_reconnect": auto,
            }
        b = getattr(w, "bridge", None)
        if b is not None:
            try:
                nm = getattr(b, "nmea_mode", None)
                if nm is not None:
                    mode = str(getattr(nm, "value", nm))
            except (RuntimeError, AttributeError):
                pass
        try:
            chk = getattr(w, "chk_udp_fanout", None)
            if chk is not None:
                fanout = bool(chk.isChecked())
            chk_ar = getattr(w, "chk_serial_auto_reconnect", None)
            if chk_ar is not None:
                auto = bool(chk_ar.isChecked())
        except RuntimeError:
            pass
        return {"nmea_mode": str(mode), "udp_fanout": fanout, "serial_auto_reconnect": auto}

    def _apply_row_visibility(self) -> None:
        show_all = self._chk_show_all.isChecked()
        for row in self._p0_rows.values():
            if show_all:
                row.setVisible(True)
            else:
                row.setVisible(row.property("needs_attention") is True)

    def apply_snapshot(
        self,
        d: dict[str, Any],
        serial_line: str,
        network_line: str,
        *,
        running: bool,
    ) -> None:
        if not self._bridge_alive():
            self.close()
            return
        ctx = self._bridge_context()
        rows = evaluate_p0_charter(
            d,
            serial_line=serial_line,
            network_line=network_line,
            running=running,
            nmea_mode=str(ctx["nmea_mode"]),
            udp_fanout=bool(ctx["udp_fanout"]),
            serial_auto_reconnect=bool(ctx["serial_auto_reconnect"]),
        )
        verdict = compute_trust_verdict(rows, d, running=running)
        self._hero_head.setText(verdict.headline)
        self._hero_sub.setText(verdict.subline)
        self._hero_head.setProperty("alert", verdict.alert)
        self._hero_head.style().unpolish(self._hero_head)
        self._hero_head.style().polish(self._hero_head)

        for row in rows:
            widget = self._p0_rows.get(row.item_id)
            if widget is None:
                continue
            widget.apply(row)
            needs = row.status in ("warn", "idle") or (
                row.status == "info" and row.item_id not in ("bench", "raw")
            )
            widget.setProperty("needs_attention", needs)

        has_issues = any(
            self._p0_rows[r.item_id].property("needs_attention")
            for r in rows
            if r.item_id in self._p0_rows
        )
        self._all_ok.setVisible(running and not has_issues and not self._chk_show_all.isChecked())
        self._apply_row_visibility()

        serial_short = serial_line.split("—", 1)[-1].strip() if serial_line else "—"
        network_short = network_line.split("—", 1)[-1].strip() if network_line else "—"
        serial_alert = running and any(
            x in serial_line.lower() for x in ("retry", "disconnected", "cannot", "busy", "in use")
        )
        net_alert = running and transport_alert_active(d)
        self._chip_serial.set_state(serial_short[:28] if serial_short else "—", alert=serial_alert)
        self._chip_network.set_state(network_short[:28] if network_short else "—", alert=net_alert)
        mode = str(ctx["nmea_mode"]).lower().replace("nmeamode.", "")
        self._chip_nmea.set_state(mode[:12] or "—", alert=mode == "raw")
        self._chip_run.set_state("Running" if running else "Stopped", alert=False)

    def place_beside(self, anchor: QtWidgets.QWidget, *, gap: int = 10) -> None:
        """Tile to the right of Survey HUD (or main window)."""
        try:
            g = anchor.frameGeometry()
        except RuntimeError:
            return
        self.move(g.right() + gap, g.y())
        if self.height() < 200:
            self.adjustSize()

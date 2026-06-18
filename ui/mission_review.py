"""Mission Review tab — throughput chart, health timeline, quick export (Modern UI)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.backup_status import _human_bytes
from ui.mission_session import MissionSessionRecord

if TYPE_CHECKING:
    from ui.mixin import BridgeLogicMixin

# High-contrast palette (matches Modern fixed theme)
_CHART_BG = "#050a12"
_CHART_BAR = "#38bdf8"
_CHART_BAR_HI = "#34d399"
_CHART_GRID = "#334155"
_CHART_TEXT = "#e2e8f0"
_TICK_OK = "#34d399"
_TICK_WARN = "#fbbf24"
_TICK_BAD = "#f87171"
_TICK_IDLE = "#475569"


class ThroughputBarChart(QtWidgets.QWidget):
    """Small bar chart — backup bytes per 5 s bucket."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("missionThroughputChart")
        self._values: list[int] = []
        self.setMinimumHeight(140)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

    def set_values(self, values: list[int]) -> None:
        self._values = [max(0, int(v)) for v in values]
        self.update()

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -24)
        p.fillRect(self.rect(), QtGui.QColor(_CHART_BG))

        p.setPen(QtGui.QColor(_CHART_TEXT))
        p.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Weight.DemiBold))
        p.drawText(8, 16, "Backup throughput (5 s buckets)")

        if not self._values or rect.width() <= 4 or rect.height() <= 4:
            p.setPen(QtGui.QColor("#94a3b8"))
            p.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, "No throughput samples")
            p.end()
            return

        peak = max(self._values) or 1
        n = len(self._values)
        gap = 2
        bar_w = max(3, (rect.width() - gap * (n - 1)) // n)
        x = rect.left()
        for i, val in enumerate(self._values):
            h = int((val / peak) * rect.height()) if peak else 0
            h = max(2, h) if val > 0 else 0
            bar_rect = QtCore.QRect(x, rect.bottom() - h, bar_w, h)
            color = _CHART_BAR_HI if val == peak and val > 0 else _CHART_BAR
            p.fillRect(bar_rect, QtGui.QColor(color))
            x += bar_w + gap

        p.setPen(QtGui.QColor(_CHART_GRID))
        p.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        p.setPen(QtGui.QColor("#94a3b8"))
        p.drawText(rect.left(), self.height() - 6, f"peak {_human_bytes(peak)} / bucket")
        p.end()


class HealthTimeline(QtWidgets.QWidget):
    """Data health timeline — green / amber / red ticks per bucket."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("missionHealthTimeline")
        self._ticks: list[str] = []
        self.setMinimumHeight(44)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

    def set_ticks(self, ticks: list[str]) -> None:
        self._ticks = list(ticks)
        self.update()

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(_CHART_BG))
        p.setPen(QtGui.QColor(_CHART_TEXT))
        p.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Weight.DemiBold))
        p.drawText(8, 16, "Data health timeline")

        rect = self.rect().adjusted(8, 22, -8, -8)
        if not self._ticks:
            p.setPen(QtGui.QColor("#94a3b8"))
            p.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, "No health windows")
            p.end()
            return

        n = len(self._ticks)
        gap = 2
        tick_w = max(4, (rect.width() - gap * (n - 1)) // n)
        x = rect.left()
        for tick in self._ticks:
            if tick == "bad":
                color = _TICK_BAD
            elif tick == "warn":
                color = _TICK_WARN
            elif tick == "ok":
                color = _TICK_OK
            else:
                color = _TICK_IDLE
            p.fillRect(QtCore.QRect(x, rect.top(), tick_w, rect.height()), QtGui.QColor(color))
            x += tick_w + gap
        p.end()


def create_mission_review_tab(win: BridgeLogicMixin) -> QtWidgets.QWidget:
    """Build the Mission Review panel (hidden until post-stop reveal)."""
    panel = QtWidgets.QWidget()
    panel.setObjectName("modernMissionReview")
    lay = QtWidgets.QVBoxLayout(panel)
    lay.setContentsMargins(20, 16, 20, 16)
    lay.setSpacing(14)

    win._mission_review_headline = QtWidgets.QLabel("Mission Review")
    win._mission_review_headline.setObjectName("modernTabSectionTitle")
    lay.addWidget(win._mission_review_headline)

    win._mission_review_summary = QtWidgets.QLabel()
    win._mission_review_summary.setObjectName("modernIntentHint")
    win._mission_review_summary.setWordWrap(True)
    lay.addWidget(win._mission_review_summary)

    win._mission_throughput_chart = ThroughputBarChart()
    lay.addWidget(win._mission_throughput_chart)

    win._mission_health_timeline = HealthTimeline()
    lay.addWidget(win._mission_health_timeline)

    win._mission_integrity_note = QtWidgets.QLabel()
    win._mission_integrity_note.setObjectName("modernIntentHint")
    win._mission_integrity_note.setWordWrap(True)
    lay.addWidget(win._mission_integrity_note)

    from ui.local_backup_settings import mount_local_backup_location_row

    win._mission_backup_location_box = QtWidgets.QWidget()
    backup_lay = QtWidgets.QVBoxLayout(win._mission_backup_location_box)
    backup_lay.setContentsMargins(0, 0, 0, 0)
    backup_lay.setSpacing(8)
    section = QtWidgets.QLabel("Next session backup location")
    section.setObjectName("modernTabSectionTitle")
    backup_lay.addWidget(section)
    mount_local_backup_location_row(win, backup_lay, show_session_file=True)
    lay.addWidget(win._mission_backup_location_box)

    actions = QtWidgets.QHBoxLayout()
    win._mission_btn_quick_export = QtWidgets.QPushButton("Quick Export")
    win._mission_btn_quick_export.setObjectName("modernStartBtn")
    win._mission_btn_quick_export.setToolTip(
        "Zip the session .raw backup and mission_summary.txt for survey office handoff."
    )
    win._mission_btn_quick_export.clicked.connect(win._on_mission_quick_export)
    actions.addWidget(win._mission_btn_quick_export)
    actions.addStretch(1)
    btn_pipeline = QtWidgets.QPushButton("Back to Activity")
    btn_pipeline.clicked.connect(win._show_modern_pipeline_tab)
    actions.addWidget(btn_pipeline)
    lay.addLayout(actions)
    lay.addStretch(1)
    return panel


def populate_mission_review(
    win: BridgeLogicMixin,
    record: MissionSessionRecord,
    summary: dict[str, object],
) -> None:
    """Fill charts and copy after Stop bridge."""
    from ui.mission_summary import format_mission_summary_line, verify_backup_on_disk

    _disk, warn, detail = verify_backup_on_disk(summary)
    line = format_mission_summary_line(summary)
    mins = int(record.duration_s // 60)
    secs = int(record.duration_s % 60)

    win._mission_review_summary.setText(
        f"{line}\n"
        f"Duration {mins}m {secs}s · avg {record.avg_hz_up:.1f} Hz COM→net"
    )
    win._mission_throughput_chart.set_values(record.throughput_buckets)
    win._mission_health_timeline.set_ticks(record.health_ticks)

    bad = sum(1 for t in record.health_ticks if t == "bad")
    warn_n = sum(1 for t in record.health_ticks if t == "warn")
    if warn:
        win._mission_integrity_note.setText(
            f"⚠ Integrity warning: {detail}\n"
            f"Timeline: {bad} critical / {warn_n} caution windows before export."
        )
        win._mission_integrity_note.setStyleSheet("color: #fbbf24;")
    elif bad > 0:
        win._mission_integrity_note.setText(
            f"Timeline shows {bad} critical window(s) with drops or write stress. "
            "Review before post-processing."
        )
        win._mission_integrity_note.setStyleSheet("color: #fbbf24;")
    else:
        win._mission_integrity_note.setText(
            "Data health timeline looks clean — ready for Quick Export to the survey office."
        )
        win._mission_integrity_note.setStyleSheet("color: #94a3b8;")

    win._mission_session_record = record
    win._mission_session_summary = dict(summary)

    from ui.local_backup_settings import set_mission_session_path_label, sync_local_backup_location_ui

    sync_local_backup_location_ui(win)
    set_mission_session_path_label(win, str(summary.get("path") or record.backup_path or ""))


def reveal_mission_review_tab(
    win: BridgeLogicMixin,
    record: MissionSessionRecord,
    summary: dict[str, object],
) -> None:
    """Show Mission Review and switch to it (Modern UI only)."""
    try:
        populate_mission_review(win, record, summary)
        opener = getattr(win, "_open_modern_section_by_sid", None)
        if callable(opener):
            opener("mission_review")
    except Exception:
        pass


def hide_mission_review_tab(win: BridgeLogicMixin) -> None:
    try:
        opener = getattr(win, "_open_modern_section_by_sid", None)
        if callable(opener):
            opener("activity")
    except Exception:
        pass

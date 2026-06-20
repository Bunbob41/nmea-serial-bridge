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
_CHART_TITLE_BAND = 24
_CHART_FOOTER_BAND = 18
_CHART_MAX_PILL_BG = "#1e293b"
_CHART_MAX_PILL_BORDER = "#64748b"
_CHART_MAX_PILL_TEXT = "#f8fafc"


def _draw_max_value_pill(
    painter: QtGui.QPainter,
    host_rect: QtCore.QRect,
    text: str,
    *,
    font: QtGui.QFont,
) -> None:
    """Draw peak label on a solid pill — call last so it sits above chart bars."""
    label_font = QtGui.QFont(font)
    label_font.setWeight(QtGui.QFont.Weight.DemiBold)
    painter.setFont(label_font)
    metrics = painter.fontMetrics()
    pad_x = 8
    pad_y = 4
    text_w = metrics.horizontalAdvance(text) + pad_x * 2
    text_h = metrics.height() + pad_y * 2
    pill = QtCore.QRect(
        host_rect.right() - text_w,
        host_rect.top() + max(0, (host_rect.height() - text_h) // 2),
        text_w,
        text_h,
    )
    painter.setPen(QtGui.QPen(QtGui.QColor(_CHART_MAX_PILL_BORDER), 1))
    painter.setBrush(QtGui.QColor(_CHART_MAX_PILL_BG))
    painter.drawRoundedRect(pill, 5, 5)
    painter.setPen(QtGui.QColor(_CHART_MAX_PILL_TEXT))
    painter.drawText(
        pill,
        int(QtCore.Qt.AlignmentFlag.AlignCenter),
        text,
    )


def _mission_metric_chip(label: str, value: str) -> tuple[QtWidgets.QFrame, QtWidgets.QLabel]:
    card = QtWidgets.QFrame()
    card.setObjectName("missionMetricChip")
    lay = QtWidgets.QVBoxLayout(card)
    lay.setContentsMargins(12, 8, 12, 8)
    lay.setSpacing(2)
    value_lbl = QtWidgets.QLabel(value)
    value_lbl.setObjectName("missionMetricValue")
    title_lbl = QtWidgets.QLabel(label.upper())
    title_lbl.setObjectName("missionMetricLabel")
    lay.addWidget(value_lbl)
    lay.addWidget(title_lbl)
    return card, value_lbl


class ThroughputBarChart(QtWidgets.QWidget):
    """Small bar chart — backup bytes per 5 s bucket."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("missionThroughputChart")
        self._values: list[int] = []
        self.setMinimumHeight(76)
        self.setMaximumHeight(108)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

    def set_values(self, values: list[int]) -> None:
        self._values = [max(0, int(v)) for v in values]
        n = len(self._values)
        if n <= 1:
            self.setFixedHeight(76)
        elif n <= 4:
            self.setFixedHeight(88)
        else:
            self.setFixedHeight(min(108, 76 + n * 2))
        self.update()

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(_CHART_BG))
        title_rect = QtCore.QRect(8, 2, self.width() - 16, _CHART_TITLE_BAND - 2)
        chart_rect = self.rect().adjusted(8, _CHART_TITLE_BAND + 2, -8, -_CHART_FOOTER_BAND)

        p.setPen(QtGui.QColor(_CHART_TEXT))
        from ui.fonts import app_ui_font

        title_font = app_ui_font(point_size=9)
        title_font.setWeight(QtGui.QFont.Weight.DemiBold)
        p.setFont(title_font)
        title_text_rect = QtCore.QRect(
            title_rect.left(),
            title_rect.top(),
            max(title_rect.width() // 2, title_rect.width() - 120),
            title_rect.height(),
        )
        p.drawText(
            title_text_rect,
            int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter),
            "Backup throughput (5 s buckets)",
        )

        if not self._values or chart_rect.width() <= 4 or chart_rect.height() <= 4:
            p.setPen(QtGui.QColor("#94a3b8"))
            p.drawText(chart_rect, QtCore.Qt.AlignmentFlag.AlignCenter, "No throughput samples")
            p.end()
            return

        peak = max(self._values) or 1
        n = len(self._values)
        gap = 2
        bar_w = max(3, (chart_rect.width() - gap * (n - 1)) // n)
        x = chart_rect.left()
        max_bar_h = chart_rect.height() if n > 1 else max(10, chart_rect.height() // 4)

        p.setPen(QtGui.QColor(_CHART_GRID))
        for i in range(1, 4):
            y = chart_rect.top() + (chart_rect.height() * i) / 4
            p.drawLine(chart_rect.left(), int(y), chart_rect.right(), int(y))

        for i, val in enumerate(self._values):
            h = int((val / peak) * chart_rect.height()) if peak else 0
            if val > 0:
                h = max(2, min(h, max_bar_h))
            else:
                h = 0
            bar_rect = QtCore.QRect(x, chart_rect.bottom() - h, bar_w, h)
            color = _CHART_BAR_HI if val == peak and val > 0 else _CHART_BAR
            p.fillRect(bar_rect, QtGui.QColor(color))
            x += bar_w + gap

        p.setPen(QtGui.QColor(_CHART_GRID))
        p.drawLine(chart_rect.left(), chart_rect.bottom(), chart_rect.right(), chart_rect.bottom())
        axis_font = app_ui_font(point_size=7)
        p.setPen(QtGui.QColor("#94a3b8"))
        p.setFont(axis_font)
        p.drawText(chart_rect.left(), self.height() - 6, f"peak {_human_bytes(peak)} / bucket")
        # Peak pill last — title band keeps it clear of filled bars at 100% height.
        _draw_max_value_pill(
            p,
            title_rect,
            f"max {_human_bytes(peak)}",
            font=axis_font,
        )
        p.end()


class HealthTimeline(QtWidgets.QWidget):
    """Data health timeline — green / amber / red ticks per bucket."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("missionHealthTimeline")
        self._ticks: list[str] = []
        self.setMinimumHeight(44)
        self.setMaximumHeight(56)
        self.setFixedHeight(48)
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
        chart_rect = self.rect().adjusted(8, _CHART_TITLE_BAND + 2, -8, -8)

        p.setPen(QtGui.QColor(_CHART_TEXT))
        from ui.fonts import app_ui_font

        title_font = app_ui_font(point_size=9)
        title_font.setWeight(QtGui.QFont.Weight.DemiBold)
        p.setFont(title_font)
        p.drawText(8, 20, "Data health timeline")

        if not self._ticks:
            p.setPen(QtGui.QColor("#94a3b8"))
            p.drawText(chart_rect, QtCore.Qt.AlignmentFlag.AlignCenter, "No health windows")
            p.end()
            return

        n = len(self._ticks)
        gap = 2
        tick_w = max(4, (chart_rect.width() - gap * (n - 1)) // n)
        x = chart_rect.left()
        for tick in self._ticks:
            if tick == "bad":
                color = _TICK_BAD
            elif tick == "warn":
                color = _TICK_WARN
            elif tick == "ok":
                color = _TICK_OK
            else:
                color = _TICK_IDLE
            p.fillRect(
                QtCore.QRect(x, chart_rect.top(), tick_w, chart_rect.height()),
                QtGui.QColor(color),
            )
            x += tick_w + gap
        p.end()


def create_mission_review_tab(win: BridgeLogicMixin) -> QtWidgets.QWidget:
    """Build the Mission Review panel (hidden until post-stop reveal)."""
    panel = QtWidgets.QWidget()
    panel.setObjectName("modernMissionReview")
    outer = QtWidgets.QVBoxLayout(panel)
    outer.setContentsMargins(16, 12, 16, 12)
    outer.setSpacing(10)

    body = QtWidgets.QWidget()
    body.setObjectName("missionReviewBody")
    body.setMaximumWidth(980)
    lay = QtWidgets.QVBoxLayout(body)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)

    head_row = QtWidgets.QHBoxLayout()
    win._mission_review_headline = QtWidgets.QLabel("Mission Review")
    win._mission_review_headline.setObjectName("modernTabSectionTitle")
    head_row.addWidget(win._mission_review_headline, 1)
    lay.addLayout(head_row)

    metrics = QtWidgets.QHBoxLayout()
    metrics.setSpacing(8)
    _b, win._mission_metric_bytes = _mission_metric_chip("Safeguarded", "—")
    metrics.addWidget(_b, 1)
    _d, win._mission_metric_drops = _mission_metric_chip("Dropped", "—")
    metrics.addWidget(_d, 1)
    _t, win._mission_metric_duration = _mission_metric_chip("Duration", "—")
    metrics.addWidget(_t, 1)
    _h, win._mission_metric_hz = _mission_metric_chip("COM→net", "—")
    metrics.addWidget(_h, 1)
    lay.addLayout(metrics)

    win._mission_review_summary = QtWidgets.QLabel()
    win._mission_review_summary.setObjectName("modernIntentHint")
    win._mission_review_summary.setWordWrap(True)
    lay.addWidget(win._mission_review_summary)

    charts_row = QtWidgets.QHBoxLayout()
    charts_row.setSpacing(10)
    win._mission_throughput_chart = ThroughputBarChart()
    charts_row.addWidget(win._mission_throughput_chart, 3)
    win._mission_health_timeline = HealthTimeline()
    charts_row.addWidget(win._mission_health_timeline, 2)
    lay.addLayout(charts_row)

    win._mission_integrity_note = QtWidgets.QLabel()
    win._mission_integrity_note.setObjectName("modernIntentHint")
    win._mission_integrity_note.setWordWrap(True)
    lay.addWidget(win._mission_integrity_note)

    from ui.local_backup_settings import mount_local_backup_location_row

    win._mission_backup_location_box = QtWidgets.QWidget()
    backup_lay = QtWidgets.QVBoxLayout(win._mission_backup_location_box)
    backup_lay.setContentsMargins(0, 0, 0, 0)
    backup_lay.setSpacing(6)
    section = QtWidgets.QLabel("Next session backup location")
    section.setObjectName("modernToolsSectionTitle")
    backup_lay.addWidget(section)
    mount_local_backup_location_row(win, backup_lay, show_session_file=True)
    lay.addWidget(win._mission_backup_location_box)

    actions = QtWidgets.QHBoxLayout()
    actions.setSpacing(8)
    actions.addStretch(1)
    win._mission_btn_quick_export = QtWidgets.QPushButton("Quick Export")
    win._mission_btn_quick_export.setObjectName("modernToolsPrimaryBtn")
    win._mission_btn_quick_export.setToolTip(
        "Save the session NMEA backup as .nmea, .log, or .txt for GIS / hydro tools."
    )
    win._mission_btn_quick_export.clicked.connect(win._on_mission_quick_export)
    actions.addWidget(win._mission_btn_quick_export, 0)
    btn_pipeline = QtWidgets.QPushButton("Back to Activity")
    btn_pipeline.setObjectName("modernToolsSecondaryBtn")
    btn_pipeline.setToolTip("Return to the Activity wire-tap view.")
    btn_pipeline.clicked.connect(win._show_modern_pipeline_tab)
    actions.addWidget(btn_pipeline, 0)
    lay.addLayout(actions)

    outer.addWidget(body, 0, QtCore.Qt.AlignmentFlag.AlignTop)
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

    bytes_lbl = getattr(win, "_mission_metric_bytes", None)
    drops_lbl = getattr(win, "_mission_metric_drops", None)
    dur_lbl = getattr(win, "_mission_metric_duration", None)
    hz_lbl = getattr(win, "_mission_metric_hz", None)
    nbytes = int(summary.get("bytes") or summary.get("nbytes") or 0)
    drops = int(summary.get("dropped") or summary.get("drops") or 0)
    if bytes_lbl is not None:
        bytes_lbl.setText(_human_bytes(nbytes))
    if drops_lbl is not None:
        drops_lbl.setText(str(drops))
    if dur_lbl is not None:
        dur_lbl.setText(f"{mins}m {secs}s")
    if hz_lbl is not None:
        hz_lbl.setText(f"{record.avg_hz_up:.1f} Hz")

    path = str(summary.get("path") or record.backup_path or "").strip()
    win._mission_review_summary.setText(
        line if line else "Session complete."
    )
    if path:
        win._mission_review_summary.setToolTip(path)
    else:
        win._mission_review_summary.setToolTip("")
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

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


class ThroughputBarChart(QtWidgets.QWidget):
    """Small bar chart — backup bytes per 5 s bucket."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("missionThroughputChart")
        self._values: list[int] = []
        self._scrub_index = -1
        self.setMinimumHeight(76)
        self.setMaximumHeight(108)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

    def set_scrub_index(self, index: int) -> None:
        if not self._values:
            self._scrub_index = -1
        else:
            self._scrub_index = max(0, min(int(index), len(self._values) - 1))
        self.update()

    def set_values(self, values: list[int]) -> None:
        self._values = [max(0, int(v)) for v in values]
        self._scrub_index = max(0, len(self._values) - 1)
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
            block_h = min(chart_rect.height(), 56)
            block_top = chart_rect.top() + max(0, (chart_rect.height() - block_h) // 2)
            block = QtCore.QRect(
                chart_rect.left(),
                block_top,
                chart_rect.width(),
                block_h,
            )
            icon_rect = QtCore.QRect(block.left(), block.top(), block.width(), 22)
            msg_rect = QtCore.QRect(
                block.left(),
                icon_rect.bottom() + 2,
                block.width(),
                max(16, block.bottom() - icon_rect.bottom() - 2),
            )
            p.setPen(QtGui.QColor("#64748b"))
            icon_font = app_ui_font(point_size=14)
            p.setFont(icon_font)
            p.drawText(
                icon_rect,
                int(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter),
                "📊",
            )
            p.setPen(QtGui.QColor("#94a3b8"))
            p.setFont(app_ui_font(point_size=8))
            p.drawText(
                msg_rect,
                int(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop),
                "No throughput samples",
            )
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
            past = self._scrub_index >= 0 and i > self._scrub_index
            if past:
                color = "#1e3a5f"
            elif val == peak and val > 0:
                color = _CHART_BAR_HI
            else:
                color = _CHART_BAR
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


class MissionIntegrityHeatmap(QtWidgets.QWidget):
    """Horizontal continuity bar — green baseline with fault ticks + scrub playhead."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("missionIntegrityHeatmap")
        self._ticks: list[str] = []
        self._scrub_index = 0
        self.setMinimumHeight(52)
        self.setMaximumHeight(64)
        self.setFixedHeight(56)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

    def set_ticks(self, ticks: list[str]) -> None:
        self._ticks = list(ticks)
        if self._ticks:
            self._scrub_index = min(self._scrub_index, len(self._ticks) - 1)
        self.update()

    def set_scrub_index(self, index: int) -> None:
        if not self._ticks:
            self._scrub_index = 0
        else:
            self._scrub_index = max(0, min(int(index), len(self._ticks) - 1))
        self.update()

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(_CHART_BG))
        chart_rect = self.rect().adjusted(8, _CHART_TITLE_BAND + 2, -8, -10)

        p.setPen(QtGui.QColor(_CHART_TEXT))
        from ui.fonts import app_ui_font

        title_font = app_ui_font(point_size=9)
        title_font.setWeight(QtGui.QFont.Weight.DemiBold)
        p.setFont(title_font)
        p.drawText(8, 20, "Data integrity heatmap")

        if not self._ticks or chart_rect.width() <= 4:
            block_h = min(chart_rect.height(), 48)
            block_top = chart_rect.top() + max(0, (chart_rect.height() - block_h) // 2)
            block = QtCore.QRect(
                chart_rect.left(),
                block_top,
                chart_rect.width(),
                block_h,
            )
            icon_rect = QtCore.QRect(block.left(), block.top(), block.width(), 20)
            msg_rect = QtCore.QRect(
                block.left(),
                icon_rect.bottom() + 2,
                block.width(),
                max(14, block.bottom() - icon_rect.bottom() - 2),
            )
            p.setPen(QtGui.QColor("#64748b"))
            icon_font = app_ui_font(point_size=13)
            p.setFont(icon_font)
            p.drawText(
                icon_rect,
                int(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter),
                "🩺",
            )
            p.setPen(QtGui.QColor("#94a3b8"))
            p.setFont(app_ui_font(point_size=8))
            p.drawText(
                msg_rect,
                int(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop),
                "No health windows",
            )
            p.end()
            return

        p.fillRect(chart_rect, QtGui.QColor(_TICK_OK))
        n = len(self._ticks)
        cell_w = chart_rect.width() / n
        for i, tick in enumerate(self._ticks):
            cx = int(chart_rect.left() + (i + 0.5) * cell_w)
            if tick == "bad":
                p.setPen(QtGui.QPen(QtGui.QColor(_TICK_BAD), 3))
                p.drawLine(cx, chart_rect.top(), cx, chart_rect.bottom())
            elif tick == "warn":
                p.setPen(QtGui.QPen(QtGui.QColor(_TICK_WARN), 2))
                p.drawLine(cx, chart_rect.top() + 2, cx, chart_rect.bottom() - 2)

        play_x = int(chart_rect.left() + (self._scrub_index + 0.5) * cell_w)
        p.setPen(QtGui.QPen(QtGui.QColor("#38bdf8"), 2))
        p.drawLine(play_x, chart_rect.top() - 2, play_x, chart_rect.bottom() + 2)
        p.end()


def _split_human_bytes(n: int) -> tuple[str, str]:
    text = _human_bytes(n)
    if " " in text:
        val, unit = text.rsplit(" ", 1)
        return val, unit
    return text, ""


def _mission_summary_metric(
    label: str,
) -> tuple[QtWidgets.QWidget, QtWidgets.QLabel, QtWidgets.QLabel | None]:
    cell = QtWidgets.QWidget()
    cell.setObjectName("missionSummaryCell")
    lay = QtWidgets.QVBoxLayout(cell)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    val_row = QtWidgets.QHBoxLayout()
    val_row.setContentsMargins(0, 0, 0, 0)
    val_row.setSpacing(4)
    value_lbl = QtWidgets.QLabel("—")
    value_lbl.setObjectName("missionSummaryValue")
    unit_lbl = QtWidgets.QLabel("")
    unit_lbl.setObjectName("missionSummaryUnit")
    val_row.addWidget(value_lbl, 0)
    val_row.addWidget(unit_lbl, 0)
    val_row.addStretch(1)
    title_lbl = QtWidgets.QLabel(label.upper())
    title_lbl.setObjectName("missionSummaryLabel")
    lay.addLayout(val_row)
    lay.addWidget(title_lbl)
    return cell, value_lbl, unit_lbl


def _build_mission_summary_grid(win: BridgeLogicMixin) -> QtWidgets.QFrame:
    card = QtWidgets.QFrame()
    card.setObjectName("missionSummaryGrid")
    grid = QtWidgets.QGridLayout(card)
    grid.setContentsMargins(20, 18, 20, 18)
    grid.setHorizontalSpacing(18)
    grid.setVerticalSpacing(6)
    specs = (
        ("Safeguarded", "_mission_sum_safeguarded_val", "_mission_sum_safeguarded_unit"),
        ("Dropped", "_mission_sum_dropped_val", "_mission_sum_dropped_unit"),
        ("Duration", "_mission_sum_duration_val", "_mission_sum_duration_unit"),
        ("COM Hz", "_mission_sum_hz_val", "_mission_sum_hz_unit"),
        ("Depth", "_mission_sum_depth_val", "_mission_sum_depth_unit"),
        ("Depth Hz", "_mission_sum_depth_hz_val", "_mission_sum_depth_hz_unit"),
    )
    for col, (label, val_attr, unit_attr) in enumerate(specs):
        cell, val_lbl, unit_lbl = _mission_summary_metric(label)
        setattr(win, val_attr, val_lbl)
        setattr(win, unit_attr, unit_lbl)
        row = 0 if col < 4 else 1
        col_in_row = col if col < 4 else col - 4
        grid.addWidget(cell, row, col_in_row)
    for col in range(4):
        grid.setColumnStretch(col, 1)
    return card


def _update_mission_summary_grid(
    win: BridgeLogicMixin,
    *,
    safeguarded_bytes: int,
    dropped: int,
    duration_s: float,
    hz: float,
    depth_m: Optional[float] = None,
    depth_hz: float = 0.0,
    depth_enabled: bool = False,
    avg_depth_m: Optional[float] = None,
    depth_source: str = "",
) -> None:
    val = getattr(win, "_mission_sum_safeguarded_val", None)
    unit = getattr(win, "_mission_sum_safeguarded_unit", None)
    if val is not None:
        num, suffix = _split_human_bytes(safeguarded_bytes)
        val.setText(num)
        if unit is not None:
            unit.setText(suffix)
    val = getattr(win, "_mission_sum_dropped_val", None)
    unit = getattr(win, "_mission_sum_dropped_unit", None)
    if val is not None:
        val.setText(f"{dropped:,}")
        if unit is not None:
            unit.setText("pkts" if dropped != 1 else "pkt")
    from ui.mission_timeline import format_mission_duration_hms

    val = getattr(win, "_mission_sum_duration_val", None)
    unit = getattr(win, "_mission_sum_duration_unit", None)
    if val is not None:
        val.setText(format_mission_duration_hms(duration_s))
        if unit is not None:
            unit.setText("")
    val = getattr(win, "_mission_sum_hz_val", None)
    unit = getattr(win, "_mission_sum_hz_unit", None)
    if val is not None:
        val.setText(f"{hz:.1f}" if hz > 0 else "0.0")
        if unit is not None:
            unit.setText("Hz")
    val = getattr(win, "_mission_sum_depth_val", None)
    unit = getattr(win, "_mission_sum_depth_unit", None)
    if val is not None:
        if depth_enabled and depth_m is not None and depth_m > 0:
            val.setText(f"{depth_m:.2f}")
            if unit is not None:
                unit.setText("m")
            tip = "Latest non-zero depth from secondary COM"
            if avg_depth_m is not None and avg_depth_m > 0:
                tip += f" · session avg {avg_depth_m:.2f} m"
            if depth_source:
                tip += f" · {depth_source}"
            val.setToolTip(tip)
        elif depth_enabled:
            val.setText("—")
            if unit is not None:
                unit.setText("")
            val.setToolTip("Depth COM enabled but no soundings were muxed this session.")
        else:
            val.setText("—")
            if unit is not None:
                unit.setText("")
            val.setToolTip("Enable Depth sonar on secondary COM on the Control tab.")
    val = getattr(win, "_mission_sum_depth_hz_val", None)
    unit = getattr(win, "_mission_sum_depth_hz_unit", None)
    if val is not None:
        if depth_enabled:
            val.setText(f"{depth_hz:.1f}" if depth_hz > 0 else "0.0")
            if unit is not None:
                unit.setText("Hz")
        else:
            val.setText("—")
            if unit is not None:
                unit.setText("")


def _mission_chart_panel(child: QtWidgets.QWidget) -> QtWidgets.QFrame:
    box = QtWidgets.QFrame()
    box.setObjectName("missionChartPanel")
    lay = QtWidgets.QVBoxLayout(box)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(0)
    lay.addWidget(child)
    return box


def apply_mission_scrub(win: BridgeLogicMixin, bucket_index: int) -> None:
    record = getattr(win, "_mission_session_record", None)
    if record is None:
        return
    from ui.mission_timeline import (
        integrity_note_for_scrub,
        scrub_snapshot,
    )

    snap = scrub_snapshot(record, bucket_index)
    heatmap = getattr(win, "_mission_integrity_heatmap", None)
    if heatmap is not None:
        heatmap.set_scrub_index(snap.bucket_index)
    chart = getattr(win, "_mission_throughput_chart", None)
    if chart is not None:
        chart.set_scrub_index(snap.bucket_index)
    scrub_lbl = getattr(win, "_mission_scrub_time", None)
    if scrub_lbl is not None:
        scrub_lbl.setText(
            f"{snap.elapsed_label} / {snap.end_label} · "
            f"window {snap.bucket_index + 1}/{snap.bucket_count}"
        )
    at_end = snap.bucket_index >= snap.bucket_count - 1
    dropped = int(getattr(win, "_mission_session_summary", {}).get("dropped") or 0)
    _update_mission_summary_grid(
        win,
        safeguarded_bytes=record.total_bytes if at_end else snap.cumulative_bytes,
        dropped=dropped,
        duration_s=record.duration_s if at_end else snap.elapsed_s,
        hz=record.avg_hz_up,
        depth_m=record.last_depth_m,
        depth_hz=record.avg_depth_rate_hz or record.depth_rate_hz,
        depth_enabled=record.depth_enabled,
        avg_depth_m=record.avg_depth_m,
        depth_source=record.depth_source,
    )
    note = getattr(win, "_mission_integrity_note", None)
    if note is not None:
        text, color = integrity_note_for_scrub(record, snap)
        note.setText(text)
        note.setStyleSheet(f"color: {color};")


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

    lay.addWidget(_build_mission_summary_grid(win))

    charts_col = QtWidgets.QVBoxLayout()
    charts_col.setSpacing(10)
    win._mission_throughput_chart = ThroughputBarChart()
    charts_col.addWidget(_mission_chart_panel(win._mission_throughput_chart))

    timeline_box = QtWidgets.QFrame()
    timeline_box.setObjectName("missionTimelinePanel")
    tl = QtWidgets.QVBoxLayout(timeline_box)
    tl.setContentsMargins(0, 0, 0, 0)
    tl.setSpacing(6)
    win._mission_integrity_heatmap = MissionIntegrityHeatmap()
    tl.addWidget(win._mission_integrity_heatmap)
    scrub_row = QtWidgets.QHBoxLayout()
    scrub_row.setSpacing(8)
    win._mission_scrub_start = QtWidgets.QLabel("0:00")
    win._mission_scrub_start.setObjectName("missionScrubRuler")
    scrub_row.addWidget(win._mission_scrub_start, 0)
    win._mission_timeline_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
    win._mission_timeline_slider.setObjectName("missionTimelineSlider")
    win._mission_timeline_slider.setMinimum(0)
    win._mission_timeline_slider.setMaximum(0)
    win._mission_timeline_slider.setValue(0)
    win._mission_timeline_slider.setToolTip(
        "Scrub the session timeline — updates summary cards and charts for that moment."
    )
    scrub_row.addWidget(win._mission_timeline_slider, 1)
    win._mission_scrub_end = QtWidgets.QLabel("0:00")
    win._mission_scrub_end.setObjectName("missionScrubRuler")
    scrub_row.addWidget(win._mission_scrub_end, 0)
    tl.addLayout(scrub_row)
    win._mission_scrub_time = QtWidgets.QLabel("")
    win._mission_scrub_time.setObjectName("missionScrubCaption")
    tl.addWidget(win._mission_scrub_time)
    charts_col.addWidget(_mission_chart_panel(timeline_box))
    lay.addLayout(charts_col)

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

    export_box = QtWidgets.QFrame()
    export_box.setObjectName("missionQuickExportPanel")
    export_lay = QtWidgets.QVBoxLayout(export_box)
    export_lay.setContentsMargins(0, 0, 0, 0)
    export_lay.setSpacing(8)
    export_title = QtWidgets.QLabel("Quick export")
    export_title.setObjectName("modernToolsSectionTitle")
    export_lay.addWidget(export_title)
    export_hint = QtWidgets.QLabel(
        "Save the raw session backup for GIS, hydro, or survey-office handoff."
    )
    export_hint.setObjectName("tabNote")
    export_hint.setWordWrap(True)
    export_lay.addWidget(export_hint)
    export_btns = QtWidgets.QHBoxLayout()
    export_btns.setSpacing(10)
    win._mission_btn_export_txt = QtWidgets.QPushButton("Export to .TXT")
    win._mission_btn_export_txt.setObjectName("missionExportBtn")
    win._mission_btn_export_txt.setToolTip("Copy raw NMEA backup as plain text.")
    win._mission_btn_export_csv = QtWidgets.QPushButton("Export to .CSV")
    win._mission_btn_export_csv.setObjectName("missionExportBtn")
    win._mission_btn_export_csv.setToolTip("One row per NMEA sentence with type and raw line.")
    win._mission_btn_export_kml = QtWidgets.QPushButton("Export to .KML")
    win._mission_btn_export_kml.setObjectName("missionExportBtn")
    win._mission_btn_export_kml.setToolTip("Track line from GGA/RMC fixes for Google Earth / GIS.")
    for btn in (
        win._mission_btn_export_txt,
        win._mission_btn_export_csv,
        win._mission_btn_export_kml,
    ):
        export_btns.addWidget(btn, 1)
    export_lay.addLayout(export_btns)
    win._mission_btn_quick_export = QtWidgets.QPushButton("Save as .NMEA…")
    win._mission_btn_quick_export.setObjectName("missionExportBtnSecondary")
    win._mission_btn_quick_export.setToolTip(
        "Choose path and extension (.nmea, .log, .txt) for the raw backup file."
    )
    export_lay.addWidget(win._mission_btn_quick_export)
    lay.addWidget(export_box)

    if hasattr(win, "_on_mission_export_txt"):
        win._mission_btn_export_txt.clicked.connect(win._on_mission_export_txt)
    if hasattr(win, "_on_mission_export_csv"):
        win._mission_btn_export_csv.clicked.connect(win._on_mission_export_csv)
    if hasattr(win, "_on_mission_export_kml"):
        win._mission_btn_export_kml.clicked.connect(win._on_mission_export_kml)
    if hasattr(win, "_on_mission_quick_export"):
        win._mission_btn_quick_export.clicked.connect(win._on_mission_quick_export)
    win._mission_timeline_slider.valueChanged.connect(
        lambda v: apply_mission_scrub(win, int(v))
    )

    actions = QtWidgets.QHBoxLayout()
    actions.setSpacing(8)
    actions.addStretch(1)
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
    from ui.mission_summary import verify_backup_on_disk
    from ui.mission_timeline import (
        format_scrub_clock,
        timeline_bucket_count,
    )

    _disk, warn, detail = verify_backup_on_disk(summary)

    nbytes = int(summary.get("bytes") or summary.get("nbytes") or 0)
    dropped = int(summary.get("dropped") or summary.get("drops") or 0)
    path = str(summary.get("path") or record.backup_path or "").strip()
    _update_mission_summary_grid(
        win,
        safeguarded_bytes=nbytes,
        dropped=dropped,
        duration_s=record.duration_s,
        hz=record.avg_hz_up,
        depth_m=record.last_depth_m,
        depth_hz=record.avg_depth_rate_hz or record.depth_rate_hz,
        depth_enabled=record.depth_enabled,
        avg_depth_m=record.avg_depth_m,
        depth_source=record.depth_source,
    )
    val = getattr(win, "_mission_sum_safeguarded_val", None)
    if val is not None and path:
        val.setToolTip(path)

    transport_note = ""
    if record.com_active_s > 0 and record.duration_s > record.com_active_s + 5:
        from ui.transport_status import format_duration_s

        transport_note = (
            f"COM data active ~{format_duration_s(record.com_active_s)} "
            f"of {format_duration_s(record.duration_s)} running."
        )
    win._mission_throughput_chart.set_values(record.throughput_buckets)
    heatmap = getattr(win, "_mission_integrity_heatmap", None)
    if heatmap is not None:
        heatmap.set_ticks(record.health_ticks)
    slider = getattr(win, "_mission_timeline_slider", None)
    bucket_n = timeline_bucket_count(record)
    if slider is not None:
        slider.blockSignals(True)
        slider.setMaximum(max(0, bucket_n - 1))
        slider.setValue(max(0, bucket_n - 1))
        slider.blockSignals(False)
    start_lbl = getattr(win, "_mission_scrub_start", None)
    end_lbl = getattr(win, "_mission_scrub_end", None)
    if start_lbl is not None:
        start_lbl.setText("0:00")
    if end_lbl is not None:
        end_lbl.setText(format_scrub_clock(record.duration_s))

    if warn:
        note_text = (
            f"Integrity warning: {detail}\n"
            "Scrub the timeline to inspect fault windows before export."
        )
        if transport_note:
            note_text = f"{transport_note}\n\n{note_text}"
        win._mission_integrity_note.setText(note_text)
        win._mission_integrity_note.setStyleSheet("color: #fbbf24;")
    elif transport_note:
        win._mission_integrity_note.setText(transport_note)
        win._mission_integrity_note.setStyleSheet("color: #94a3b8;")
    apply_mission_scrub(win, max(0, bucket_n - 1))

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

"""Lightweight Control-tab position track (Qt paint, GGA/RMC only)."""
from __future__ import annotations

import math
import time
from typing import Callable, Optional, Sequence

TrackPoint = tuple[float, float, float]  # mono_time, lat, lon

from PySide6 import QtCore, QtGui, QtWidgets

TRACK_MAX = 120
_DEFAULT_PAD_DEG = 0.00015
_GRID_DIVISIONS = 4
_METERS_PER_DEG_LAT = 111_320.0
_GRID_SNAP_INTERVALS_M = (1, 2, 5, 10, 25, 50, 100, 250, 500)
_MAX_GRID_LINES_PER_AXIS = 12
_ROLLING_WINDOW_S = 5.0
_VELOCITY_CELL_SECONDS = 1.5


def position_fix_color_hex(
    *,
    stale: bool,
    stream_idle: bool,
    quality: Optional[int],
) -> str:
    """Match web dashboard `positionFixColor` for fix-quality dots."""
    if stale or stream_idle:
        return "#f87171"
    if quality in (4, 5):
        return "#4ade80"
    if quality in (1, 2):
        return "#60a5fa"
    return "#fbbf24"


def _float_or_none(value: object, *, is_lat: bool) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if is_lat and not (-90.0 <= out <= 90.0):
        return None
    if not is_lat and not (-180.0 <= out <= 180.0):
        return None
    return out


def latlon_bounds(
    points: Sequence[tuple[float, float]],
    *,
    pad_deg: float = _DEFAULT_PAD_DEG,
) -> Optional[tuple[float, float, float, float]]:
    """Return (min_lon, max_lon, min_lat, max_lat) with padding."""
    if not points:
        return None
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    if abs(max_lat - min_lat) < 1e-9:
        min_lat -= pad_deg
        max_lat += pad_deg
    if abs(max_lon - min_lon) < 1e-9:
        min_lon -= pad_deg
        max_lon += pad_deg
    pad_lat = max(pad_deg, (max_lat - min_lat) * 0.08)
    pad_lon = max(pad_deg, (max_lon - min_lon) * 0.08)
    return (
        min_lon - pad_lon,
        max_lon + pad_lon,
        min_lat - pad_lat,
        max_lat + pad_lat,
    )


def project_latlon(
    lat: float,
    lon: float,
    bounds: tuple[float, float, float, float],
    width: int,
    height: int,
    *,
    margin: int = 12,
) -> tuple[float, float]:
    min_lon, max_lon, min_lat, max_lat = bounds
    inner_w = max(1, width - margin * 2)
    inner_h = max(1, height - margin * 2)
    lon_span = max(max_lon - min_lon, 1e-12)
    lat_span = max(max_lat - min_lat, 1e-12)
    x = margin + ((lon - min_lon) / lon_span) * inner_w
    y = margin + ((max_lat - lat) / lat_span) * inner_h
    return x, y


def _bounds_span_meters(
    bounds: tuple[float, float, float, float],
) -> tuple[float, float, float]:
    """Return (lat_mid, lat_span_m, lon_span_m) for the plot bounds."""
    min_lon, max_lon, min_lat, max_lat = bounds
    lat_mid = (min_lat + max_lat) * 0.5
    lat_span_m = (max_lat - min_lat) * _METERS_PER_DEG_LAT
    lon_span_m = (
        (max_lon - min_lon)
        * _METERS_PER_DEG_LAT
        * max(0.15, math.cos(math.radians(lat_mid)))
    )
    return lat_mid, lat_span_m, lon_span_m


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ground distance in meters between two WGS84 points."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(d_lon / 2) ** 2
    )
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def prune_track_points(
    points: list[TrackPoint],
    *,
    window_s: float = _ROLLING_WINDOW_S,
    now_mono: Optional[float] = None,
) -> list[TrackPoint]:
    """Drop samples older than the rolling window (in-place)."""
    if not points:
        return points
    now = time.monotonic() if now_mono is None else now_mono
    cutoff = now - window_s
    while points and points[0][0] < cutoff:
        points.pop(0)
    return points


def track_points_in_window(
    points: Sequence[TrackPoint],
    *,
    window_s: float = _ROLLING_WINDOW_S,
    now_mono: Optional[float] = None,
) -> list[TrackPoint]:
    """Return track samples from the rolling time window only."""
    if not points:
        return []
    now = time.monotonic() if now_mono is None else now_mono
    cutoff = now - window_s
    return [p for p in points if p[0] >= cutoff]


def track_average_velocity_mps(
    points: Sequence[TrackPoint],
    *,
    window_s: float = _ROLLING_WINDOW_S,
    now_mono: Optional[float] = None,
) -> float:
    """Average ground speed (m/s) across the rolling track window."""
    windowed = track_points_in_window(
        points, window_s=window_s, now_mono=now_mono
    )
    if len(windowed) < 2:
        return 0.0
    dist_m = 0.0
    for idx in range(1, len(windowed)):
        _, lat0, lon0 = windowed[idx - 1]
        _, lat1, lon1 = windowed[idx]
        dist_m += _haversine_meters(lat0, lon0, lat1, lon1)
    dt = windowed[-1][0] - windowed[0][0]
    if dt <= 1e-6:
        return 0.0
    return dist_m / dt


def footprint_span_meters(points: Sequence[tuple[float, float]]) -> float:
    """Largest ground span (m) across a lat/lon point set."""
    bounds = latlon_bounds(points)
    if bounds is None:
        return 1.0
    _, lat_span_m, lon_span_m = _bounds_span_meters(bounds)
    return max(lat_span_m, lon_span_m, 1.0)


def _snap_interval(raw_m: float) -> int:
    raw = max(0.5, raw_m)
    return min(_GRID_SNAP_INTERVALS_M, key=lambda v: abs(v - raw))


def snap_grid_interval_meters(bounds: tuple[float, float, float, float]) -> int:
    """Snap grid cell size from static plot bounds (fallback when no track)."""
    _, lat_span_m, lon_span_m = _bounds_span_meters(bounds)
    raw = max(
        0.5,
        (lat_span_m / _GRID_DIVISIONS + lon_span_m / _GRID_DIVISIONS) * 0.5,
    )
    return _snap_interval(raw)


def dynamic_grid_interval_meters(
    track: Sequence[TrackPoint],
    bounds: tuple[float, float, float, float],
    *,
    window_s: float = _ROLLING_WINDOW_S,
    now_mono: Optional[float] = None,
) -> int:
    """Snap grid spacing from rolling velocity + active work-area footprint."""
    windowed = track_points_in_window(
        track, window_s=window_s, now_mono=now_mono
    )
    coords = [(lat, lon) for _t, lat, lon in windowed]
    footprint_m = footprint_span_meters(coords) if coords else 1.0
    velocity_mps = track_average_velocity_mps(
        track, window_s=window_s, now_mono=now_mono
    )
    static_raw = snap_grid_interval_meters(bounds)
    raw = max(
        footprint_m / _GRID_DIVISIONS,
        velocity_mps * _VELOCITY_CELL_SECONDS,
        float(static_raw) * 0.35,
        0.5,
    )
    return _snap_interval(raw)


def _grid_steps_deg(
    bounds: tuple[float, float, float, float],
    interval_m: int,
) -> tuple[float, float]:
    """Ground interval in degrees (lat step, lon step at plot mid-latitude)."""
    lat_mid, _, _ = _bounds_span_meters(bounds)
    lat_step = interval_m / _METERS_PER_DEG_LAT
    lon_step = interval_m / (
        _METERS_PER_DEG_LAT * max(0.15, math.cos(math.radians(lat_mid)))
    )
    return lat_step, lon_step


def grid_cell_scale_label(
    bounds: tuple[float, float, float, float],
    track: Sequence[TrackPoint] | None = None,
    *,
    now_mono: Optional[float] = None,
) -> str:
    """Human-readable snapped grid spacing for the position track."""
    if track:
        interval_m = dynamic_grid_interval_meters(
            track, bounds, now_mono=now_mono
        )
    else:
        interval_m = snap_grid_interval_meters(bounds)
    return f"Grid: {interval_m} m"


class ControlPositionMap(QtWidgets.QWidget):
    """Simple lat/lon track plot for Modern Control (no tile server)."""

    clear_requested = QtCore.Signal()
    open_full_map_requested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modernControlMap")
        self.setMinimumHeight(120)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self._track: list[TrackPoint] = []
        self._marker: tuple[float, float] | None = None
        self._stale = False
        self._stream_idle = False
        self._quality: Optional[int] = None
        self._source = ""
        self._fix_label = ""
        self._idle = True
        self._message = "Start bridge for live position"
        self.setToolTip("Double-click to open full map in browser (street/satellite).")

    def clear_track(self) -> None:
        self._track.clear()
        self.update()

    def clear_session(self) -> None:
        self._track.clear()
        self._marker = None
        self._stale = False
        self._stream_idle = False
        self._quality = None
        self._source = ""
        self._fix_label = ""
        self._idle = True
        self._message = "Stopped — map updates when bridge runs"
        self.update()

    def set_session_idle(self, message: str) -> None:
        self._marker = None
        self._idle = True
        self._message = message.strip() or "Waiting for position"
        self.update()

    def update_position(
        self,
        *,
        lat: Optional[float],
        lon: Optional[float],
        stale: bool = False,
        stream_idle: bool = False,
        quality: Optional[int] = None,
        source: str = "",
        fix_label: str = "",
    ) -> None:
        lat_f = _float_or_none(lat, is_lat=True)
        lon_f = _float_or_none(lon, is_lat=False)
        self._stale = bool(stale)
        self._stream_idle = bool(stream_idle)
        self._quality = quality if isinstance(quality, int) else None
        self._source = source.strip().upper()
        self._fix_label = fix_label.strip()

        if lat_f is None or lon_f is None:
            self._marker = None
            self._idle = True
            if stream_idle or stale:
                self._message = "No GGA/RMC fix — waiting for NMEA"
            else:
                self._message = "Waiting for GGA/RMC position"
            self.update()
            return

        self._idle = False
        self._marker = (lat_f, lon_f)
        now = time.monotonic()
        last = self._track[-1] if self._track else None
        if (
            last is None
            or abs(last[1] - lat_f) > 1e-7
            or abs(last[2] - lon_f) > 1e-7
        ):
            self._track.append((now, lat_f, lon_f))
            prune_track_points(self._track, now_mono=now)
            if len(self._track) > TRACK_MAX:
                self._track = self._track[-TRACK_MAX:]
        self.update()

    def _active_track(self, now_mono: Optional[float] = None) -> list[TrackPoint]:
        """Rolling 5 s subset used for paint, bounds, velocity, and grid."""
        now = time.monotonic() if now_mono is None else now_mono
        prune_track_points(self._track, now_mono=now)
        return track_points_in_window(self._track, now_mono=now)

    def _caption_text(self) -> str:
        if self._marker is None:
            return ""
        lat, lon = self._marker
        parts = [f"{lat:.5f}, {lon:.5f}"]
        if self._source:
            parts.append(self._source)
        if self._fix_label and self._fix_label.lower() != "no data stream":
            parts.append(self._fix_label)
        if self._stale or self._stream_idle:
            parts.append("stale")
        return " · ".join(parts)

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        painter.fillRect(rect, QtGui.QColor("#0f172a"))

        if self._idle:
            painter.setPen(QtGui.QColor("#64748b"))
            icon_font = painter.font()
            icon_font.setPointSizeF(28.0)
            painter.setFont(icon_font)
            painter.drawText(
                rect.adjusted(12, 0, -12, -28),
                int(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter),
                "🗺",
            )
            painter.setPen(QtGui.QColor("#94a3b8"))
            msg_font = painter.font()
            msg_font.setPointSizeF(max(9.0, msg_font.pointSizeF()))
            painter.setFont(msg_font)
            painter.drawText(
                rect.adjusted(12, 0, -12, 0),
                int(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter),
                self._message,
            )
            painter.end()
            return

        now = time.monotonic()
        active = self._active_track(now_mono=now)
        points: list[tuple[float, float]] = [
            (lat, lon) for _t, lat, lon in active
        ]
        if self._marker and (
            not points
            or points[-1][0] != self._marker[0]
            or points[-1][1] != self._marker[1]
        ):
            points = points + [self._marker]

        bounds = latlon_bounds(points)
        if bounds is None:
            painter.end()
            return

        self._paint_grid(painter, rect, bounds, active, now_mono=now)
        scale = grid_cell_scale_label(bounds, active, now_mono=now)
        painter.setPen(QtGui.QColor("#94a3b8"))
        scale_font = painter.font()
        scale_font.setPointSizeF(7.5)
        painter.setFont(scale_font)
        painter.drawText(
            rect.adjusted(10, 0, -10, -10),
            int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignBottom),
            scale,
        )

        if len(points) >= 2:
            path = QtGui.QPainterPath()
            first = True
            for lat, lon in points:
                x, y = project_latlon(
                    lat, lon, bounds, rect.width(), rect.height()
                )
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)
            pen = QtGui.QPen(QtGui.QColor(96, 165, 250, 170))
            pen.setWidthF(2.0)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)

        if self._marker is not None:
            lat, lon = self._marker
            x, y = project_latlon(lat, lon, bounds, rect.width(), rect.height())
            color = QtGui.QColor(
                position_fix_color_hex(
                    stale=self._stale,
                    stream_idle=self._stream_idle,
                    quality=self._quality,
                )
            )
            fill_alpha = 115 if (self._stale or self._stream_idle) else 230
            color.setAlpha(fill_alpha)
            border = QtGui.QColor("#8b93a8" if (self._stale or self._stream_idle) else "#e2e8f0")
            painter.setPen(QtGui.QPen(border, 2))
            painter.setBrush(color)
            painter.drawEllipse(QtCore.QPointF(x, y), 7.0, 7.0)

        caption = self._caption_text()
        if caption:
            font = painter.font()
            font.setPointSizeF(max(8.0, font.pointSizeF() - 0.5))
            painter.setFont(font)
            metrics = painter.fontMetrics()
            text_w = metrics.horizontalAdvance(caption)
            text_h = metrics.height()
            pad_x, pad_y = 10, 5
            pill_w = text_w + pad_x * 2
            pill_h = text_h + pad_y * 2
            margin = 12
            pill_x = margin
            pill_y = rect.height() - margin - pill_h
            pill_rect = QtCore.QRectF(pill_x, pill_y, pill_w, pill_h)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(15, 23, 42, 210))
            painter.drawRoundedRect(pill_rect, 6.0, 6.0)
            painter.setPen(QtGui.QColor("#e2e8f0"))
            painter.drawText(
                pill_rect,
                int(QtCore.Qt.AlignmentFlag.AlignCenter),
                caption,
            )
        painter.end()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.open_full_map_requested.emit()
        super().mouseDoubleClickEvent(event)

    def _paint_grid(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
        bounds: tuple[float, float, float, float],
        track: Sequence[TrackPoint],
        *,
        now_mono: Optional[float] = None,
    ) -> None:
        min_lon, max_lon, min_lat, max_lat = bounds
        interval_m = dynamic_grid_interval_meters(
            track, bounds, now_mono=now_mono
        )
        lat_step, lon_step = _grid_steps_deg(bounds, interval_m)
        grid_pen = QtGui.QPen(QtGui.QColor(30, 41, 59))
        grid_pen.setWidthF(1.0)
        painter.setPen(grid_pen)

        plot_left = rect.left() + 8
        plot_right = rect.right() - 8
        plot_top = rect.top() + 8
        plot_bottom = rect.bottom() - 8

        lat = min_lat + lat_step
        lat_lines = 0
        while lat < max_lat - 1e-12 and lat_lines < _MAX_GRID_LINES_PER_AXIS:
            _, y = project_latlon(
                lat, min_lon, bounds, rect.width(), rect.height()
            )
            yi = int(max(plot_top, min(plot_bottom, y)))
            painter.drawLine(plot_left, yi, plot_right, yi)
            lat += lat_step
            lat_lines += 1

        lon = min_lon + lon_step
        lon_lines = 0
        while lon < max_lon - 1e-12 and lon_lines < _MAX_GRID_LINES_PER_AXIS:
            x, _ = project_latlon(
                min_lat, lon, bounds, rect.width(), rect.height()
            )
            xi = int(max(plot_left, min(plot_right, x)))
            painter.drawLine(xi, plot_top, xi, plot_bottom)
            lon += lon_step
            lon_lines += 1

        # North hint — lat increases upward on the plot.
        painter.setPen(QtGui.QColor("#64748b"))
        font = painter.font()
        font.setPointSizeF(7.5)
        painter.setFont(font)
        painter.drawText(
            rect.adjusted(10, 6, -10, -6),
            int(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignRight),
            "N ↑",
        )


def build_control_map_panel(
    parent: QtWidgets.QWidget,
    *,
    on_layout_change: Optional[Callable[[bool], None]] = None,
) -> tuple[QtWidgets.QWidget, ControlPositionMap]:
    """Map card for Modern Control tab — collapsible accordion, with hybrid full-map button."""
    from ui.ui_prefs import load_modern_layout_prefs, save_modern_layout_prefs

    card = QtWidgets.QFrame()
    card.setObjectName("modernControlMapCard")
    lay = QtWidgets.QVBoxLayout(card)
    lay.setContentsMargins(12, 8, 12, 10)
    lay.setSpacing(4)

    # ── Header row — acts as the section disclosure row ────────────────────
    # The entire header strip is clickable to toggle the panel.
    header_widget = QtWidgets.QFrame()
    header_widget.setObjectName("modernControlMapHeader")
    header_widget.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    header_lay = QtWidgets.QHBoxLayout(header_widget)
    header_lay.setContentsMargins(0, 0, 0, 0)
    header_lay.setSpacing(6)

    title = QtWidgets.QLabel("Position track")
    title.setObjectName("modernControlMapTitle")
    title.setToolTip(
        "GGA/RMC track — click anywhere on this bar to expand/collapse."
    )
    title.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    # Action buttons — only shown when expanded
    btn_open = QtWidgets.QPushButton("Open full map")
    btn_open.setObjectName("modernToolsPrimaryBtn")
    btn_open.setToolTip("Open local Web dashboard with Position map on (needs Web API).")
    btn_open.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    btn_clear = QtWidgets.QPushButton("Clear")
    btn_clear.setObjectName("modernToolsSecondaryBtn")
    btn_clear.setToolTip("Clear the on-screen track (does not affect logs).")
    btn_clear.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    # Disclosure chevron — right-aligned
    btn_collapse = QtWidgets.QToolButton()
    btn_collapse.setObjectName("modernControlMapCollapseBtn")
    btn_collapse.setAutoRaise(True)
    btn_collapse.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    btn_collapse.setFixedSize(22, 22)
    btn_collapse.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    header_lay.addWidget(title, 1)
    header_lay.addWidget(btn_open, 0)
    header_lay.addWidget(btn_clear, 0)
    header_lay.addWidget(btn_collapse, 0)
    lay.addWidget(header_widget)

    # ── Body (hidden when collapsed) ──────────────────────────────────────
    body = QtWidgets.QWidget()
    body.setObjectName("modernControlMapBody")
    body_lay = QtWidgets.QVBoxLayout(body)
    body_lay.setContentsMargins(0, 4, 0, 0)
    body_lay.setSpacing(4)

    widget = ControlPositionMap(parent)
    body_lay.addWidget(widget, 1)
    lay.addWidget(body, 1)

    # ── Collapse state management ─────────────────────────────────────────
    _collapsed: list[bool] = [bool(load_modern_layout_prefs().get("control_map_collapsed", False))]

    def _apply_collapsed(collapsed: bool, *, save: bool = True) -> None:
        _collapsed[0] = collapsed
        body.setVisible(not collapsed)
        # Action buttons disappear when collapsed — clean minimal header
        btn_open.setVisible(not collapsed)
        btn_clear.setVisible(not collapsed)
        # ▸ = closed (expand me), ▾ = open (collapse me)
        btn_collapse.setText("▸" if collapsed else "▾")
        btn_collapse.setToolTip(
            "Expand position track" if collapsed else "Collapse position track"
        )
        if collapsed:
            card.setMaximumHeight(48)
            card.setMinimumHeight(0)
            body.setMinimumHeight(0)
            card.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
        else:
            card.setMaximumHeight(16777215)
            card.setMinimumHeight(160)
            body.setMinimumHeight(120)
            card.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Expanding,
            )
        if on_layout_change is not None:
            on_layout_change(collapsed)
        if save:
            payload = load_modern_layout_prefs()
            save_modern_layout_prefs(
                hsplit=payload.get("hsplit"),
                left_vsplit=payload.get("left_vsplit"),
                right_vsplit=payload.get("right_vsplit"),
                slot_assignments=payload.get("slot_assignments"),
                sidebar_collapsed=payload.get("sidebar_collapsed"),
                control_map_collapsed=collapsed,
            )

    def _toggle() -> None:
        _apply_collapsed(not _collapsed[0])

    btn_collapse.clicked.connect(_toggle)

    def _click_on_action_button(local_pos: QtCore.QPoint) -> bool:
        for btn in (btn_open, btn_clear, btn_collapse):
            if btn.isVisible() and btn.geometry().contains(local_pos):
                return True
        return False

    # Whole header row toggles — title + frame, not just the chevron.
    class _HeaderFilter(QtCore.QObject):
        def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
            if obj not in (header_widget, title):
                return False
            if event.type() != QtCore.QEvent.Type.MouseButtonRelease:
                return False
            mouse = event  # type: ignore[assignment]
            if mouse.button() != QtCore.Qt.MouseButton.LeftButton:
                return False
            local = header_widget.mapFromGlobal(mouse.globalPosition().toPoint())
            if _click_on_action_button(local):
                return False
            _toggle()
            return True

    _hf = _HeaderFilter(card)
    header_widget.installEventFilter(_hf)
    title.installEventFilter(_hf)
    header_widget.setProperty("_header_filter", _hf)  # keep alive

    _apply_collapsed(_collapsed[0], save=False)

    btn_clear.clicked.connect(widget.clear_track)
    widget.clear_session()
    opener = getattr(parent, "_on_web_open_dashboard_map", None)
    if callable(opener):
        btn_open.clicked.connect(opener)
        widget.open_full_map_requested.connect(opener)
    return card, widget

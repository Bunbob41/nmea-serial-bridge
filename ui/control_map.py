"""Lightweight Control-tab position track (Qt paint, GGA/RMC only)."""
from __future__ import annotations

from typing import Callable, Optional, Sequence

from PySide6 import QtCore, QtGui, QtWidgets

TRACK_MAX = 120
_DEFAULT_PAD_DEG = 0.00015


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
        self._track: list[tuple[float, float]] = []
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
        last = self._track[-1] if self._track else None
        if (
            last is None
            or abs(last[0] - lat_f) > 1e-7
            or abs(last[1] - lon_f) > 1e-7
        ):
            self._track.append((lat_f, lon_f))
            if len(self._track) > TRACK_MAX:
                self._track = self._track[-TRACK_MAX:]
        self.update()

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
            painter.setPen(QtGui.QColor("#94a3b8"))
            painter.drawText(
                rect.adjusted(12, 0, -12, 0),
                int(QtCore.Qt.AlignmentFlag.AlignCenter),
                self._message,
            )
            painter.end()
            return

        points: list[tuple[float, float]] = list(self._track)
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

        self._paint_grid(painter, rect, bounds)

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
            painter.setPen(QtGui.QColor("#cbd5e1"))
            font = painter.font()
            font.setPointSizeF(max(8.0, font.pointSizeF() - 0.5))
            painter.setFont(font)
            painter.drawText(
                rect.adjusted(12, 0, -12, -8),
                int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignBottom),
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
    ) -> None:
        min_lon, max_lon, min_lat, max_lat = bounds
        grid_pen = QtGui.QPen(QtGui.QColor(30, 41, 59))
        grid_pen.setWidthF(1.0)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = rect.top() + (rect.height() * i) / 4
            painter.drawLine(rect.left() + 8, int(y), rect.right() - 8, int(y))
        for i in range(1, 4):
            x = rect.left() + (rect.width() * i) / 4
            painter.drawLine(int(x), rect.top() + 8, int(x), rect.bottom() - 8)

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
        "GGA/RMC track — tap to expand/collapse. Open full map for browser satellite view."
    )

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
    _collapsed: list[bool] = [bool(load_modern_layout_prefs().get("control_map_collapsed", True))]

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
            card.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
        else:
            card.setMaximumHeight(16777215)
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

    # Make the whole header row clickable — but don't steal button clicks
    class _HeaderFilter(QtCore.QObject):
        def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
            if (
                event.type() == QtCore.QEvent.Type.MouseButtonRelease
                and obj is header_widget
            ):
                mouse = event  # type: ignore[assignment]
                if not btn_open.geometry().contains(mouse.pos()) and not btn_clear.geometry().contains(mouse.pos()) and not btn_collapse.geometry().contains(mouse.pos()):  # type: ignore[union-attr]
                    _toggle()
                    return True
            return False

    _hf = _HeaderFilter(card)
    header_widget.installEventFilter(_hf)
    header_widget.setProperty("_header_filter", _hf)  # keep alive

    _apply_collapsed(_collapsed[0], save=False)

    btn_clear.clicked.connect(widget.clear_track)
    opener = getattr(parent, "_on_web_open_dashboard_map", None)
    if callable(opener):
        btn_open.clicked.connect(opener)
        widget.open_full_map_requested.connect(opener)
    return card, widget

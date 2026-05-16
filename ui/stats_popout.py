"""Detachable survey HUD — collapsible sections, pick metrics, saved layout."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.stats_line import _fmt_k
from ui.styles import hud_stylesheet
from ui.theme_choice import THEME_MAROON_CLASSIC, THEME_MAROON_HC
from ui.survey_hud_layout import (
    METRIC_IDS,
    METRIC_LABELS,
    METRIC_SECTION,
    SECTION_IDS,
    SECTION_LABELS,
    default_layout,
    load_layout,
    normalized_section_order,
    save_layout,
)

_TT_HZ_DOWN = (
    "Sentences per second from the network (UDP/TCP) toward the serial port "
    "(rolling 1 second). Assembled NMEA toward the autopilot COM—not raw UDP packets."
)
_TT_HZ_UP = (
    "Sentences per second from the serial port toward the network "
    "(device answering on COM)."
)
_TT_HZ_INJ = (
    "Send-tab inject rate toward COM only (rolling 1 second). "
    "Does not add to Into COM above."
)
_TT_SESS_DOWN = "Total complete sentences forwarded network → serial this session."
_TT_SESS_UP = "Total complete sentences forwarded serial → network this session."
_TT_TRANSPORT = (
    "OK when there are no queue drops, no line rejects, and both queues are empty. "
    "Warn when any backpressure counter is non-zero."
)
_TT_DROP_NS = "Lines dropped because the network→serial queue was full."
_TT_DROP_SN = "Lines dropped because the serial→network queue was full."
_TT_REJ_NS = "Lines rejected toward COM (assembler or strict NMEA filter)."
_TT_REJ_SN = "Lines rejected from COM toward the network."
_TT_Q_NS = "Chunks waiting to be written to the serial port."
_TT_Q_SN = "Chunks waiting to be sent on the network."
_TT_SERIAL = "Serial port state for this bridge session."
_TT_NETWORK = "Network listen / connect state for this bridge session."
_TT_PIN = "Keep this HUD above other windows while you use Hypack / browser / charts."
_TT_DRAG_ORDER = (
    "Drag from the grip (\u22ee), then release on another group's grip to swap section order (saved)."
)
_TT_ROW = "Lay out section groups in one horizontal row (works with panels expanded)."
_TT_COLLAPSE = "Click to show or hide this group (saved for next time)."
_TT_CUSTOMIZE = "Choose which groups and metrics appear on this HUD."
_TT_SCALE = "Scale all stat tiles up/down to better use available space."
_TT_COLS = "Force metric columns (Auto keeps responsive behavior)."
_TT_SUB = "Show or hide subtitle lines on metric tiles."
_TT_LOG = "Show live NMEA log panel on the right side."
_TT_LOCK = "Lock HUD size (disable edge/corner resize) until unchecked."
_TT_THEME = "Cycle HUD/app theme."
_TT_CORNER = "One-click corner profile: 60%, 6 cols, Sub off, Row on."
_TT_READABLE = "One-click readable profile: 90%, Auto cols, Sub on, Row off."


class _HudResizeEdge(QtWidgets.QWidget):
    """Invisible frameless-window resize hit target (edges + corners).

    Role uses letters: N S E W in combinations, e.g. \"nw\", \"e\", \"se\".
    """

    def __init__(self, window: QtWidgets.QWidget, role: str) -> None:
        super().__init__(window)
        self._win = window
        self._role = role.upper()
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_MouseNoMask, False)
        self.raise_()
        cmap = {
            "N": QtCore.Qt.CursorShape.SizeVerCursor,
            "S": QtCore.Qt.CursorShape.SizeVerCursor,
            "E": QtCore.Qt.CursorShape.SizeHorCursor,
            "W": QtCore.Qt.CursorShape.SizeHorCursor,
            "NW": QtCore.Qt.CursorShape.SizeFDiagCursor,
            "NE": QtCore.Qt.CursorShape.SizeBDiagCursor,
            "SW": QtCore.Qt.CursorShape.SizeBDiagCursor,
            "SE": QtCore.Qt.CursorShape.SizeFDiagCursor,
        }
        self._cursor = cmap.get(self._role, QtCore.Qt.CursorShape.ArrowCursor)
        self.setCursor(QtGui.QCursor(self._cursor))
        self.setStyleSheet("background:transparent;")

        self._press_global: QtCore.QPoint | None = None
        self._geom0 = QtCore.QRect()
        self._grabbed = False
        self._guard_timer = QtCore.QTimer(self)
        self._guard_timer.setInterval(120)
        self._guard_timer.timeout.connect(self._guard_drag_state)

    def _guard_drag_state(self) -> None:
        if self._press_global is None:
            return
        if not (QtWidgets.QApplication.mouseButtons() & QtCore.Qt.MouseButton.LeftButton):
            self._end_resize_session()

    def _end_resize_session(self) -> None:
        self._press_global = None
        setattr(self._win, "_interactive_resize_active", False)
        self._guard_timer.stop()
        if self._grabbed:
            try:
                self.releaseMouse()
            except Exception:
                pass
            self._grabbed = False
        if hasattr(self._win, "_schedule_layout_reflow"):
            try:
                self._win._schedule_layout_reflow()  # type: ignore[attr-defined]
            except Exception:
                pass

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if (
            event.button() == QtCore.Qt.MouseButton.LeftButton
            and not self._win.isMaximized()
            and not self._win.isFullScreen()
        ):
            self._press_global = event.globalPosition().toPoint()
            self._geom0 = self._win.geometry()
            setattr(self._win, "_interactive_resize_active", True)
            self.grabMouse()
            self._grabbed = True
            self._guard_timer.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._end_resize_session()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._press_global is not None and not (
            event.buttons() & QtCore.Qt.MouseButton.LeftButton
        ):
            # Defensive cleanup if release was delivered elsewhere.
            self._end_resize_session()
            super().mouseMoveEvent(event)
            return
        if (
            self._press_global is None
            or not (event.buttons() & QtCore.Qt.MouseButton.LeftButton)
            or self._win.isMaximized()
        ):
            super().mouseMoveEvent(event)
            return

        d = event.globalPosition().toPoint() - self._press_global
        g = QtCore.QRect(self._geom0)
        r = self._role
        mw = self._win.minimumWidth()
        mh = self._win.minimumHeight()

        if "W" in r:
            g.setLeft(g.left() + d.x())
        if "E" in r:
            g.setRight(g.right() + d.x())
        if "N" in r:
            g.setTop(g.top() + d.y())
        if "S" in r:
            g.setBottom(g.bottom() + d.y())

        if g.width() < mw:
            if "W" in r:
                g.setLeft(g.right() - mw + 1)
            else:
                g.setRight(g.left() + mw - 1)
        if g.height() < mh:
            if "N" in r:
                g.setTop(g.bottom() - mh + 1)
            else:
                g.setBottom(g.top() + mh - 1)

        self._win.setGeometry(g)
        super().mouseMoveEvent(event)


class _HudChromeBar(QtWidgets.QWidget):
    """One-pixel-tall draggable strip replacing the OS title bar (frameless HUD)."""

    def __init__(
        self,
        hud: QtWidgets.QWidget,
        *,
        layout_btn: QtWidgets.QAbstractButton,
        theme_btn: QtWidgets.QAbstractButton,
        corner_btn: QtWidgets.QAbstractButton,
        readable_btn: QtWidgets.QAbstractButton,
        row_cb: QtWidgets.QCheckBox,
        pin_cb: QtWidgets.QCheckBox,
        sub_cb: QtWidgets.QCheckBox,
        log_cb: QtWidgets.QCheckBox,
        lock_cb: QtWidgets.QCheckBox,
        scale_box: QtWidgets.QWidget,
        cols_box: QtWidgets.QWidget,
    ) -> None:
        super().__init__(hud)
        self._hud = hud
        self._drag: Optional[QtCore.QPoint] = None

        self.setObjectName("surveyHudChromeBar")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        fm = QtGui.QFontMetrics(self.font())
        self.setFixedHeight(max(18, fm.height() + 3))

        hl = QtWidgets.QHBoxLayout(self)
        hl.setContentsMargins(2, 0, 2, 0)
        hl.setSpacing(2)

        self._title = QtWidgets.QLabel("Live bridge")
        self._title.setObjectName("surveyHudWindowTitle")
        hl.addWidget(self._title)
        hl.addStretch(1)
        hl.addWidget(layout_btn)
        hl.addWidget(theme_btn)
        hl.addWidget(corner_btn)
        hl.addWidget(readable_btn)
        hl.addWidget(scale_box)
        hl.addWidget(cols_box)
        hl.addWidget(sub_cb)
        hl.addWidget(log_cb)
        hl.addWidget(lock_cb)
        hl.addWidget(row_cb)
        hl.addWidget(pin_cb)

        def _mk_cap(icon: str, tip: str, fn: Callable[..., None]) -> QtWidgets.QToolButton:
            b = QtWidgets.QToolButton(self)
            b.setObjectName("surveyHudCapBtn")
            b.setText(icon)
            b.setToolTip(tip)
            b.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            b.setAutoRaise(True)
            b.setFixedSize(QtCore.QSize(22, 18))
            b.clicked.connect(fn)
            return b

        hl.addWidget(_mk_cap("−", "Minimize", self._hud.showMinimized))
        hl.addWidget(
            _mk_cap(
                "□",
                "Maximize",
                lambda: (
                    self._hud.showNormal()
                    if self._hud.isMaximized()
                    else self._hud.showMaximized()
                ),
            )
        )
        hl.addWidget(_mk_cap("×", "Close HUD", self._hud.close))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag = event.globalPosition().toPoint() - self._hud.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._hud.move(event.globalPosition().toPoint() - self._drag)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        tgt = self.childAt(event.position().toPoint())
        if tgt in (None, self._title) and event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self._hud.isMaximized():
                self._hud.showNormal()
            else:
                self._hud.showMaximized()
            return
        super().mouseDoubleClickEvent(event)


class _HudMetric(QtWidgets.QFrame):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        *,
        hero: bool = False,
        tooltip: str = "",
    ) -> None:
        super().__init__()
        self._metric_id = ""
        self._popout_ref: Any = None
        self._value_on_top = False
        self._compact = False
        self._hero = hero
        self._scale = 1.0
        self._show_subtitles = True
        self._has_subtitle = bool(subtitle)
        self.setObjectName("surveyHudMetricHero" if hero else "surveyHudMetric")
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        if tooltip:
            self.setToolTip(tooltip)

        self._lay = QtWidgets.QVBoxLayout(self)
        self._lay.setContentsMargins(3, 2, 3, 2)
        self._lay.setSpacing(0)

        self._title = QtWidgets.QLabel(title)
        self._title.setObjectName("surveyHudMetricTitle")
        self._title.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._title.setWordWrap(True)
        self._title_base_font = QtGui.QFont(self._title.font())

        self._sub = QtWidgets.QLabel(subtitle)
        self._sub.setObjectName("surveyHudMetricSub")
        self._sub.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._sub.setVisible(self._has_subtitle)
        self._sub_base_font = QtGui.QFont(self._sub.font())

        self._val = QtWidgets.QLabel("—")
        self._val.setObjectName("surveyHudMetricValueHero" if hero else "surveyHudMetricValue")
        self._val.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._val.setMinimumHeight(28 if hero else 18)
        self._val.setMinimumWidth(40)
        self._val_base_font = QtGui.QFont(self._val.font())
        self._last_text = "—"
        self._last_alert = False
        self._apply_style_layout()

    def _clear_layout(self) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item is None:
                continue

    def _apply_style_layout(self) -> None:
        scale = max(0.50, min(1.9, float(self._scale)))
        dense = self._compact or scale <= 0.90
        ultra_dense = scale <= 0.80
        self._clear_layout()

        # Preserve readability in compact mode by scaling fonts and hiding subtitles.
        def _scaled_font(base: QtGui.QFont, factor: float, min_pt: float) -> QtGui.QFont:
            f = QtGui.QFont(base)
            psz = base.pointSizeF()
            if psz <= 0:
                psz = float(base.pointSize() if base.pointSize() > 0 else 10.0)
            f.setPointSizeF(max(min_pt, psz * factor))
            return f

        title_factor = scale * (0.92 if dense else 1.0)
        val_factor = scale * (0.94 if dense else 1.0)
        sub_factor = scale * 0.88
        self._title.setFont(_scaled_font(self._title_base_font, title_factor, 7.0))
        self._val.setFont(_scaled_font(self._val_base_font, val_factor, 9.0))
        self._sub.setFont(_scaled_font(self._sub_base_font, sub_factor, 6.5))

        show_sub = self._has_subtitle and self._show_subtitles and not ultra_dense
        self._sub.setVisible(show_sub)

        if dense:
            self._lay.setContentsMargins(1, 0, 1, 0)
            self._lay.setSpacing(0)
            self.setMinimumHeight(int((52 if self._hero else 40) * scale))
        else:
            self._lay.setContentsMargins(2, 1, 2, 1)
            self._lay.setSpacing(0)
            self.setMinimumHeight(int((72 if self._hero else 52) * scale))
        self._val.setMinimumHeight(int((24 if self._hero else 18) * scale))

        if self._value_on_top:
            self._lay.addWidget(self._val, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
            self._lay.addWidget(self._title)
            if show_sub:
                self._lay.addWidget(self._sub)
        else:
            self._lay.addWidget(self._title)
            if show_sub:
                self._lay.addWidget(self._sub)
            self._lay.addWidget(self._val, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)

        self.updateGeometry()

    def apply_style(
        self,
        *,
        value_on_top: bool,
        compact: bool,
        scale: float,
        show_subtitles: bool,
    ) -> None:
        if (
            value_on_top == self._value_on_top
            and compact == self._compact
            and abs(float(scale) - float(self._scale)) < 0.001
            and show_subtitles == self._show_subtitles
        ):
            return
        self._value_on_top = value_on_top
        self._compact = compact
        self._scale = max(0.50, min(1.9, float(scale)))
        self._show_subtitles = bool(show_subtitles)
        self._apply_style_layout()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        pop = self._popout_ref
        mid = self._metric_id
        if pop is not None and mid:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                pop._toggle_metric_value_on_top(mid)
                event.accept()
                return
            if event.button() == QtCore.Qt.MouseButton.RightButton:
                pop._open_metric_style_menu(mid, event.globalPosition().toPoint())
                event.accept()
                return
        super().mousePressEvent(event)

    def set_value(self, text: str, *, alert: bool = False) -> None:
        if text == self._last_text and alert == self._last_alert:
            return
        if text != self._last_text:
            self._val.setText(text)
            self._last_text = text
        if alert == self._last_alert:
            return
        self._last_alert = alert
        self.setProperty("alert", "true" if alert else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class _SectionDragHandle(QtWidgets.QLabel):
    """Drag from ⋮ grip; release over another group's header swaps order (grabMouse so drop hits any widget under cursor)."""

    def __init__(self, section: object) -> None:
        super().__init__("\u22ee")
        self._sec = section
        self.setObjectName("surveyHudDragHandle")
        self.setToolTip(_TT_DRAG_ORDER)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
        self.setFixedWidth(16)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            pop = getattr(self._sec, "_popout_ref", None)
            if pop is not None:
                pop._reorder_drag_from = getattr(self._sec, "section_id", None)
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ClosedHandCursor))
            self.grabMouse()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        pop = getattr(self._sec, "_popout_ref", None)
        if self.hasMouseGrab():
            try:
                if (
                    pop is not None
                    and event.button() == QtCore.Qt.MouseButton.LeftButton
                    and getattr(pop, "_reorder_drag_from", None) in SECTION_IDS
                ):
                    from_id = str(pop._reorder_drag_from)
                    tgt = QtWidgets.QApplication.widgetAt(event.globalPosition().toPoint())
                    while tgt is not None:
                        sid = getattr(tgt, "section_id", None)
                        if sid in SECTION_IDS:
                            break
                        tgt = tgt.parentWidget()
                    to_sid = getattr(tgt, "section_id", "") if tgt is not None else ""
                    pop._reorder_drag_from = None
                    if to_sid and to_sid != from_id:
                        pop._swap_section_order(from_id, to_sid)
                elif pop is not None:
                    pop._reorder_drag_from = None
            finally:
                self.releaseMouse()
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
        super().mouseReleaseEvent(event)


class _HudSection(QtWidgets.QFrame):
    """Collapsible group; metrics registered by id for show/hide."""

    def __init__(
        self,
        section_id: str,
        heading: str,
        *,
        on_collapsed_changed: Optional[Callable[[str, bool], None]] = None,
    ) -> None:
        super().__init__()
        self.section_id = section_id
        self._heading = heading
        self._on_collapsed_changed = on_collapsed_changed
        self.setObjectName("surveyHudSection")
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self._popout_ref: Any = None
        # Do not absorb spare window height (collapsed headers were stretching to fill).
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )

        self._outer = QtWidgets.QVBoxLayout(self)
        self._outer.setContentsMargins(2, 1, 2, 1)
        self._outer.setSpacing(2)

        self._toggle = QtWidgets.QToolButton()
        self._toggle.setObjectName("surveyHudSectionToggle")
        self._toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        self._toggle.setText(heading)
        self._toggle.setToolTip(_TT_COLLAPSE)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(True)
        self._toggle.setAutoRaise(True)
        self._toggle.toggled.connect(self._on_toggle)

        self._head = QtWidgets.QWidget()
        head_lay = QtWidgets.QHBoxLayout(self._head)
        head_lay.setContentsMargins(0, 0, 0, 0)
        head_lay.setSpacing(2)
        self._drag_handle = _SectionDragHandle(self)
        head_lay.addWidget(self._drag_handle)
        head_lay.addWidget(self._toggle, 1)
        self._outer.addWidget(self._head)

        self._body = QtWidgets.QWidget()
        self._body.setObjectName("surveyHudSectionBody")
        self._body_grid = QtWidgets.QGridLayout(self._body)
        self._body_grid.setContentsMargins(0, 0, 0, 0)
        self._body_grid.setHorizontalSpacing(2)
        self._body_grid.setVerticalSpacing(2)

        self._outer.addWidget(self._body)

        self._metric_order: list[_HudMetric] = []
        self._ncols_max = 6
        self._ncols = 1
        self._apply_expanded(True)

    def _update_margins(self, expanded: bool) -> None:
        if expanded:
            self._outer.setContentsMargins(2, 1, 2, 1)
            self.setProperty("collapsed", "false")
        else:
            self._outer.setContentsMargins(2, 0, 2, 0)
            self.setProperty("collapsed", "true")
        self.style().unpolish(self)
        self.style().polish(self)

    def _apply_expanded(self, expanded: bool) -> None:
        """Keep visuals + geometry in sync; read toggle state vs signal arg (avoids sizing glitches after repeated toggles)."""
        self._body.setVisible(expanded)
        if expanded:
            self._body.setMinimumHeight(0)
            self._body.setMaximumHeight(16777215)
            self._body.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Minimum,
            )
        else:
            self._body.setMinimumHeight(0)
            self._body.setMaximumHeight(0)
            self._body.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Ignored,
                QtWidgets.QSizePolicy.Policy.Ignored,
            )
        self._outer.setSpacing(2 if expanded else 0)
        self._toggle.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow
        )
        if expanded:
            self._toggle.setMinimumHeight(0)
            self._toggle.setMaximumHeight(16777215)
        else:
            h = max(18, QtGui.QFontMetrics(self._toggle.font()).height() + 2)
            self._toggle.setFixedHeight(h)
        self._update_margins(expanded)
        self._body.updateGeometry()
        self.updateGeometry()

    def _on_toggle(self, _checked: bool) -> None:
        expanded = self._toggle.isChecked()
        self._apply_expanded(expanded)
        if self._on_collapsed_changed:
            self._on_collapsed_changed(self.section_id, not expanded)

    def is_expanded(self) -> bool:
        return bool(self._toggle.isChecked())

    def set_collapsed(self, collapsed: bool) -> None:
        expanded = not collapsed
        if self._toggle.isChecked() != expanded:
            self._toggle.blockSignals(True)
            self._toggle.setChecked(expanded)
            self._toggle.blockSignals(False)
        self._apply_expanded(expanded)

    def set_metrics(self, metrics: list[_HudMetric], *, col_cap: int = 6) -> None:
        self._metric_order = list(metrics)
        self._ncols_max = max(1, col_cap)
        self._ncols = min(self._ncols_max, len(self._metric_order) or 1)
        self._rebuild_body_grid()

    def set_body_columns(self, columns: int) -> None:
        want = max(1, min(columns, self._ncols_max, len(self._metric_order) or 1))
        if want == self._ncols:
            return
        self._ncols = want
        self._rebuild_body_grid()

    def _rebuild_body_grid(self) -> None:
        while self._body_grid.count():
            item = self._body_grid.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                self._body_grid.removeWidget(w)
        ncols = max(1, min(self._ncols, len(self._metric_order) or 1))
        for i, m in enumerate(self._metric_order):
            r, c = divmod(i, ncols)
            self._body_grid.addWidget(m, r, c)
        for c in range(ncols):
            self._body_grid.setColumnStretch(c, 1)

    def refresh_layout_chain(self) -> None:
        self._body_grid.invalidate()
        self._body_grid.activate()
        if (sl := self.layout()) is not None:
            sl.invalidate()
            sl.activate()

    def any_metric_visible(self) -> bool:
        return any(m.isVisible() for m in self._metric_order)


class _HudLayoutDialog(QtWidgets.QDialog):
    def __init__(self, cfg: dict[str, Any], parent: QtWidgets.QWidget | None) -> None:
        super().__init__(parent)
        self.setObjectName("SurveyHudLayoutDialog")
        self.setWindowTitle("Survey HUD layout")
        self.setMinimumWidth(400)
        self._cfg_in = deepcopy(cfg)
        self._cfg_out: dict[str, Any] = deepcopy(cfg)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 10)
        lay.setSpacing(10)

        header = QtWidgets.QFrame()
        header.setObjectName("layoutDialogHeader")
        hl = QtWidgets.QVBoxLayout(header)
        hl.setContentsMargins(16, 16, 16, 16)
        title = QtWidgets.QLabel("Survey HUD Configuration")
        title.setObjectName("layoutDialogTitle")
        sub = QtWidgets.QLabel("Tailor your telemetry views. (Curated by Argo)")
        sub.setObjectName("layoutDialogSub")
        hl.addWidget(title)
        hl.addWidget(sub)
        lay.addWidget(header)

        content = QtWidgets.QVBoxLayout()
        content.setContentsMargins(12, 0, 12, 0)
        content.setSpacing(8)
        lay.addLayout(content)

        hint = QtWidgets.QLabel(
            "Turn off groups or individual metrics you do not need. "
            "Collapsed groups stay on the HUD as a single header line until expanded."
        )
        hint.setWordWrap(True)
        content.addWidget(hint)

        self._section_boxes: dict[str, QtWidgets.QCheckBox] = {}
        self._collapse_boxes: dict[str, QtWidgets.QCheckBox] = {}
        self._metric_boxes: dict[str, QtWidgets.QCheckBox] = {}

        for sid in SECTION_IDS:
            box = QtWidgets.QGroupBox(SECTION_LABELS[sid])
            bl = QtWidgets.QVBoxLayout(box)
            show = QtWidgets.QCheckBox("Show this group")
            show.setChecked(cfg["sections"][sid]["visible"])
            self._section_boxes[sid] = show
            bl.addWidget(show)

            collapsed = QtWidgets.QCheckBox("Start minimized")
            collapsed.setChecked(cfg["sections"][sid]["collapsed"])
            self._collapse_boxes[sid] = collapsed
            bl.addWidget(collapsed)

            grid = QtWidgets.QGridLayout()
            row = 0
            for mid in METRIC_IDS:
                if METRIC_SECTION[mid] != sid:
                    continue
                cb = QtWidgets.QCheckBox(METRIC_LABELS[mid])
                cb.setChecked(cfg["metrics"][mid])
                self._metric_boxes[mid] = cb
                grid.addWidget(cb, row // 2, row % 2)
                row += 1
            bl.addLayout(grid)
            content.addWidget(box)

        foot_box = QtWidgets.QGroupBox("Connection strip")
        fl = QtWidgets.QVBoxLayout(foot_box)
        self._footer_cb = QtWidgets.QCheckBox("Show COM / network lines at bottom")
        self._footer_cb.setChecked(cfg.get("footer", True))
        fl.addWidget(self._footer_cb)
        content.addWidget(foot_box)

        presets = QtWidgets.QHBoxLayout()
        btn_rates = QtWidgets.QPushButton("Rates only")
        btn_rates.setToolTip("Show only sentence-rate metrics + connection strip")
        btn_rates.clicked.connect(self._preset_rates_only)
        btn_all = QtWidgets.QPushButton("Show all")
        btn_all.clicked.connect(self._preset_all)
        btn_reset = QtWidgets.QPushButton("Reset defaults")
        btn_reset.clicked.connect(self._preset_defaults)
        presets.addWidget(btn_rates)
        presets.addWidget(btn_all)
        presets.addWidget(btn_reset)
        presets.addStretch(1)
        content.addLayout(presets)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        content.addWidget(buttons)

        for sid in SECTION_IDS:
            self._section_boxes[sid].toggled.connect(
                lambda _checked=False, s=sid: self._sync_section_enabled(s)
            )
        for sid in SECTION_IDS:
            self._sync_section_enabled(sid)

    def _sync_section_enabled(self, sid: str) -> None:
        on = self._section_boxes[sid].isChecked()
        self._collapse_boxes[sid].setEnabled(on)
        for mid, cb in self._metric_boxes.items():
            if METRIC_SECTION[mid] == sid:
                cb.setEnabled(on)

    def _preset_rates_only(self) -> None:
        for sid in SECTION_IDS:
            self._section_boxes[sid].setChecked(sid == "rates")
            self._collapse_boxes[sid].setChecked(False)
        for mid in METRIC_IDS:
            self._metric_boxes[mid].setChecked(METRIC_SECTION[mid] == "rates")
        self._footer_cb.setChecked(True)
        for sid in SECTION_IDS:
            self._sync_section_enabled(sid)

    def _preset_all(self) -> None:
        for sid in SECTION_IDS:
            self._section_boxes[sid].setChecked(True)
            self._collapse_boxes[sid].setChecked(False)
        for mid in METRIC_IDS:
            self._metric_boxes[mid].setChecked(True)
        self._footer_cb.setChecked(True)
        for sid in SECTION_IDS:
            self._sync_section_enabled(sid)

    def _preset_defaults(self) -> None:
        d = default_layout()
        for sid in SECTION_IDS:
            self._section_boxes[sid].setChecked(d["sections"][sid]["visible"])
            self._collapse_boxes[sid].setChecked(d["sections"][sid]["collapsed"])
        for mid in METRIC_IDS:
            self._metric_boxes[mid].setChecked(d["metrics"][mid])
        self._footer_cb.setChecked(d["footer"])
        for sid in SECTION_IDS:
            self._sync_section_enabled(sid)

    def result_config(self) -> dict[str, Any]:
        if self.result() != QtWidgets.QDialog.DialogCode.Accepted:
            return self._cfg_in
        out = deepcopy(self._cfg_in)
        for sid in SECTION_IDS:
            out["sections"][sid]["visible"] = self._section_boxes[sid].isChecked()
            out["sections"][sid]["collapsed"] = self._collapse_boxes[sid].isChecked()
        for mid in METRIC_IDS:
            out["metrics"][mid] = self._metric_boxes[mid].isChecked()
        out["footer"] = self._footer_cb.isChecked()
        return out


class SurveyStatsPopout(QtWidgets.QWidget):
    def __init__(self, bridge_window: QtWidgets.QWidget) -> None:
        super().__init__(None)
        self._bridge = bridge_window
        self._layout_cfg = load_layout()
        self._theme_id = getattr(bridge_window, "_theme_id", "maroon_classic")
        self.setObjectName("SurveyStatsPopout")
        self.setWindowTitle("Survey HUD")
        self._base_min_width = 236
        self._base_min_height = 72
        self.setMinimumSize(self._base_min_width, self._base_min_height)
        self.resize(620, 360)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

        flags = QtCore.Qt.WindowType.Window | QtCore.Qt.WindowType.FramelessWindowHint
        if bool(self._layout_cfg.get("pin_on_top", True)):
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setStyleSheet(hud_stylesheet(self._theme_id))

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(1)

        btn_layout = QtWidgets.QPushButton("Layout…")
        btn_layout.setObjectName("surveyHudLayoutBtn")
        btn_layout.setToolTip(_TT_CUSTOMIZE)
        btn_layout.clicked.connect(self._open_layout_dialog)
        btn_theme = QtWidgets.QPushButton("Theme")
        btn_theme.setObjectName("surveyHudThemeBtn")
        btn_theme.setToolTip(_TT_THEME)
        btn_theme.clicked.connect(self._toggle_theme_quick)
        btn_corner = QtWidgets.QPushButton("Corner")
        btn_corner.setObjectName("surveyHudCornerBtn")
        btn_corner.setToolTip(_TT_CORNER)
        btn_corner.clicked.connect(self._apply_corner_preset)
        btn_readable = QtWidgets.QPushButton("Readable")
        btn_readable.setObjectName("surveyHudReadableBtn")
        btn_readable.setToolTip(_TT_READABLE)
        btn_readable.clicked.connect(self._apply_readable_preset)
        self._chk_top = QtWidgets.QCheckBox("Pin")
        self._chk_top.setObjectName("surveyHudPin")
        self._chk_top.setToolTip(_TT_PIN)
        self._chk_top.setChecked(bool(self._layout_cfg.get("pin_on_top", True)))
        self._chk_top.toggled.connect(self._on_stay_on_top)
        self._chk_row = QtWidgets.QCheckBox("Row")
        self._chk_row.setObjectName("surveyHudRow")
        self._chk_row.setToolTip(_TT_ROW)
        self._chk_row.setChecked(bool(self._layout_cfg.get("sections_row", False)))
        self._chk_row.toggled.connect(self._on_sections_row)
        self._chk_sub = QtWidgets.QCheckBox("Sub")
        self._chk_sub.setObjectName("surveyHudSub")
        self._chk_sub.setToolTip(_TT_SUB)
        self._chk_sub.setChecked(bool(self._layout_cfg.get("show_subtitles", True)))
        self._chk_sub.toggled.connect(self._on_show_subtitles)
        self._chk_log = QtWidgets.QCheckBox("Log")
        self._chk_log.setObjectName("surveyHudLog")
        self._chk_log.setToolTip(_TT_LOG)
        self._chk_log.setChecked(bool(self._layout_cfg.get("show_nmea_log", False)))
        self._chk_log.toggled.connect(self._on_show_nmea_log)
        self._chk_lock = QtWidgets.QCheckBox("Lock")
        self._chk_lock.setObjectName("surveyHudLock")
        self._chk_lock.setToolTip(_TT_LOCK)
        self._chk_lock.setChecked(bool(self._layout_cfg.get("lock_size", False)))
        self._chk_lock.toggled.connect(self._on_lock_size)
        self._scale_box = QtWidgets.QComboBox()
        self._scale_box.setObjectName("surveyHudScale")
        self._scale_box.setToolTip(_TT_SCALE)
        self._scale_box.setFixedWidth(68)
        for txt, v in (
            ("50%", 0.50),
            ("60%", 0.60),
            ("75%", 0.75),
            ("90%", 0.90),
            ("100%", 1.00),
            ("115%", 1.15),
            ("130%", 1.30),
            ("150%", 1.50),
        ):
            self._scale_box.addItem(txt, v)
        self._scale_box.currentIndexChanged.connect(self._on_box_scale_changed)
        self._cols_box = QtWidgets.QComboBox()
        self._cols_box.setObjectName("surveyHudCols")
        self._cols_box.setToolTip(_TT_COLS)
        self._cols_box.setFixedWidth(64)
        for txt, v in (("Auto", 0), ("1", 1), ("2", 2), ("3", 3), ("4", 4), ("6", 6)):
            self._cols_box.addItem(txt, v)
        self._cols_box.currentIndexChanged.connect(self._on_forced_columns_changed)

        self._chrome = _HudChromeBar(
            self,
            layout_btn=btn_layout,
            theme_btn=btn_theme,
            corner_btn=btn_corner,
            readable_btn=btn_readable,
            row_cb=self._chk_row,
            pin_cb=self._chk_top,
            sub_cb=self._chk_sub,
            log_cb=self._chk_log,
            lock_cb=self._chk_lock,
            scale_box=self._scale_box,
            cols_box=self._cols_box,
        )
        root.addWidget(self._chrome)

        self._responsive_cols: tuple[int, int, int] = (-1, -1, -1)
        self._shrink_pending = False
        self._layout_reflow_in_progress = False
        self._interactive_resize_active = False
        self._first_show_layout_pending = True
        self._layout_reflow_timer = QtCore.QTimer(self)
        self._layout_reflow_timer.setSingleShot(True)
        self._layout_reflow_timer.timeout.connect(self._recompute_layout_now)

        self._sections: dict[str, _HudSection] = {}
        self._metrics: dict[str, _HudMetric] = {}
        self._strip_layout_key: Optional[tuple[bool, tuple[str, ...]]] = None
        self._sections_strip_horizontal = False
        self._reorder_drag_from: str | None = None

        ROLES = ("nw", "n", "ne", "w", "e", "sw", "s", "se")
        self._resize_handles: dict[str, _HudResizeEdge] = {r: _HudResizeEdge(self, r) for r in ROLES}
        self._resize_border_px = 8

        self._sections_scroll = QtWidgets.QScrollArea()
        self._sections_scroll.setObjectName("surveyHudSectionsScroll")
        self._sections_scroll.setWidgetResizable(True)
        self._sections_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._sections_scroll.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft
        )
        self._sections_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._sections_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._sections_scroll.viewport().setAutoFillBackground(True)
        self._sections_scroll.viewport().setStyleSheet(
            "background-color: #2a1d22;"
        )

        self._sections_host = QtWidgets.QWidget()
        self._sections_host.setObjectName("surveyHudSectionsHost")
        self._sections_host.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self._sections_host.setStyleSheet("background-color: #2a1d22;")
        self._sections_host.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self._sections_band_layout = QtWidgets.QGridLayout(self._sections_host)
        self._sections_band_layout.setContentsMargins(0, 0, 0, 0)
        self._sections_band_layout.setHorizontalSpacing(3)
        self._sections_band_layout.setVerticalSpacing(3)
        self._sections_band_layout.setSizeConstraint(
            QtWidgets.QLayout.SizeConstraint.SetMinimumSize
        )
        self._sections_band_layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft
        )
        self._sections_scroll.setWidget(self._sections_host)

        sec_rates = _HudSection(
            "rates", SECTION_LABELS["rates"], on_collapsed_changed=self._section_collapsed_changed
        )
        self._m_hz_dn = _HudMetric("Into COM", "per second", hero=True, tooltip=_TT_HZ_DOWN)
        self._m_hz_up = _HudMetric("From COM", "per second", hero=True, tooltip=_TT_HZ_UP)
        self._m_hz_inj = _HudMetric("Inject", "Send tab only", hero=True, tooltip=_TT_HZ_INJ)
        sec_rates.set_metrics([self._m_hz_dn, self._m_hz_up, self._m_hz_inj], col_cap=3)
        self._register_metric("hz_dn", self._m_hz_dn)
        self._register_metric("hz_up", self._m_hz_up)
        self._register_metric("hz_inj", self._m_hz_inj)
        self._sections["rates"] = sec_rates

        sec_sess = _HudSection(
            "session",
            SECTION_LABELS["session"],
            on_collapsed_changed=self._section_collapsed_changed,
        )
        self._m_sess_dn = _HudMetric("Toward COM", "total lines", tooltip=_TT_SESS_DOWN)
        self._m_sess_up = _HudMetric("Toward network", "total lines", tooltip=_TT_SESS_UP)
        self._m_health = _HudMetric("Transport", "backpressure", tooltip=_TT_TRANSPORT)
        sec_sess.set_metrics([self._m_sess_dn, self._m_sess_up, self._m_health], col_cap=3)
        self._register_metric("sess_dn", self._m_sess_dn)
        self._register_metric("sess_up", self._m_sess_up)
        self._register_metric("health", self._m_health)
        self._sections["session"] = sec_sess

        sec_bp = _HudSection(
            "backpressure",
            SECTION_LABELS["backpressure"],
            on_collapsed_changed=self._section_collapsed_changed,
        )
        self._m_dr_ns = _HudMetric("Drops", "network → COM", tooltip=_TT_DROP_NS)
        self._m_dr_sn = _HudMetric("Drops", "COM → network", tooltip=_TT_DROP_SN)
        self._m_rj_ns = _HudMetric("Rejected", "toward COM", tooltip=_TT_REJ_NS)
        self._m_rj_sn = _HudMetric("Rejected", "from COM", tooltip=_TT_REJ_SN)
        self._m_q_ns = _HudMetric("Queued", "toward COM", tooltip=_TT_Q_NS)
        self._m_q_sn = _HudMetric("Queued", "toward network", tooltip=_TT_Q_SN)
        bp_order = (
            self._m_dr_ns,
            self._m_dr_sn,
            self._m_rj_ns,
            self._m_rj_sn,
            self._m_q_ns,
            self._m_q_sn,
        )
        sec_bp.set_metrics(list(bp_order), col_cap=6)
        for mid, m in (
            ("dr_ns", self._m_dr_ns),
            ("dr_sn", self._m_dr_sn),
            ("rj_ns", self._m_rj_ns),
            ("rj_sn", self._m_rj_sn),
            ("q_ns", self._m_q_ns),
            ("q_sn", self._m_q_sn),
        ):
            self._register_metric(mid, m)
        self._sections["backpressure"] = sec_bp

        for sec in self._sections.values():
            sec._popout_ref = self

        self._foot_panel = QtWidgets.QFrame()
        self._foot_panel.setObjectName("surveyHudFootPanel")
        self._foot_panel.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._foot_panel.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        foot = QtWidgets.QVBoxLayout(self._foot_panel)
        foot.setContentsMargins(4, 2, 4, 2)
        foot.setSpacing(2)
        self._foot_serial = QtWidgets.QLabel("—")
        self._foot_serial.setObjectName("surveyHudFootLine")
        self._foot_serial.setToolTip(_TT_SERIAL)
        self._foot_net = QtWidgets.QLabel("—")
        self._foot_net.setObjectName("surveyHudFootLine")
        self._foot_net.setToolTip(_TT_NETWORK)
        foot.addWidget(self._foot_serial)
        foot.addWidget(self._foot_net)

        self._metrics_pane = QtWidgets.QWidget()
        mlay = QtWidgets.QVBoxLayout(self._metrics_pane)
        mlay.setContentsMargins(0, 0, 0, 0)
        mlay.setSpacing(1)
        mlay.addWidget(self._sections_scroll, 1)
        mlay.addWidget(self._foot_panel)

        self._nmea_panel = QtWidgets.QFrame()
        self._nmea_panel.setObjectName("surveyHudNmeaPanel")
        self._nmea_panel.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._nmea_panel.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        nlay = QtWidgets.QVBoxLayout(self._nmea_panel)
        nlay.setContentsMargins(2, 2, 2, 2)
        nlay.setSpacing(2)
        ncap = QtWidgets.QLabel("NMEA log")
        ncap.setObjectName("surveyHudSectionHead")
        nlay.addWidget(ncap)
        self._nmea_log = QtWidgets.QPlainTextEdit()
        self._nmea_log.setObjectName("surveyHudNmeaLog")
        self._nmea_log.setReadOnly(True)
        self._nmea_log.setMaximumBlockCount(800)
        self._nmea_log.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        nlay.addWidget(self._nmea_log, 1)

        self._content_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._content_splitter.addWidget(self._metrics_pane)
        self._content_splitter.addWidget(self._nmea_panel)
        self._content_splitter.setStretchFactor(0, 3)
        self._content_splitter.setStretchFactor(1, 2)
        self._content_splitter.setSizes([720, 360])
        root.addWidget(self._content_splitter, 1)

        self.apply_layout_config(self._layout_cfg)
        self.apply_snapshot({}, "", "", running=False)
        self._layout_resize_handles()

    def _layout_resize_handles(self) -> None:
        h = getattr(self, "_resize_handles", None)
        if not h:
            return
        if bool(self._layout_cfg.get("lock_size", False)):
            for wg in h.values():
                wg.hide()
            return
        m = max(6, int(getattr(self, "_resize_border_px", 8)))
        w_, h_ = max(1, self.width()), max(1, self.height())

        hide = (
            self.isMaximized()
            or self.isFullScreen()
            or w_ <= m * 2
            or h_ <= m * 2
        )
        if hide:
            for wg in h.values():
                wg.hide()
            return

        h["nw"].setGeometry(0, 0, m, m)
        h["n"].setGeometry(m, 0, max(m, w_ - 2 * m), m)
        h["ne"].setGeometry(max(0, w_ - m), 0, m, m)
        h["w"].setGeometry(0, m, m, max(m, h_ - 2 * m))
        h["e"].setGeometry(max(0, w_ - m), m, m, max(m, h_ - 2 * m))
        h["sw"].setGeometry(0, max(0, h_ - m), m, m)
        h["s"].setGeometry(m, max(0, h_ - m), max(m, w_ - 2 * m), m)
        h["se"].setGeometry(max(0, w_ - m), max(0, h_ - m), m, m)

        for wg in h.values():
            wg.show()
        # Edges under corners so intersections use diagonal resize.
        for role in ("n", "w", "e", "s", "nw", "ne", "sw", "se"):
            h[role].raise_()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._layout_resize_handles()
        if not self._interactive_resize_active:
            self._schedule_layout_reflow()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._layout_resize_handles()
        QtCore.QTimer.singleShot(0, lambda: self._layout_resize_handles())
        QtCore.QTimer.singleShot(0, self._reset_sections_scroll_origin)
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()
        QtCore.QTimer.singleShot(40, self._finalize_first_show_layout)

    def _reset_sections_scroll_origin(self) -> None:
        # Avoid reopening at stale scrolled positions after previous resizes.
        self._sections_scroll.horizontalScrollBar().setValue(0)
        self._sections_scroll.verticalScrollBar().setValue(0)

    def _finalize_first_show_layout(self) -> None:
        if not self.isVisible():
            return
        self._recompute_layout_now()
        self._reset_sections_scroll_origin()
        self._sections_scroll.ensureVisible(0, 0, 0, 0)
        self._first_show_layout_pending = False

    def changeEvent(self, event: QtCore.QEvent) -> None:
        if event.type() == QtCore.QEvent.Type.WindowStateChange:
            self._layout_resize_handles()
        super().changeEvent(event)

    def _columns_for_band(self, usable_w: int, *, hero_tiles: bool) -> int:
        u = usable_w
        scale = self._box_scale_cfg()
        dense = scale <= 0.90
        if hero_tiles:
            if dense:
                if u < 240:
                    return 1
                if u < 360:
                    return 2
                return 3
            if u < 380:
                return 1
            if u < 640:
                return 2
            return 3
        # Backpressure tiles (smaller)
        if dense:
            if u < 180:
                return 1
            if u < 260:
                return 2
            if u < 340:
                return 3
            if u < 460:
                return 4
            return 6
        if u < 300:
            return 1
        if u < 430:
            return 2
        if u < 580:
            return 3
        if u < 820:
            return 4
        return 6

    def _usable_inner_width(self) -> int:
        vp = getattr(self, "_sections_scroll", None)
        if vp is not None:
            vw = vp.viewport().width()
            if vw > 0:
                return max(200, vw - 2)
        lay = self.layout()
        if lay is None:
            return max(200, self.width() - 8)
        mg = lay.contentsMargins()
        return max(200, self.width() - mg.left() - mg.right() - 2)

    def _visible_section_ids_ordered(self) -> list[str]:
        order = normalized_section_order(self._layout_cfg.get("section_order"))
        return [sid for sid in order if self._sections[sid].isVisible()]

    def _sections_collapsed_where_visible(self) -> bool:
        for sid in SECTION_IDS:
            sec = self._sections[sid]
            if not sec.isVisible():
                continue
            if sec.is_expanded():
                return False
        return True

    def _prefer_horizontal_sections_strip(self) -> bool:
        uw = self._usable_inner_width()
        ar = self.width() / max(1, self.height())
        if uw < 420:
            return False
        if ar >= 1.95 and uw >= 480:
            return True
        if uw >= 720 and ar >= 1.12:
            return True
        if uw >= 600 and ar >= 1.25:
            return True
        if uw >= 960:
            return True
        return False

    def _apply_section_strip_layout(self) -> None:
        vis_tuple = tuple(self._visible_section_ids_ordered())
        force_row = bool(self._layout_cfg.get("sections_row", False))
        # Respect Row toggle directly; viewport handles overflow safely.
        allow_forced_row = force_row
        # Keep behavior deterministic: Row toggle controls horizontal strip.
        horizontal = len(vis_tuple) >= 2 and allow_forced_row
        key = (horizontal, vis_tuple)
        if key != self._strip_layout_key:
            self._strip_layout_key = key
            lay = self._sections_band_layout
            for sid in SECTION_IDS:
                w = self._sections[sid]
                lay.removeWidget(w)
            for i in range(8):
                lay.setColumnStretch(i, 0)
                lay.setRowStretch(i, 0)

            visible_list = list(vis_tuple)
            if horizontal:
                for col, sid in enumerate(visible_list):
                    lay.addWidget(self._sections[sid], 0, col)
                    lay.setColumnStretch(col, 1)
            else:
                for row, sid in enumerate(visible_list):
                    lay.addWidget(self._sections[sid], row, 0)
                    lay.setColumnStretch(0, 1)

        self._sections_strip_horizontal = horizontal

    def _effective_metric_band_width(self) -> int:
        uw = self._usable_inner_width()
        visible_list = self._visible_section_ids_ordered()
        if not visible_list:
            return uw
        if self._sections_strip_horizontal and len(visible_list) >= 2:
            gs = self._sections_band_layout.horizontalSpacing()
            g = gs if gs is not None and gs >= 0 else 3
            return max(220, (uw - g * (len(visible_list) - 1)) // len(visible_list))
        return uw

    def _apply_responsive_columns(self) -> None:
        if self._interactive_resize_active and self._responsive_cols != (-1, -1, -1):
            # Keep columns stable while the user is dragging window edges.
            return
        self._apply_section_strip_layout()
        uw = self._effective_metric_band_width()
        cr = self._columns_for_band(uw, hero_tiles=True)
        cs = self._columns_for_band(uw, hero_tiles=True)
        cb = self._columns_for_band(uw, hero_tiles=False)
        forced = max(0, min(6, int(self._layout_cfg.get("forced_columns", 0) or 0)))
        if forced > 0:
            cr = max(1, min(3, forced))
            cs = max(1, min(3, forced))
            cb = max(1, min(6, forced))
        sig = (cr, cs, cb)
        if sig == self._responsive_cols:
            return
        self._responsive_cols = sig
        self._sections["rates"].set_body_columns(cr)
        self._sections["session"].set_body_columns(cs)
        self._sections["backpressure"].set_body_columns(cb)

    def _register_metric(self, mid: str, widget: _HudMetric) -> None:
        self._metrics[mid] = widget
        widget._metric_id = mid
        widget._popout_ref = self

    def _metric_style_cfg(self, mid: str) -> dict[str, bool]:
        styles = self._layout_cfg.setdefault("metric_style", {})
        block = styles.get(mid)
        if not isinstance(block, dict):
            block = {"value_on_top": False, "compact": False}
            styles[mid] = block
        block["value_on_top"] = bool(block.get("value_on_top", False))
        block["compact"] = bool(block.get("compact", False))
        return block

    def _box_scale_cfg(self) -> float:
        raw = self._layout_cfg.get("box_scale", 1.0)
        try:
            val = float(raw)
        except (TypeError, ValueError):
            val = 1.0
        val = max(0.50, min(1.9, val))
        self._layout_cfg["box_scale"] = val
        return val

    def _apply_metric_style(self, mid: str) -> None:
        w = self._metrics.get(mid)
        if w is None:
            return
        st = self._metric_style_cfg(mid)
        w.apply_style(
            value_on_top=bool(st.get("value_on_top", False)),
            compact=bool(st.get("compact", False)),
            scale=self._box_scale_cfg(),
            show_subtitles=bool(self._layout_cfg.get("show_subtitles", True)),
        )

    def _toggle_metric_value_on_top(self, mid: str) -> None:
        st = self._metric_style_cfg(mid)
        st["value_on_top"] = not bool(st.get("value_on_top", False))
        save_layout(self._layout_cfg)
        self._apply_metric_style(mid)
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _set_metric_compact(self, mid: str, on: bool) -> None:
        st = self._metric_style_cfg(mid)
        st["compact"] = bool(on)
        save_layout(self._layout_cfg)
        self._apply_metric_style(mid)
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _reset_metric_style(self, mid: str) -> None:
        st = self._metric_style_cfg(mid)
        st["value_on_top"] = False
        st["compact"] = False
        save_layout(self._layout_cfg)
        self._apply_metric_style(mid)
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _open_metric_style_menu(self, mid: str, global_pos: QtCore.QPoint) -> None:
        st = self._metric_style_cfg(mid)
        menu = QtWidgets.QMenu(self)
        act_top = menu.addAction("Number on top")
        act_top.setCheckable(True)
        act_top.setChecked(bool(st.get("value_on_top", False)))
        act_compact = menu.addAction("Compact box")
        act_compact.setCheckable(True)
        act_compact.setChecked(bool(st.get("compact", False)))
        menu.addSeparator()
        act_reset = menu.addAction("Reset box style")

        chosen = menu.exec(global_pos)
        if chosen == act_top:
            self._toggle_metric_value_on_top(mid)
        elif chosen == act_compact:
            self._set_metric_compact(mid, bool(act_compact.isChecked()))
        elif chosen == act_reset:
            self._reset_metric_style(mid)

    def _section_collapsed_changed(self, section_id: str, collapsed: bool) -> None:
        self._layout_cfg["sections"][section_id]["collapsed"] = collapsed
        save_layout(self._layout_cfg)
        self._strip_layout_key = None
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _open_layout_dialog(self) -> None:
        dlg = _HudLayoutDialog(self._layout_cfg, self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        self._layout_cfg = dlg.result_config()
        save_layout(self._layout_cfg)
        self.apply_layout_config(self._layout_cfg)

    def apply_layout_config(self, cfg: dict[str, Any]) -> None:
        for sid, sec in self._sections.items():
            block = cfg["sections"][sid]
            visible = bool(block["visible"])
            sec.setVisible(visible)
            if visible:
                sec.set_collapsed(bool(block["collapsed"]))
            for mid, widget in self._metrics.items():
                if METRIC_SECTION[mid] != sid:
                    continue
                show = visible and bool(cfg["metrics"].get(mid, True))
                widget.setVisible(show)
        show_foot = bool(cfg.get("footer", True))
        self._foot_panel.setVisible(show_foot)
        self._set_nmea_panel_visible(bool(cfg.get("show_nmea_log", False)))
        for mid in METRIC_IDS:
            self._apply_metric_style(mid)
        cfg["section_order"] = normalized_section_order(cfg.get("section_order"))
        self._strip_layout_key = None
        self._sync_chrome_from_cfg()
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _sync_chrome_from_cfg(self) -> None:
        cfg = self._layout_cfg
        self._chk_row.blockSignals(True)
        self._chk_row.setChecked(bool(cfg.get("sections_row", False)))
        self._chk_row.blockSignals(False)
        pin_on = bool(cfg.get("pin_on_top", True))
        self._chk_top.blockSignals(True)
        self._chk_top.setChecked(pin_on)
        self._chk_top.blockSignals(False)
        self._chk_sub.blockSignals(True)
        self._chk_sub.setChecked(bool(cfg.get("show_subtitles", True)))
        self._chk_sub.blockSignals(False)
        self._chk_log.blockSignals(True)
        self._chk_log.setChecked(bool(cfg.get("show_nmea_log", False)))
        self._chk_log.blockSignals(False)
        self._chk_lock.blockSignals(True)
        self._chk_lock.setChecked(bool(cfg.get("lock_size", False)))
        self._chk_lock.blockSignals(False)
        forced = max(0, min(6, int(cfg.get("forced_columns", 0) or 0)))
        idx = 0
        for i in range(self._cols_box.count()):
            data = self._cols_box.itemData(i)
            if int(data or 0) == forced:
                idx = i
                break
        self._cols_box.blockSignals(True)
        self._cols_box.setCurrentIndex(idx)
        self._cols_box.blockSignals(False)
        scale = self._box_scale_cfg()
        best_i = 0
        best_d = 999.0
        for i in range(self._scale_box.count()):
            data = self._scale_box.itemData(i)
            try:
                v = float(data)
            except (TypeError, ValueError):
                continue
            d = abs(v - scale)
            if d < best_d:
                best_d = d
                best_i = i
        self._scale_box.blockSignals(True)
        self._scale_box.setCurrentIndex(best_i)
        self._scale_box.blockSignals(False)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, pin_on)

    def _swap_section_order(self, a: str, b: str) -> None:
        if a not in SECTION_IDS or b not in SECTION_IDS or a == b:
            return
        order = normalized_section_order(self._layout_cfg.get("section_order"))
        ia, ib = order.index(a), order.index(b)
        order[ia], order[ib] = order[ib], order[ia]
        self._layout_cfg["section_order"] = order
        save_layout(self._layout_cfg)
        self._strip_layout_key = None
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _on_sections_row(self, on: bool) -> None:
        self._layout_cfg["sections_row"] = on
        save_layout(self._layout_cfg)
        self._strip_layout_key = None
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _on_box_scale_changed(self, index: int) -> None:
        data = self._scale_box.itemData(index)
        try:
            scale = float(data)
        except (TypeError, ValueError):
            scale = 1.0
        scale = max(0.50, min(1.9, scale))
        if abs(scale - self._box_scale_cfg()) < 0.001:
            return
        self._layout_cfg["box_scale"] = scale
        save_layout(self._layout_cfg)
        for mid in METRIC_IDS:
            self._apply_metric_style(mid)
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _on_forced_columns_changed(self, index: int) -> None:
        data = self._cols_box.itemData(index)
        try:
            cols = int(data)
        except (TypeError, ValueError):
            cols = 0
        cols = max(0, min(6, cols))
        if cols == int(self._layout_cfg.get("forced_columns", 0) or 0):
            return
        self._layout_cfg["forced_columns"] = cols
        save_layout(self._layout_cfg)
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _on_show_subtitles(self, on: bool) -> None:
        if bool(self._layout_cfg.get("show_subtitles", True)) == bool(on):
            return
        self._layout_cfg["show_subtitles"] = bool(on)
        save_layout(self._layout_cfg)
        for mid in METRIC_IDS:
            self._apply_metric_style(mid)
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _on_show_nmea_log(self, on: bool) -> None:
        if bool(self._layout_cfg.get("show_nmea_log", False)) == bool(on):
            return
        self._layout_cfg["show_nmea_log"] = bool(on)
        save_layout(self._layout_cfg)
        self._set_nmea_panel_visible(bool(on))

    def _set_nmea_panel_visible(self, on: bool) -> None:
        self._nmea_panel.setVisible(on)
        if on:
            self._content_splitter.setSizes([720, 360])
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _on_lock_size(self, on: bool) -> None:
        if bool(self._layout_cfg.get("lock_size", False)) == bool(on):
            return
        self._layout_cfg["lock_size"] = bool(on)
        if on:
            self._interactive_resize_active = False
        save_layout(self._layout_cfg)
        self._layout_resize_handles()

    def _apply_corner_preset(self) -> None:
        self._layout_cfg["box_scale"] = 0.60
        self._layout_cfg["forced_columns"] = 6
        self._layout_cfg["show_subtitles"] = False
        self._layout_cfg["show_nmea_log"] = True
        self._layout_cfg["sections_row"] = True
        save_layout(self._layout_cfg)
        self._sync_chrome_from_cfg()
        for mid in METRIC_IDS:
            self._apply_metric_style(mid)
        self._strip_layout_key = None
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _apply_readable_preset(self) -> None:
        self._layout_cfg["box_scale"] = 0.90
        self._layout_cfg["forced_columns"] = 0
        self._layout_cfg["show_subtitles"] = True
        self._layout_cfg["show_nmea_log"] = False
        self._layout_cfg["sections_row"] = False
        save_layout(self._layout_cfg)
        self._sync_chrome_from_cfg()
        for mid in METRIC_IDS:
            self._apply_metric_style(mid)
        self._strip_layout_key = None
        self._schedule_layout_reflow()
        self._schedule_shrink_to_content()

    def _schedule_shrink_to_content(self) -> None:
        if self._shrink_pending:
            return
        self._shrink_pending = True

        def _run() -> None:
            self._shrink_pending = False
            self._shrink_to_content()

        QtCore.QTimer.singleShot(0, _run)

    def _schedule_layout_reflow(self) -> None:
        # Debounce relayout while user drags/resizes to prevent UI stalls.
        delay_ms = 90 if self._interactive_resize_active else 28
        self._layout_reflow_timer.start(delay_ms)

    def _recompute_layout_now(self) -> None:
        if self._layout_reflow_in_progress:
            return
        self._layout_reflow_in_progress = True
        try:
            self._apply_responsive_columns()
            self._normalize_sections_canvas()
            if self._first_show_layout_pending:
                self._reset_sections_scroll_origin()
        finally:
            self._layout_reflow_in_progress = False

    def _normalize_sections_canvas(self) -> None:
        vp = self._sections_scroll.viewport()
        if vp is None:
            return
        target_w = max(220, vp.width())
        if self._sections_host.minimumWidth() != target_w:
            self._sections_host.setMinimumWidth(target_w)
        self._sections_host.updateGeometry()

    def _shrink_to_content(self) -> None:
        self._recompute_layout_now()

        root = self.layout()
        if root is not None:
            root.invalidate()

        # Keep a stable floor; rely on scroll area instead of forced window resize.
        self.setMinimumSize(self._base_min_width, self._base_min_height)

    def _on_stay_on_top(self, on: bool) -> None:
        self._layout_cfg["pin_on_top"] = on
        save_layout(self._layout_cfg)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, on)
        self.show()
        self.raise_()
        self.activateWindow()

    def apply_snapshot(
        self,
        d: dict,
        serial_line: str,
        network_line: str,
        *,
        running: bool,
    ) -> None:
        # Avoid heavy repaint churn while user is actively dragging resize edges.
        if self._interactive_resize_active:
            return
        if self._foot_panel.isVisible():
            self._foot_serial.setText(_strip_status_prefix(serial_line))
            self._foot_net.setText(_strip_status_prefix(network_line))

        visible_metrics = [m for mid, m in self._metrics.items() if m.isVisible()]

        if not running:
            for m in visible_metrics:
                m.set_value("—", alert=False)
            if self._m_health.isVisible():
                self._m_health.set_value("Off", alert=False)
            return

        hz_d = float(d.get("hz_down", 0.0))
        hz_u = float(d.get("hz_up", 0.0))
        hz_i = float(d.get("hz_gui", 0.0))
        ld = int(d.get("lines_down", 0))
        lu = int(d.get("lines_up", 0))
        d_ns = int(d.get("drops_n2s", 0))
        d_sn = int(d.get("drops_s2n", 0))
        r_ns = int(d.get("rej_n2s", 0))
        r_sn = int(d.get("rej_s2n", 0))
        q_ns = int(d.get("n2s_q", 0))
        q_sn = int(d.get("s2n_q", 0))

        if self._m_hz_dn.isVisible():
            self._m_hz_dn.set_value(f"{hz_d:.1f}", alert=False)
        if self._m_hz_up.isVisible():
            self._m_hz_up.set_value(f"{hz_u:.1f}", alert=False)
        if self._m_hz_inj.isVisible():
            self._m_hz_inj.set_value(f"{hz_i:.1f}" if hz_i >= 0.05 else "0", alert=False)
        if self._m_sess_dn.isVisible():
            self._m_sess_dn.set_value(_fmt_k(ld) if ld else "0", alert=False)
        if self._m_sess_up.isVisible():
            self._m_sess_up.set_value(_fmt_k(lu) if lu else "0", alert=False)

        warn = bool(d_ns or d_sn or r_ns or r_sn or q_ns or q_sn)
        if self._m_health.isVisible():
            self._m_health.set_value("Warn" if warn else "OK", alert=warn)

        if self._m_dr_ns.isVisible():
            self._m_dr_ns.set_value(str(d_ns), alert=bool(d_ns))
        if self._m_dr_sn.isVisible():
            self._m_dr_sn.set_value(str(d_sn), alert=bool(d_sn))
        if self._m_rj_ns.isVisible():
            self._m_rj_ns.set_value(str(r_ns), alert=bool(r_ns))
        if self._m_rj_sn.isVisible():
            self._m_rj_sn.set_value(str(r_sn), alert=bool(r_sn))
        if self._m_q_ns.isVisible():
            self._m_q_ns.set_value(str(q_ns), alert=bool(q_ns))
        if self._m_q_sn.isVisible():
            self._m_q_sn.set_value(str(q_sn), alert=bool(q_sn))

    def set_status_lines(self, serial: str, network: str) -> None:
        if self._foot_panel.isVisible():
            self._foot_serial.setText(_strip_status_prefix(serial))
            self._foot_net.setText(_strip_status_prefix(network))

    def append_nmea_log_lines(self, lines: list[str]) -> None:
        if not lines:
            return
        self._nmea_log.appendPlainText("\n".join(lines))
        sb = self._nmea_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_stats_text(self, text: str, tooltip: str) -> None:
        _ = text, tooltip

    def bridge_window(self) -> QtWidgets.QWidget:
        return self._bridge

    def set_theme(self, theme_id: str) -> None:
        self._theme_id = theme_id
        self.setStyleSheet(hud_stylesheet(theme_id))

    def _toggle_theme_quick(self) -> None:
        nxt = (
            THEME_MAROON_HC
            if self._theme_id == THEME_MAROON_CLASSIC
            else THEME_MAROON_CLASSIC
        )
        bridge = self.bridge_window()
        fn = getattr(bridge, "_apply_theme", None)
        if callable(fn):
            fn(nxt)
            return
        self.set_theme(nxt)


def _strip_status_prefix(line: str) -> str:
    s = line.strip()
    for prefix in ("Serial:", "Network:", "Serial :", "Network :"):
        if s.lower().startswith(prefix.lower()):
            return s[len(prefix) :].strip()
    return s

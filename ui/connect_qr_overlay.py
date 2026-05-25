"""Floating phone-setup QR on the Connect tab (Web API + LAN enabled)."""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

_QR_BASE_PX = 256
_QR_MIN_PX = 88
_QR_MAX_PX = 160
_QUIET_ZONE = 4
_FLOAT_MARGIN = 16
_STATUS_BAR_RESERVE = 44


class ConnectQrFloat(QtWidgets.QFrame):
    """Draggable QR chip on the main window; right-click to hide until Web API cycles."""

    def __init__(self, win: QtWidgets.QWidget) -> None:
        super().__init__(win)
        self._win = win
        self._drag_origin: QtCore.QPoint | None = None
        self._source: Optional[QtGui.QPixmap] = None
        self._message = ""
        self.setObjectName("connectQrFloat")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Drag to move · right-click to hide until Web API is toggled off/on")

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 4)
        lay.setSpacing(2)
        self._img = QtWidgets.QLabel()
        self._img.setObjectName("connectQrImage")
        self._img.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._img.setMinimumSize(_QR_MIN_PX + _QUIET_ZONE * 2, _QR_MIN_PX + _QUIET_ZONE * 2)
        lay.addWidget(self._img, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        self._hint = QtWidgets.QLabel("Scan on phone")
        self._hint.setObjectName("connectQrCaption")
        self._hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._hint, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.hide()

    def set_qr_content(
        self,
        *,
        pixmap: Optional[QtGui.QPixmap] = None,
        message: str = "",
    ) -> None:
        self._source = pixmap if pixmap is not None and not pixmap.isNull() else None
        self._message = (message or "").strip()
        self._apply_scaled_pixmap()
        self.adjustSize()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_scaled_pixmap()

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        menu = QtWidgets.QMenu(self)
        hide_act = menu.addAction("Hide QR code")
        hide_act.setToolTip("Shown again when Web API is turned off and back on")
        if menu.exec(event.globalPos()) == hide_act:
            self._win._connect_qr_user_hidden = True  # type: ignore[attr-defined]
            self.hide()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_origin is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self._drag_origin is not None:
            self._drag_origin = None
            self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            self._win._connect_qr_user_positioned = True  # type: ignore[attr-defined]
            _persist_qr_float_pos(self._win)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _apply_scaled_pixmap(self) -> None:
        if self._source is not None:
            side = max(_QR_MIN_PX, min(_QR_MAX_PX, self._img.width() - _QUIET_ZONE * 2 or _QR_MIN_PX))
            scaled = self._source.scaled(
                side,
                side,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            self._img.setText("")
            self._img.setPixmap(scaled)
            return
        self._img.setPixmap(QtGui.QPixmap())
        self._img.setText(self._message or "")
        self._img.setWordWrap(True)


def connect_qr_should_show(win: QtWidgets.QWidget) -> bool:
    enabled = getattr(win, "chk_web_enabled", None)
    lan = getattr(win, "chk_web_lan", None)
    if enabled is None or lan is None:
        return False
    return bool(enabled.isChecked() and lan.isChecked())


def _load_qr_overlay_state(win: QtWidgets.QWidget) -> tuple[QtCore.QPoint | None, bool]:
    """Return (position in window coords, user_has_dragged) from global qr_overlay prefs."""
    from ui.ui_prefs import load_qr_overlay_prefs

    prefs = load_qr_overlay_prefs()
    user_positioned = bool(prefs.get("user_positioned"))
    floater: ConnectQrFloat | None = getattr(win, "_connect_qr_overlay", None)
    if isinstance(floater, ConnectQrFloat):
        floater.adjustSize()
        fw = max(floater.width(), 120)
        fh = max(floater.height(), 120)
    else:
        fw, fh = 140, 160

    norm = prefs.get("float_pos_norm")
    if isinstance(norm, (list, tuple)) and len(norm) >= 2:
        anchor = _qr_placement_anchor(win)
        try:
            nx = max(0.0, min(1.0, float(norm[0])))
            ny = max(0.0, min(1.0, float(norm[1])))
            cx = anchor.x() + int(nx * max(1, anchor.width()))
            cy = anchor.y() + int(ny * max(1, anchor.height()))
            return QtCore.QPoint(cx - fw // 2, cy - fh // 2), user_positioned
        except (TypeError, ValueError):
            pass

    pix = prefs.get("float_pos_pixels")
    if isinstance(pix, (list, tuple)) and len(pix) >= 2:
        try:
            return QtCore.QPoint(max(0, int(pix[0])), max(0, int(pix[1]))), user_positioned
        except (TypeError, ValueError):
            pass
    return None, user_positioned


def _persist_qr_float_pos(win: QtWidgets.QWidget) -> None:
    floater: ConnectQrFloat | None = getattr(win, "_connect_qr_overlay", None)
    if not isinstance(floater, ConnectQrFloat):
        return
    floater.adjustSize()
    fw = floater.width()
    fh = floater.height()
    pos = floater.pos()
    anchor = _qr_placement_anchor(win)
    cx = pos.x() + fw // 2
    cy = pos.y() + fh // 2
    aw = max(1, anchor.width())
    ah = max(1, anchor.height())
    nx = max(0.0, min(1.0, (cx - anchor.x()) / aw))
    ny = max(0.0, min(1.0, (cy - anchor.y()) / ah))
    from ui.ui_prefs import save_qr_overlay_prefs

    save_qr_overlay_prefs(
        float_pos_norm=(nx, ny),
        float_pos_pixels=[int(pos.x()), int(pos.y())],
        user_positioned=True,
    )


def _qr_placement_anchor(win: QtWidgets.QWidget) -> QtCore.QRect:
    """Region to center the QR on first launch (log pane / tabs / splitter top)."""
    log_view = getattr(win, "log_view", None)
    if isinstance(log_view, QtWidgets.QWidget) and log_view.isVisible():
        origin = log_view.mapTo(win, QtCore.QPoint(0, 0))
        return QtCore.QRect(origin, log_view.size())

    tabs = getattr(win, "_main_tabs", None)
    if isinstance(tabs, QtWidgets.QTabWidget) and tabs.isVisible():
        origin = tabs.mapTo(win, QtCore.QPoint(0, 0))
        return QtCore.QRect(origin, tabs.size())

    splitter = getattr(win, "_splitter", None)
    if isinstance(splitter, QtWidgets.QSplitter) and splitter.count() > 0:
        pane = splitter.widget(0)
        if pane is not None and pane.isVisible():
            origin = pane.mapTo(win, QtCore.QPoint(0, 0))
            return QtCore.QRect(origin, pane.size())

    margin = _FLOAT_MARGIN
    client_h = max(120, win.height() - _STATUS_BAR_RESERVE - margin * 2)
    client_w = max(120, win.width() - margin * 2)
    return QtCore.QRect(margin, margin, client_w, client_h)


def _default_qr_float_pos(win: QtWidgets.QWidget, floater: ConnectQrFloat) -> QtCore.QPoint:
    floater.adjustSize()
    fw = max(floater.width(), 120)
    fh = max(floater.height(), 120)
    anchor = _qr_placement_anchor(win)
    x = anchor.x() + max(0, (anchor.width() - fw) // 2)
    y = anchor.y() + max(0, (anchor.height() - fh) // 2)
    return QtCore.QPoint(x, y)


def _clamp_qr_float_pos(win: QtWidgets.QWidget) -> None:
    floater: ConnectQrFloat | None = getattr(win, "_connect_qr_overlay", None)
    if not isinstance(floater, ConnectQrFloat) or not floater.isVisible():
        return
    floater.adjustSize()
    fw = floater.width()
    fh = floater.height()
    max_x = max(_FLOAT_MARGIN, win.width() - fw - _FLOAT_MARGIN)
    max_y = max(_FLOAT_MARGIN, win.height() - fh - _STATUS_BAR_RESERVE - _FLOAT_MARGIN)
    pos = floater.pos()
    floater.move(
        min(max(_FLOAT_MARGIN, pos.x()), max_x),
        min(max(_FLOAT_MARGIN, pos.y()), max_y),
    )


def _place_qr_float(win: QtWidgets.QWidget, *, force: bool = False) -> None:
    floater: ConnectQrFloat | None = getattr(win, "_connect_qr_overlay", None)
    if not isinstance(floater, ConnectQrFloat):
        return
    if not force and getattr(win, "_connect_qr_placed", False) and floater.isVisible():
        _clamp_qr_float_pos(win)
        return
    saved, _positioned = _load_qr_overlay_state(win)
    if saved is not None:
        floater.move(saved)
    else:
        floater.move(_default_qr_float_pos(win, floater))
    win._connect_qr_placed = True
    _clamp_qr_float_pos(win)


class _ConnectQrResizeFilter(QtCore.QObject):
    def __init__(self, win: QtWidgets.QWidget) -> None:
        super().__init__(win)
        self._win = win

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if obj is self._win and event.type() == QtCore.QEvent.Type.Resize:
            floater: ConnectQrFloat | None = getattr(self._win, "_connect_qr_overlay", None)
            if isinstance(floater, ConnectQrFloat) and floater.isVisible():
                if not getattr(self._win, "_connect_qr_user_positioned", False):
                    floater.move(_default_qr_float_pos(self._win, floater))
                _clamp_qr_float_pos(self._win)
                floater.raise_()
        return False


def setup_connect_qr_overlay(win: QtWidgets.QWidget) -> None:
    """Attach floating QR widget to the main window."""
    existing = getattr(win, "_connect_qr_overlay", None)
    if not isinstance(existing, ConnectQrFloat):
        if existing is not None:
            existing.deleteLater()
        win._connect_qr_overlay = ConnectQrFloat(win)
    if not hasattr(win, "_connect_qr_user_hidden"):
        win._connect_qr_user_hidden = False
    if not hasattr(win, "_connect_qr_user_positioned"):
        _pos, positioned = _load_qr_overlay_state(win)
        win._connect_qr_user_positioned = positioned
    win._connect_qr_placed = False
    if not getattr(win, "_connect_qr_resize_filter_installed", False):
        filt = _ConnectQrResizeFilter(win)
        win.installEventFilter(filt)
        win._connect_qr_resize_filter = filt
        win._connect_qr_resize_filter_installed = True
    schedule_refresh_connect_qr_overlay(win)


def _sync_qr_api_cycle(win: QtWidgets.QWidget, api_active: bool) -> None:
    """Clear right-click hide when Web API + LAN turn off; re-show when they turn on."""
    prev = bool(getattr(win, "_connect_qr_api_active", False))
    win._connect_qr_api_active = api_active
    if not api_active:
        win._connect_qr_user_hidden = False
        return
    if api_active and not prev:
        win._connect_qr_user_hidden = False


def schedule_refresh_connect_qr_overlay(win: QtWidgets.QWidget, *, delay_ms: int = 120) -> None:
    """Debounced QR refresh (layout reflows were flashing hide/show)."""
    timer: QtCore.QTimer | None = getattr(win, "_connect_qr_refresh_timer", None)
    if timer is None:
        t = QtCore.QTimer(win)
        t.setSingleShot(True)
        t.timeout.connect(lambda w=win: refresh_connect_qr_overlay(w))
        win._connect_qr_refresh_timer = t
        timer = t
    timer.start(max(0, int(delay_ms)))


def _phone_tools_tab_active(win: QtWidgets.QWidget) -> bool:
    nav = getattr(win, "_tools_nav", None)
    if nav is None:
        return False
    item = nav.currentItem()
    if item is None:
        return False
    return item.text().strip().lower() == "phone"


def refresh_connect_qr_overlay(win: QtWidgets.QWidget) -> None:
    """Show/update/hide floating Connect QR from Web API + LAN prefs."""
    if getattr(win, "_connect_qr_overlay", None) is None:
        setup_connect_qr_overlay(win)
    floater: ConnectQrFloat | None = getattr(win, "_connect_qr_overlay", None)
    if not isinstance(floater, ConnectQrFloat):
        return

    if _phone_tools_tab_active(win):
        if floater.isVisible():
            floater.hide()
        win._connect_qr_last_show = False
        refresh = getattr(win, "_refresh_phone_tab_qr", None)
        if callable(refresh):
            refresh()
        return

    api_active = connect_qr_should_show(win)
    _sync_qr_api_cycle(win, api_active)
    show = api_active and not bool(getattr(win, "_connect_qr_user_hidden", False))

    if not show:
        if floater.isVisible():
            floater.hide()
        win._connect_qr_last_show = False
        return

    token_fn = getattr(win, "_web_token_from_ui", None)
    build_url = getattr(win, "_build_phone_setup_url", None)
    token = token_fn() if callable(token_fn) else None
    content_key = (token or "", build_url() if callable(build_url) else "")
    if (
        floater.isVisible()
        and getattr(win, "_connect_qr_last_show", False)
        and getattr(win, "_connect_qr_content_key", None) == content_key
    ):
        return

    if not token:
        floater.set_qr_content(message="Generate\na token\nin Phone")
    else:
        from ui.token_qr import make_token_qr_pixmap

        setup_url = build_url() if callable(build_url) else None
        pix = make_token_qr_pixmap(token, size=_QR_BASE_PX, setup_url=setup_url)
        if pix is None or pix.isNull():
            floater.set_qr_content(message="QR unavailable\n(pip install qrcode)")
        else:
            floater.set_qr_content(pixmap=pix)

    _place_qr_float(win, force=not floater.isVisible())
    if not floater.isVisible():
        floater.show()
    floater.raise_()
    if not getattr(win, "_connect_qr_user_positioned", False):
        _schedule_centered_qr_placement(win)
    win._connect_qr_last_show = True
    win._connect_qr_content_key = content_key


def _schedule_centered_qr_placement(win: QtWidgets.QWidget) -> None:
    """Re-center after layout/splitter settle so the QR is visible on startup."""

    def _recenter() -> None:
        if getattr(win, "_connect_qr_user_positioned", False):
            return
        _place_qr_float(win, force=True)

    for delay_ms in (0, 120, 280):
        QtCore.QTimer.singleShot(delay_ms, _recenter)


def schedule_qr_on_window_show(win: QtWidgets.QWidget) -> None:
    """Refresh floating QR after the window is shown (all layouts)."""
    schedule_refresh_connect_qr_overlay(win, delay_ms=0)
    schedule_refresh_connect_qr_overlay(win, delay_ms=160)


# Back-compat for older imports/tests.
def recommended_qr_lane_width(win: QtWidgets.QWidget | None = None) -> int:
    _ = win
    return 0

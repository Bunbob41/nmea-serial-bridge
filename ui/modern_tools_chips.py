"""Horizontal tools chip rail for Modern UI (top navigation mode)."""
from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6 import QtCore, QtGui, QtWidgets

from ui.fonts import emoji_ui_font
from ui.nav_chip_icons import NAV_CHIP_TILE_SIZE, apply_squircle_nav_chip

HEADER_EMBEDDED_CHIP_H = max(32, NAV_CHIP_TILE_SIZE)
_HEADER_EMBEDDED_CHIP_H = HEADER_EMBEDDED_CHIP_H
_HEADER_ICON_ONLY_CHIP_W = NAV_CHIP_TILE_SIZE
_HEADER_ICON_ONLY_DROPDOWN_W = NAV_CHIP_TILE_SIZE
_HEADER_CHIP_LABEL_PAD = 22
_HEADER_DROPDOWN_MENU_PAD = 24
_HEADER_CHIP_ROW_PAD = 4
_NAV_DROPDOWN_ARROW = "\u25be"  # ▾ — inline; native indicator hidden via QSS
_ICON_ONLY_ENTER_SLACK = 8
_ICON_ONLY_EXIT_SLACK = 16
_SQUIRCLE_CHIP_SPACING = 5


def _remove_squircle_filter(btn: QtWidgets.QWidget) -> None:
    """Remove the hover border filter installed by apply_squircle_nav_chip, if any."""
    filt = getattr(btn, "_squircle_hover_filter", None)
    if filt is not None:
        btn.removeEventFilter(filt)
        try:
            del btn._squircle_hover_filter  # type: ignore[attr-defined]
        except AttributeError:
            pass


def format_chip_dropdown_text(icon: str, label: str) -> str:
    """Pill label with trailing menu arrow (not the Qt menu-indicator box)."""
    core = f"{icon}  {label}".strip() if icon else label.strip()
    return f"{core}  {_NAV_DROPDOWN_ARROW}"


def ensure_dropdown_arrow(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.endswith(_NAV_DROPDOWN_ARROW) or stripped.endswith("\u25bc"):
        return stripped
    return f"{stripped}  {_NAV_DROPDOWN_ARROW}"


def _embedded_chip_text(icon: str, label: str) -> str:
    icon = icon.strip()
    label = label.strip()
    if icon and label:
        return f"{icon} {label}"
    return icon or label


def parse_dropdown_default_parts(default: str) -> tuple[str, str]:
    """Split stored dropdown default text into (icon, tier_label)."""
    text = (default or "").strip()
    if text.endswith(f"  {_NAV_DROPDOWN_ARROW}"):
        text = text[: -len(f"  {_NAV_DROPDOWN_ARROW}")].strip()
    parts = text.split("  ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "", text


def _chip_button_metrics(btn: QtWidgets.QWidget) -> QtGui.QFontMetrics:
    font = QtGui.QFont(btn.font())
    font.setPointSizeF(8.0 if btn.property("headerCompact") else 8.5)
    return QtGui.QFontMetrics(font)


def estimate_chip_button_width(
    btn: QtWidgets.QPushButton, *, icon_only: bool
) -> int:
    icon = str(btn.property("navIcon") or "").strip()
    label = str(btn.property("navLabel") or "").strip()
    if icon_only:
        return _HEADER_ICON_ONLY_CHIP_W
    text = _embedded_chip_text(icon, label)
    return _chip_button_metrics(btn).horizontalAdvance(text) + _HEADER_CHIP_LABEL_PAD


def estimate_dropdown_chip_width(
    btn: QtWidgets.QToolButton,
    *,
    icon_only: bool,
    active_icon: str = "",
    active_label: str = "",
) -> int:
    if icon_only:
        return _HEADER_ICON_ONLY_DROPDOWN_W
    default = str(btn.property("navDefaultText") or btn.text() or "").strip()
    tier_icon, tier_label = parse_dropdown_default_parts(default)
    icon = active_icon.strip() or tier_icon
    label = active_label.strip() or tier_label
    text = ensure_dropdown_arrow(_embedded_chip_text(icon, label))
    return _chip_button_metrics(btn).horizontalAdvance(text) + _HEADER_DROPDOWN_MENU_PAD


def estimate_embedded_chips_row_width(
    buttons: Sequence[QtWidgets.QPushButton],
    dropdowns: Sequence[QtWidgets.QToolButton],
    *,
    icon_only: bool,
    spacing: int = 4,
) -> int:
    count = len(buttons) + len(dropdowns)
    if count <= 0:
        return 0
    total = sum(estimate_chip_button_width(b, icon_only=icon_only) for b in buttons)
    total += sum(
        estimate_dropdown_chip_width(b, icon_only=icon_only) for b in dropdowns
    )
    total += spacing * max(0, count - 1)
    return total + _HEADER_CHIP_ROW_PAD


def sync_embedded_chip_inner_width(
    inner: QtWidgets.QWidget,
    buttons: Sequence[QtWidgets.QPushButton],
    dropdowns: Sequence[QtWidgets.QToolButton],
    *,
    icon_only: bool,
) -> int:
    """Lock inner track to natural chip row width so the header scroll area never clips."""
    spacing = 4
    lay = inner.layout()
    if lay is not None:
        spacing = lay.spacing()
    row_w = estimate_embedded_chips_row_width(
        buttons,
        dropdowns,
        icon_only=icon_only,
        spacing=spacing,
    )
    inner.setMinimumWidth(row_w)
    inner.setMaximumWidth(max(row_w, 1))
    inner.adjustSize()
    return row_w


_CHIP_FADE_W = 18


class ChipFadeEdge(QtWidgets.QWidget):
    """Soft edge hint when the chip rail overflows (no scrollbar)."""

    def __init__(self, parent: QtWidgets.QWidget | None, *, side: str) -> None:
        super().__init__(parent)
        self._side = "right" if str(side).lower().startswith("r") else "left"
        self.setObjectName(
            "modernHeaderChipFadeRight"
            if self._side == "right"
            else "modernHeaderChipFadeLeft"
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedWidth(_CHIP_FADE_W)
        self._fade_color = "#1e293b"
        self.hide()

    def set_fade_color(self, color: str) -> None:
        c = str(color or "").strip()
        if c and c != self._fade_color:
            self._fade_color = c
            self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        solid = QtGui.QColor(self._fade_color)
        clear = QtGui.QColor(solid)
        clear.setAlpha(0)
        grad = QtGui.QLinearGradient(0, 0, self.width(), 0)
        if self._side == "left":
            grad.setColorAt(0.0, solid)
            grad.setColorAt(1.0, clear)
        else:
            grad.setColorAt(0.0, clear)
            grad.setColorAt(1.0, solid)
        painter.fillRect(self.rect(), grad)


def sync_header_chip_fade_edges(
    scroll: QtWidgets.QScrollArea,
    fade_left: ChipFadeEdge | None,
    fade_right: ChipFadeEdge | None,
    *,
    fade_color: str,
) -> None:
    """Show left/right fades when scrolled chips hide off-screen."""
    if scroll is None or not scroll.isVisible():
        if fade_left is not None:
            fade_left.hide()
        if fade_right is not None:
            fade_right.hide()
        return
    host = scroll.parentWidget()
    if host is None:
        return
    bar = scroll.horizontalScrollBar()
    overflow = bar.maximum() > 0
    show_left = overflow and bar.value() > 2
    show_right = overflow and bar.value() < bar.maximum() - 2
    geo = scroll.geometry()
    h = max(geo.height(), scroll.height(), 24)
    y = geo.y()
    if fade_left is not None:
        fade_left.set_fade_color(fade_color)
        fade_left.setFixedHeight(h)
        fade_left.move(geo.x(), y)
        fade_left.setVisible(show_left)
        if show_left:
            fade_left.raise_()
    if fade_right is not None:
        fade_right.set_fade_color(fade_color)
        fade_right.setFixedHeight(h)
        fade_right.move(max(geo.x(), geo.x() + geo.width() - _CHIP_FADE_W), y)
        fade_right.setVisible(show_right)
        if show_right:
            fade_right.raise_()


def header_chip_scroll_policy(
    row_width: int,
    viewport_width: int,
) -> QtCore.Qt.ScrollBarPolicy:
    if row_width > max(viewport_width, 0):
        return QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    return QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def _ordered_header_chips(
    buttons: Sequence[QtWidgets.QPushButton],
    dropdowns: Sequence[QtWidgets.QToolButton],
) -> list[QtWidgets.QWidget]:
    chips: list[QtWidgets.QWidget] = list(buttons) + list(dropdowns)
    chips.sort(key=lambda w: w.x())
    return chips


def snap_header_chip_scroll(
    scroll: QtWidgets.QScrollArea,
    chips: Sequence[QtWidgets.QWidget],
) -> None:
    """Snap scroll so the viewport left edge never bisects a chip."""
    bar = scroll.horizontalScrollBar()
    if bar.maximum() <= 0:
        bar.setValue(0)
        return
    ordered = sorted(chips, key=lambda w: w.x())
    if not ordered:
        return
    pos = bar.value()
    for btn in ordered:
        left = btn.x() - pos
        if left < 0 and left + btn.width() > 0:
            bar.setValue(max(0, btn.x()))
            return


def reveal_active_header_chip(
    scroll: QtWidgets.QScrollArea,
    chips: Sequence[QtWidgets.QWidget],
    active: QtWidgets.QWidget | None,
) -> None:
    """Reset to start when chips fit; otherwise reveal the active chip without partial clips."""
    bar = scroll.horizontalScrollBar()
    viewport_w = max(scroll.viewport().width(), 1)
    inner = scroll.widget()
    row_w = inner.width() if inner is not None else 0
    if row_w <= viewport_w:
        bar.setValue(0)
        return
    if active is None:
        bar.setValue(0)
        snap_header_chip_scroll(scroll, chips)
        return
    margin = 2
    left = active.x() - bar.value()
    right = left + active.width()
    if left >= margin and right <= viewport_w - margin:
        snap_header_chip_scroll(scroll, chips)
        return
    if right > viewport_w - margin:
        bar.setValue(
            min(bar.maximum(), active.x() + active.width() - viewport_w + margin)
        )
    elif left < margin:
        bar.setValue(max(0, active.x() - margin))
    snap_header_chip_scroll(scroll, chips)


class ModernToolsChipScrollArea(QtWidgets.QScrollArea):
    """Single-row chip rail; mouse wheel scrolls horizontally."""

    scrolled = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modernToolsChipScroll")
        self.setWidgetResizable(False)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setMinimumWidth(0)
        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.viewport().setContentsMargins(0, 0, 0, 0)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta:
            bar = self.horizontalScrollBar()
            bar.setValue(bar.value() - delta)
            inner = self.widget()
            chips: list[QtWidgets.QWidget] = []
            if inner is not None:
                chips = inner.findChildren(
                    QtWidgets.QWidget,
                    options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly,
                )
            snap_header_chip_scroll(self, chips)
            self.scrolled.emit()
            event.accept()
            return
        super().wheelEvent(event)


def should_use_header_icon_only(
    avail_width: int,
    labeled_width: int,
    *,
    icon_width: int = 0,
    currently_icon_only: bool,
) -> bool:
    """Auto mode: prefer scrollable labeled chips; icons only when the pane is very narrow."""
    row_w = max(96, int(icon_width or 0))
    if row_w <= 96 and labeled_width > 0:
        row_w = max(96, min(int(labeled_width), 280))
    if currently_icon_only:
        return avail_width < row_w + _ICON_ONLY_EXIT_SLACK
    return avail_width < row_w


def apply_embedded_header_chip_style(
    btn: QtWidgets.QPushButton,
    *,
    compact: bool,
    icon_only: bool = False,
) -> None:
    label = str(btn.property("navLabel") or btn.toolTip() or "").strip()
    icon = str(btn.property("navIcon") or "").strip()
    sid = str(btn.property("navSid") or "").strip()
    if icon_only:
        if sid:
            apply_squircle_nav_chip(
                btn, sid=sid, style=btn.style(), emoji_fallback=icon
            )
        else:
            btn.setText(icon or (label[:1] if label else "?"))
            btn.setFont(emoji_ui_font(point_size=11.0))
            btn.setFixedHeight(HEADER_EMBEDDED_CHIP_H)
            btn.setFixedWidth(_HEADER_ICON_ONLY_CHIP_W)
        if label:
            btn.setToolTip(label)
        btn.setProperty("headerCompact", compact)
        btn.setProperty("headerIconOnly", True)
        btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
    elif compact:
        btn.setIcon(QtGui.QIcon())
        text = _embedded_chip_text(icon, label)
        btn.setText(text)
        if label:
            btn.setToolTip(label)
        btn.setProperty("headerCompact", True)
        btn.setProperty("headerIconOnly", False)
        btn.setFont(emoji_ui_font(point_size=8.5))
        btn.setFixedHeight(HEADER_EMBEDDED_CHIP_H)
        btn_w = _chip_button_metrics(btn).horizontalAdvance(text) + _HEADER_CHIP_LABEL_PAD
        btn.setFixedWidth(max(btn_w, _HEADER_ICON_ONLY_CHIP_W))
        btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
    else:
        # Clear any squircle inline stylesheet and hover filter before showing label
        btn.setStyleSheet("")
        _remove_squircle_filter(btn)
        btn.setIcon(QtGui.QIcon())
        text = f"{icon}  {label}".strip() if icon else label
        btn.setText(text)
        btn.setProperty("headerCompact", False)
        btn.setProperty("headerIconOnly", False)
        btn.setProperty("navGeminiTile", "false")
        btn.setFont(emoji_ui_font(point_size=9.0))
        btn.setFixedHeight(HEADER_EMBEDDED_CHIP_H)
        btn_w = _chip_button_metrics(btn).horizontalAdvance(text) + _HEADER_CHIP_LABEL_PAD
        btn.setFixedWidth(btn_w)
        btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
    style = btn.style()
    style.unpolish(btn)
    style.polish(btn)


def apply_embedded_header_dropdown_style(
    btn: QtWidgets.QToolButton,
    *,
    compact: bool,
    icon_only: bool = False,
    active_icon: str = "",
    active_label: str = "",
    active_sid: str = "",
) -> None:
    default = str(btn.property("navDefaultText") or btn.text() or "").strip()
    tier_icon, tier_label = parse_dropdown_default_parts(default)
    icon = active_icon.strip() or tier_icon
    label = active_label.strip() or tier_label
    if icon_only:
        tile_sid = (
            str(active_sid or "").strip()
            or str(btn.property("navSid") or "").strip()
            or str(btn.property("navTierKey") or "").strip()
        )
        if tile_sid:
            apply_squircle_nav_chip(
                btn,
                sid=tile_sid,
                style=btn.style(),
                emoji_fallback=icon,
            )
        else:
            text = icon or (label[:1] if label else "?")
            btn.setText(text)
            btn.setFont(emoji_ui_font(point_size=11.0))
            btn.setFixedHeight(HEADER_EMBEDDED_CHIP_H)
            btn.setFixedWidth(_HEADER_ICON_ONLY_DROPDOWN_W)
        btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        btn.setProperty("headerCompact", compact)
        btn.setProperty("headerIconOnly", True)
        btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
    elif compact:
        btn.setIcon(QtGui.QIcon())
        btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        text = ensure_dropdown_arrow(_embedded_chip_text(icon, label))
        btn.setText(text)
        btn.setProperty("headerCompact", True)
        btn.setProperty("headerIconOnly", False)
        btn.setFont(emoji_ui_font(point_size=8.5))
        btn.setFixedHeight(HEADER_EMBEDDED_CHIP_H)
        btn_w = _chip_button_metrics(btn).horizontalAdvance(text) + _HEADER_DROPDOWN_MENU_PAD
        btn.setFixedWidth(max(btn_w, _HEADER_ICON_ONLY_DROPDOWN_W))
        btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
    else:
        # Clear any squircle inline stylesheet and hover filter before showing label
        btn.setStyleSheet("")
        _remove_squircle_filter(btn)
        btn.setIcon(QtGui.QIcon())
        text = ensure_dropdown_arrow(default)
        btn.setText(text)
        btn.setProperty("headerCompact", False)
        btn.setProperty("headerIconOnly", False)
        btn.setProperty("navGeminiTile", "false")
        btn.setFont(emoji_ui_font(point_size=9.0))
        btn.setFixedHeight(HEADER_EMBEDDED_CHIP_H)
        btn_w = _chip_button_metrics(btn).horizontalAdvance(text) + _HEADER_DROPDOWN_MENU_PAD
        btn.setFixedWidth(max(btn_w, _HEADER_ICON_ONLY_DROPDOWN_W))
        btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
    style = btn.style()
    style.unpolish(btn)
    style.polish(btn)


def make_chip_group_separator() -> QtWidgets.QFrame:
    sep = QtWidgets.QFrame()
    sep.setObjectName("modernToolsChipSep")
    sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    sep.setFixedWidth(1)
    sep.setFixedHeight(22)
    return sep


class _ChipDropdownMenuContextFilter(QtCore.QObject):
    """Right-click a dropdown row to open a child-specific menu (e.g. Theme presets)."""

    def __init__(
        self,
        menu: QtWidgets.QMenu,
        *,
        child_sids: frozenset[str],
        on_child_context: Callable[[str, QtCore.QPoint], None],
    ) -> None:
        super().__init__(menu)
        self._menu = menu
        self._child_sids = child_sids
        self._on_child_context = on_child_context

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if obj is not self._menu or event.type() != QtCore.QEvent.Type.MouseButtonPress:
            return False
        me = event
        if not isinstance(me, QtGui.QMouseEvent):
            return False
        if me.button() != QtCore.Qt.MouseButton.RightButton:
            return False
        action = self._menu.actionAt(me.pos())
        if action is None:
            return False
        sid = str(action.property("navChildSid") or "").strip()
        if sid not in self._child_sids:
            return False
        self._on_child_context(sid, self._menu.mapToGlobal(me.pos()))
        return True


def make_chip_dropdown_button(
    *,
    tier_key: str,
    label: str,
    icon: str,
    children: list[tuple[str, str, str, int]],
    on_pick: Callable[[str], None],
    on_cycle: Callable[[str, list[str]], None],
    utility_actions: list[tuple[str, str, Callable[[], None]]] | None = None,
    child_context_menu_sids: frozenset[str] | None = None,
    on_child_context_menu: Callable[[str, QtCore.QPoint], None] | None = None,
) -> QtWidgets.QToolButton:
    """Dropdown chip for grouped nav tiers (Logging, Bench Tools)."""
    btn = QtWidgets.QToolButton()
    btn.setObjectName("modernToolsNavChipMenu")
    text = format_chip_dropdown_text(icon, label)
    btn.setText(text)
    btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
    btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
    btn.setAutoRaise(False)
    btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(32)
    btn.setProperty("navTierKey", tier_key)
    btn.setProperty("navSid", tier_key)
    btn.setProperty("navActive", False)
    btn.setProperty("navDefaultText", text)
    child_sids = [sid for sid, _lbl, _icon, _idx in children]
    btn.setProperty("navChildSids", child_sids)
    btn.setProperty("navActiveChildSid", "")

    menu = QtWidgets.QMenu(btn)
    menu.setObjectName("modernToolsNavChipMenuPopup")
    for sid, child_label, child_icon, _idx in children:
        action = menu.addAction(f"{child_icon}  {child_label}".strip())
        action.setProperty("navChildSid", sid)
        if sid == "theme":
            action.setToolTip(
                "Left-click: Theme studio. Right-click: apply a built-in palette "
                "or saved preset."
            )
        action.triggered.connect(lambda _checked=False, s=sid: on_pick(s))
    if utility_actions:
        menu.addSeparator()
        for util_label, util_icon, util_cb in utility_actions:
            util_action = menu.addAction(f"{util_icon}  {util_label}".strip())
            util_action.triggered.connect(util_cb)
    btn.setMenu(menu)
    if child_context_menu_sids and on_child_context_menu is not None:
        filt = _ChipDropdownMenuContextFilter(
            menu,
            child_sids=child_context_menu_sids,
            on_child_context=on_child_context_menu,
        )
        menu.installEventFilter(filt)
        btn._nav_child_context_filter = filt  # keep alive
    btn.clicked.connect(
        lambda _checked=False, sids=list(child_sids): on_cycle(tier_key, sids)
    )
    tip_lines = [f"{child_icon}  {child_label}" for _sid, child_label, child_icon, _idx in children]
    btn.setToolTip(
        f"{label} — click to cycle, arrow for menu — " + " · ".join(tip_lines)
    )
    return btn

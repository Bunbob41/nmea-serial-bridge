"""Survey top bar — bordered chips with drag-to-reorder (no manager dialog).

Layout invariant (TOPBAR_ALWAYS_FILL_TRACK): every visible chip uses equal
horizontal stretch so the bar always fills the window width — no empty gutter.
Labels are full text when a chip's share fits; otherwise a single centered letter.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

DEFAULT_TOPBAR_ORDER: tuple[str, ...] = (
    "view",
    "presets",
    "recent",
    "hud",
    "tools",
    "randomize_theme",
    "standardize_theme",
    "ui_editor",
    "shortcuts",
    "copy_stats",
    "ui_switch",
)

PIN_RIGHT_KEYS: frozenset[str] = frozenset({"ui_switch"})

# Readable short text when a tile is too narrow for the full label (never opaque N/O/I).
TOPBAR_SHORT_LABEL: dict[str, str] = {
    "view": "View",
    "presets": "Presets",
    "recent": "Recent",
    "hud": "HUD",
    "tools": "Tools",
    "randomize_theme": "Rand",
    "standardize_theme": "Strd",
    "ui_editor": "UI",
    "shortcuts": "Shortcuts",
    "copy_stats": "Stats",
    "ui_switch": "Layout",
}

# Preferred compact words before abbreviations (try smaller font first).
TOPBAR_COMPACT_WORD_LABEL: dict[str, str] = {
    "randomize_theme": "Random",
    "standardize_theme": "Standard",
}

# Back-compat alias for tests.
TOPBAR_COMPACT_LETTER = TOPBAR_SHORT_LABEL

COMPACT_CHIP_WIDTH = 54
# Hysteresis only when leaving short-label mode (avoids expand/collapse flicker).
COMPACT_EXIT_ABOVE_PX = 80
EXPANDED_FIT_SLACK_PX = 12
CHIP_TEXT_PAD = 12
CHIP_MARGINS_EXPANDED = (7, 4, 3, 4)
CHIP_MARGINS_COMPACT = (4, 3, 2, 3)
_GRIP_WIDTH = 12
_RESIZE_EDGE_WIDTH = 5
_PROP_FULL = "topBarFullText"
_WIDGET_SIZE_MAX = 16777215
_MIN_CHIP_FONT_PT = 8.0
# Enforced in SurveyTopBar._apply_spring_layout — do not reintroduce content-sized gaps.
TOPBAR_ALWAYS_FILL_TRACK = True


def text_body_width(fm: QtGui.QFontMetrics, text: str) -> int:
    """Width for label text plus minimal horizontal breathing room."""
    return fm.horizontalAdvance(text.strip() or "?") + CHIP_TEXT_PAD


def compact_display_for(key: str, full_label: str) -> str:
    """Short readable label when the full title does not fit."""
    short = TOPBAR_SHORT_LABEL.get(key)
    if short:
        return short
    text = full_label.strip()
    if len(text) <= 8:
        return text
    words = text.split()
    if len(words) >= 2:
        return (words[0][:4] + " " + words[1][:4]).strip()
    return text[:7]


def compact_letter_for(key: str, full_label: str) -> str:
    return compact_display_for(key, full_label)


def preferred_compact_for(key: str, full_label: str) -> str:
    preferred = TOPBAR_COMPACT_WORD_LABEL.get(key)
    if preferred:
        return preferred
    return compact_display_for(key, full_label)


def configure_topbar_button(
    btn: QtWidgets.QToolButton,
    full_text: str,
    *,
    tooltip: Optional[str] = None,
) -> None:
    """Store full title; bar switches to one-letter tiles when narrow."""
    btn.setText(full_text)
    btn.setProperty(_PROP_FULL, full_text)
    btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
    btn.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    tip = tooltip if tooltip else full_text
    btn.setToolTip(tip)


def distribute_equal_widths(inner_total: int, count: int) -> list[int]:
    """Split inner track pixels across chips (remainder → last tiles)."""
    if count <= 0:
        return []
    inner_total = max(inner_total, count * COMPACT_CHIP_WIDTH)
    base = inner_total // count
    rem = inner_total % count
    return [base + (1 if i < rem else 0) for i in range(count)]


def snap_insert_index(global_x: int, chip_rects: list[tuple[str, QtCore.QRect]]) -> int:
    if not chip_rects:
        return 0
    for i, (_key, rect) in enumerate(chip_rects):
        if global_x < rect.center().x():
            return i
    return len(chip_rects)


def choose_compact_mode(
    *,
    avail: int,
    need_expanded: int,
    need_compact: int,
    currently_compact: bool,
) -> bool:
    """Letter tiles unless full labels fully fit — never clip overlapping chips."""
    if need_compact <= 0:
        return False
    if avail < need_compact:
        return True
    if currently_compact:
        return avail < need_expanded + COMPACT_EXIT_ABOVE_PX
    return avail < need_expanded + EXPANDED_FIT_SLACK_PX


def normalize_topbar_order(order: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for key in order:
        k = str(key).strip()
        if k == "demo":
            k = "ui_editor"
        if k == "hidden_tabs":
            continue
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    for key in DEFAULT_TOPBAR_ORDER:
        if key not in seen:
            out.append(key)
            seen.add(key)
    return out


class TopBarResizeEdge(QtWidgets.QWidget):
    """Right-edge drag target to change this tile's width."""

    def __init__(self, chip: "TopBarChip", parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent or chip)
        self._chip = chip
        self.setObjectName("topBarResizeEdge")
        self.setFixedWidth(_RESIZE_EDGE_WIDTH)
        self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
        self.setToolTip("Drag left/right to resize this tile")


class TopBarChip(QtWidgets.QFrame):
    """Bordered box: label, reorder grip, resize edge; letter mode when narrow."""

    def __init__(
        self,
        key: str,
        inner: QtWidgets.QWidget,
        *,
        full_label: str = "",
        pin_right: bool = False,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._key = key
        self._pin_right = pin_right
        self._inner = inner
        self._full_label = full_label
        self._short = compact_display_for(key, full_label)
        self._compact_preferred = preferred_compact_for(key, full_label)
        self._compact = False
        self._inner_base_font = inner.font() if isinstance(inner, QtWidgets.QToolButton) else None
        self.setObjectName("topBarChip")
        if hasattr(self, "setClipChildren"):
            self.setClipChildren(True)
        self.setProperty("dragging", False)
        self.setProperty("compact", False)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._lay = QtWidgets.QHBoxLayout(self)
        self._lay.setContentsMargins(*CHIP_MARGINS_EXPANDED)
        self._lay.setSpacing(3)
        inner.setParent(self)
        inner.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._lay.addWidget(inner, 1, QtCore.Qt.AlignmentFlag.AlignCenter)
        self._grip = QtWidgets.QLabel("⋮⋮")
        self._grip.setObjectName("topBarDragGrip")
        self._grip.setFixedWidth(_GRIP_WIDTH)
        self._grip.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._grip.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        self._grip.setToolTip("Drag to reorder this tile on the top bar")
        self._lay.addWidget(self._grip, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._resize_edge = TopBarResizeEdge(self, self)
        self._lay.addWidget(self._resize_edge, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)

    def _body_width_expanded(self) -> int:
        if isinstance(self._inner, QtWidgets.QToolButton):
            full = str(self._inner.property(_PROP_FULL) or self._full_label)
            return text_body_width(self._inner.fontMetrics(), full)
        return self._inner.sizeHint().width()

    def _body_width_compact(self) -> int:
        if isinstance(self._inner, QtWidgets.QToolButton):
            return text_body_width(self._inner.fontMetrics(), self._short)
        return COMPACT_CHIP_WIDTH - _GRIP_WIDTH - 10

    def natural_total_width(self, *, compact: bool) -> int:
        margins = CHIP_MARGINS_COMPACT if compact else CHIP_MARGINS_EXPANDED
        body = self._body_width_compact() if compact else self._body_width_expanded()
        return (
            body
            + _GRIP_WIDTH
            + _RESIZE_EDGE_WIDTH
            + margins[0]
            + margins[2]
            + self._lay.spacing()
            + 2
        )

    def expanded_min_width(self) -> int:
        return self.natural_total_width(compact=False)

    def body_slot_width(self, outer_w: int, *, compact: bool) -> int:
        margins = CHIP_MARGINS_COMPACT if compact else CHIP_MARGINS_EXPANDED
        chrome = _GRIP_WIDTH + _RESIZE_EDGE_WIDTH + margins[0] + margins[2] + self._lay.spacing() * 2
        return max(outer_w - chrome, 12)

    def full_label_fits(self, outer_w: int) -> bool:
        """True when full text fits in the label area (never clip with …)."""
        return self._body_width_expanded() <= self.body_slot_width(outer_w, compact=False)

    def set_spring_width(self, outer_w: int) -> None:
        """Equal tile width — fills the track with no trailing gutter."""
        w = max(int(outer_w), COMPACT_CHIP_WIDTH)
        self.setFixedWidth(w)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        slot = self.body_slot_width(w, compact=self._compact)
        if isinstance(self._inner, QtWidgets.QToolButton):
            self._inner.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            self._inner.setMinimumWidth(0)
            cap = max(slot, 0) if self._compact else _WIDGET_SIZE_MAX
            self._inner.setMaximumWidth(cap)
            self._sync_inner_label_width(slot)

    def set_compact(self, compact: bool) -> None:
        if self._compact == compact:
            return
        self._compact = compact
        self.setProperty("compact", compact)
        if compact:
            self._lay.setContentsMargins(*CHIP_MARGINS_COMPACT)
            if isinstance(self._inner, QtWidgets.QToolButton):
                self._inner.setText(self._short)
            tip = self._full_label or str(
                self._inner.property(_PROP_FULL) if isinstance(self._inner, QtWidgets.QToolButton) else ""
            )
            if tip:
                self.setToolTip(tip)
                if isinstance(self._inner, QtWidgets.QToolButton):
                    self._inner.setToolTip(tip)
        else:
            self._lay.setContentsMargins(*CHIP_MARGINS_EXPANDED)
            if isinstance(self._inner, QtWidgets.QToolButton):
                full = str(self._inner.property(_PROP_FULL) or self._full_label)
                self._inner.setText(full)
            tip = self._full_label
            self.setToolTip(tip)
            if isinstance(self._inner, QtWidgets.QToolButton):
                self._inner.setToolTip(tip)
        self._sync_inner_label_width(self.body_slot_width(self.width(), compact=self._compact))
        self.updateGeometry()

    def _sync_inner_label_width(self, slot: int) -> None:
        """Prefer readable words with smaller font; fallback to abbreviations."""
        if not isinstance(self._inner, QtWidgets.QToolButton):
            return
        base = QtGui.QFont(self._inner_base_font or self._inner.font())
        candidates = (
            [self._compact_preferred, self._short]
            if self._compact
            else [str(self._inner.property(_PROP_FULL) or self._full_label).strip() or self._inner.text() or "?"]
        )
        slot = max(int(slot), 24)
        chosen_text = candidates[-1]
        chosen_font = QtGui.QFont(base)
        for text in candidates:
            text = (text or "").strip() or "?"
            test_font = QtGui.QFont(base)
            pt = float(test_font.pointSizeF() if test_font.pointSizeF() > 0 else test_font.pointSize())
            if pt <= 0:
                pt = 9.0
            while pt >= _MIN_CHIP_FONT_PT:
                test_font.setPointSizeF(pt)
                need = text_body_width(QtGui.QFontMetrics(test_font), text)
                if need <= slot:
                    chosen_text = text
                    chosen_font = QtGui.QFont(test_font)
                    break
                pt -= 0.5
            else:
                continue
            break
        self._inner.setFont(chosen_font)
        self._inner.setText(chosen_text)
        self._inner.setMinimumWidth(0)

    def key(self) -> str:
        return self._key

    def pin_right(self) -> bool:
        return self._pin_right

    def grip(self) -> QtWidgets.QLabel:
        return self._grip

    def resize_edge(self) -> TopBarResizeEdge:
        return self._resize_edge

    def set_dragging(self, on: bool) -> None:
        self.setProperty("dragging", on)
        self._grip.setCursor(
            QtCore.Qt.CursorShape.ClosedHandCursor
            if on
            else QtCore.Qt.CursorShape.OpenHandCursor
        )
        self.style().unpolish(self)
        self.style().polish(self)


class SurveyTopBar(QtWidgets.QWidget):
    """Horizontal bar of draggable chips; always fills window width (spring layout)."""

    order_changed = QtCore.Signal(list)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("surveyMenuBar")
        self._chips: dict[str, TopBarChip] = {}
        self._labels: dict[str, str] = {}
        self._order: list[str] = []
        self._hidden: set[str] = set()
        self._pin_right: set[str] = set(PIN_RIGHT_KEYS)
        self._compact_mode = False
        self._launch_readable_labels = False
        self._last_visible_sig: tuple[str, ...] = ()
        self._last_spring_sig: tuple[object, ...] = ()
        self._spring_layout_busy = False
        self._host_width_fitted = False
        self._spring_layout_timer = QtCore.QTimer(self)
        self._spring_layout_timer.setSingleShot(True)
        self._spring_layout_timer.timeout.connect(self._apply_spring_layout)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._track = QtWidgets.QWidget(self)
        self._track.setObjectName("surveyTopBarTrack")
        self._track.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._track_lay = QtWidgets.QHBoxLayout(self._track)
        self._track_lay.setContentsMargins(6, 3, 6, 3)
        self._track_lay.setSpacing(6)
        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._track, 1)
        self._drop_line = QtWidgets.QFrame(self._track)
        self._drop_line.setObjectName("topBarDropLine")
        self._drop_line.setFixedWidth(2)
        self._drop_line.hide()
        self._drag_key: Optional[str] = None
        self._resize_key: Optional[str] = None
        self._resize_start_x = 0
        self._resize_start_widths: list[int] = []
        self._chip_weights: dict[str, float] = {}
        self._host_window: Optional[QtWidgets.QWidget] = None
        self._on_order_persist: Optional[
            Callable[[list[str], set[str], dict[str, float]], None]
        ] = None

    def set_persist_callback(
        self, cb: Callable[[list[str], set[str], dict[str, float]], None]
    ) -> None:
        self._on_order_persist = cb

    def set_host_window(self, host: QtWidgets.QWidget) -> None:
        """Main window — used for width before the bar has been laid out."""
        self._host_window = host

    def _avail_width(self) -> int:
        w = max(self._track.width(), self.width())
        if w < 200 and self._host_window is not None:
            w = max(w, self._host_window.width())
        win = self.window()
        if w < 200 and win is not None:
            w = max(w, win.width())
        return max(w - 8, 0)

    def _effective_avail_width(self) -> int:
        """Bar track width, or main window width before first layout pass."""
        avail = self._avail_width()
        if self._host_window is not None:
            avail = max(avail, self._host_window.width() - 16)
        return avail

    def _schedule_spring_layout(self, attempt: int = 0) -> None:
        """Coalesce layout work — avoids resize→layout→resize storms (memory/CPU freeze)."""
        if self._effective_avail_width() < 120 and attempt < 8:
            QtCore.QTimer.singleShot(
                50, lambda a=attempt + 1: self._schedule_spring_layout(a)
            )
            return
        self._spring_layout_timer.start(16)

    def _track_inner_width(self) -> int:
        avail = max(self._track.width(), self.width(), 0)
        if self._host_window is not None:
            avail = max(avail, self._host_window.width())
        win = self.window()
        if win is not None:
            avail = max(avail, win.width())
        m = self._track_lay.contentsMargins()
        return max(avail - m.left() - m.right(), 0)

    def chip_weights(self) -> dict[str, float]:
        return {k: max(float(self._chip_weights.get(k, 1.0)), 0.25) for k in self._chips}

    def _chip_widths(self, keys: list[str]) -> list[int]:
        if not keys:
            return []
        spacing = self._track_lay.spacing() * max(0, len(keys) - 1)
        inner = max(self._track_inner_width() - spacing, len(keys) * COMPACT_CHIP_WIDTH)
        weights = [max(self._chip_weights.get(k, 1.0), 0.25) for k in keys]
        total_w = sum(weights)
        widths = [max(int(inner * wt / total_w), COMPACT_CHIP_WIDTH) for wt in weights]
        for i, key in enumerate(keys):
            floor = self._chips[key].natural_total_width(compact=True)
            widths[i] = max(widths[i], floor)
        drift = inner - sum(widths)
        if widths and drift > 0:
            widths[-1] = max(widths[-1] + drift, widths[-1])
        elif widths and drift < 0:
            for i in range(len(widths) - 1, -1, -1):
                if drift >= 0:
                    break
                take = min(-drift, widths[i] - COMPACT_CHIP_WIDTH)
                if take > 0:
                    widths[i] -= take
                    drift += take
        return widths

    def register(
        self,
        key: str,
        label: str,
        inner: QtWidgets.QWidget,
        *,
        pin_right: bool = False,
    ) -> TopBarChip:
        if isinstance(inner, QtWidgets.QToolButton):
            configure_topbar_button(inner, label, tooltip=label)
        chip = TopBarChip(
            key,
            inner,
            full_label=label,
            pin_right=pin_right,
            parent=self._track,
        )
        chip.grip().installEventFilter(self)
        chip.resize_edge().installEventFilter(self)
        self._chips[key] = chip
        self._labels[key] = label
        if pin_right:
            self._pin_right.add(key)
        if key not in self._order:
            self._order.append(key)
        return chip

    def chip(self, key: str) -> Optional[TopBarChip]:
        return self._chips.get(key)

    def set_prefs(
        self,
        order: list[str],
        hidden: set[str],
        chip_weights: Optional[dict[str, float]] = None,
    ) -> None:
        self._order = normalize_topbar_order(order)
        self._hidden = {str(x) for x in hidden if str(x).strip()}
        self._hidden.discard("view")
        if chip_weights:
            for k, v in chip_weights.items():
                if k in self._chips or k in DEFAULT_TOPBAR_ORDER:
                    try:
                        self._chip_weights[str(k)] = max(float(v), 0.25)
                    except (TypeError, ValueError):
                        pass
        self.rebuild()

    def order(self) -> list[str]:
        return list(self._order)

    def hidden(self) -> set[str]:
        return set(self._hidden)

    def hide_chip(self, key: str) -> None:
        if key == "view":
            return
        self._hidden.add(key)
        chip = self._chips.get(key)
        if chip is not None:
            chip.hide()
        self.rebuild()
        self._emit_persist()

    def show_all_chips(self) -> None:
        self._hidden.clear()
        self.rebuild()
        self._emit_persist()

    def reset_layout(self) -> None:
        self._order = list(DEFAULT_TOPBAR_ORDER)
        self._hidden.clear()
        self._chip_weights.clear()
        self.rebuild()
        self._emit_persist()

    def _visible_keys(self) -> list[str]:
        order = [k for k in self._order if k in self._chips]
        return [k for k in order if k not in self._hidden]

    def _expanded_width_needed(self, keys: list[str]) -> int:
        if not keys:
            return 0
        m = self._track_lay.contentsMargins()
        total = m.left() + m.right() + self._track_lay.spacing() * max(0, len(keys) - 1)
        for key in keys:
            total += self._chips[key].expanded_min_width()
        return total

    def expanded_bar_width(self) -> int:
        """Width needed to show full labels (content-sized chips)."""
        return self._expanded_width_needed(self._visible_keys()) + 24

    def prefer_expanded_on_show(self, host: QtWidgets.QWidget) -> None:
        """Launch: prefer full labels when the window is wide enough; else readable shorts."""
        self.set_host_window(host)
        self._launch_readable_labels = True
        self._schedule_spring_layout()

    def ensure_host_fits_full_labels(self, host: QtWidgets.QWidget) -> None:
        """Widen the main window once on launch so top-bar titles are not clipped."""
        self.set_host_window(host)
        if self._host_width_fitted:
            return
        self._host_width_fitted = True
        need = self.expanded_bar_width()
        if need <= 0:
            return
        screen = host.screen()
        cap = int(screen.availableGeometry().width() * 0.96) if screen is not None else 2400
        target_w = min(max(need + 24, int(host.minimumWidth())), cap)
        if host.width() < target_w:
            host.resize(target_w, host.height())

    def sync_host_minimum_width(self, host: QtWidgets.QWidget) -> None:
        """Floor window width so letter mode still fits; expanded mode uses hysteresis."""
        floor = self._compact_width_needed(self._visible_keys()) + 32
        if floor > 0:
            host.setMinimumWidth(max(int(host.minimumWidth()), floor))

    def _compact_width_needed(self, keys: list[str]) -> int:
        if not keys:
            return 0
        m = self._track_lay.contentsMargins()
        total = m.left() + m.right() + self._track_lay.spacing() * max(0, len(keys) - 1)
        for key in keys:
            total += max(COMPACT_CHIP_WIDTH, self._chips[key].natural_total_width(compact=True))
        return total

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._schedule_spring_layout()

    def _apply_spring_layout(self) -> None:
        """Rule: visible tiles always share the full top-bar width (no empty track)."""
        if self._spring_layout_busy:
            return
        keys = self._visible_keys()
        if not keys:
            return
        widths = self._chip_widths(keys)
        if not widths:
            return
        spacing = self._track_lay.spacing() * max(0, len(keys) - 1)
        inner = max(self._track_inner_width() - spacing, len(keys) * COMPACT_CHIP_WIDTH)
        drift = inner - sum(widths)
        if widths and drift > 0:
            widths[-1] += drift
        need_full = self._expanded_width_needed(keys)
        need_compact = self._compact_width_needed(keys)
        use_compact = choose_compact_mode(
            avail=inner,
            need_expanded=need_full + EXPANDED_FIT_SLACK_PX,
            need_compact=need_compact,
            currently_compact=self._compact_mode,
        )
        if self._launch_readable_labels:
            if inner < need_full + EXPANDED_FIT_SLACK_PX:
                use_compact = True
            else:
                self._launch_readable_labels = False
        spring_sig = (tuple(keys), tuple(widths), use_compact, inner)
        if spring_sig == self._last_spring_sig:
            return
        self._spring_layout_busy = True
        changed = False
        try:
            self._apply_spring_layout_body(
                keys, widths, use_compact, changed_start=changed
            )
            self._last_spring_sig = spring_sig
        finally:
            self._spring_layout_busy = False

    def _apply_spring_layout_body(
        self,
        keys: list[str],
        widths: list[int],
        use_compact: bool,
        *,
        changed_start: bool,
    ) -> None:
        sig = tuple(keys)
        changed = changed_start
        for key, w in zip(keys, widths):
            chip = self._chips[key]
            compact = use_compact
            if chip._compact != compact:
                chip.set_compact(compact)
                changed = True
            chip.set_spring_width(w)
        self._compact_mode = bool(use_compact)
        if not use_compact:
            self._launch_readable_labels = False
        for i in range(self._track_lay.count()):
            self._track_lay.setStretch(i, 0)
        if changed or sig != self._last_visible_sig:
            self._last_visible_sig = sig
            self._update_bar_height()
        self._track_lay.activate()
        self._track.updateGeometry()
        self.updateGeometry()

    def rebuild(self) -> None:
        while self._track_lay.count():
            item = self._track_lay.takeAt(0)
            w = item.widget()
            if w is not None and w is not self._drop_line:
                w.setParent(self._track)
        order = [k for k in self._order if k in self._chips]
        for k in self._chips:
            if k not in order:
                order.append(k)
        self._order = order
        visible = self._visible_keys()
        visible_set = set(visible)
        for key, chip in self._chips.items():
            if key in visible_set:
                continue
            chip.hide()
        left = [k for k in visible if k not in self._pin_right]
        right = [k for k in visible if k in self._pin_right]
        for k in left:
            chip = self._chips[k]
            chip.show()
            self._track_lay.addWidget(chip, 0)
        for k in right:
            chip = self._chips[k]
            chip.show()
            self._track_lay.addWidget(chip, 0)
        self._last_visible_sig = ()
        self._schedule_spring_layout()
        self._track.updateGeometry()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._schedule_spring_layout()

    def _visible_chip_rects(self, exclude_key: Optional[str] = None) -> list[tuple[str, QtCore.QRect]]:
        out: list[tuple[str, QtCore.QRect]] = []
        for i in range(self._track_lay.count()):
            item = self._track_lay.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w is None or w is self._drop_line:
                continue
            if not isinstance(w, TopBarChip):
                continue
            key = w.key()
            if key == exclude_key:
                continue
            out.append((key, w.geometry()))
        return out

    def _update_bar_height(self) -> None:
        h = 0
        for chip in self._chips.values():
            if chip.isVisible():
                h = max(h, chip.sizeHint().height())
        self.setFixedHeight(max(h + 8, 30))

    def _emit_persist(self) -> None:
        self.order_changed.emit(list(self._order))
        if self._on_order_persist is not None:
            self._on_order_persist(list(self._order), set(self._hidden), self.chip_weights())

    def _begin_drag(self, key: str, global_pos: QtCore.QPoint) -> None:
        self._drag_key = key
        chip = self._chips.get(key)
        if chip is not None:
            chip.set_dragging(True)
            chip.raise_()
        QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.CursorShape.ClosedHandCursor)

    def _end_drag(self) -> None:
        key = self._drag_key
        self._drag_key = None
        self._drop_line.hide()
        if key is not None:
            chip = self._chips.get(key)
            if chip is not None:
                chip.set_dragging(False)
        while QtGui.QGuiApplication.overrideCursor() is not None:
            QtGui.QGuiApplication.restoreOverrideCursor()

    def _begin_resize(self, key: str, global_x: int) -> None:
        self._resize_key = key
        self._resize_start_x = global_x
        keys = self._visible_keys()
        self._resize_start_widths = self._chip_widths(keys)
        QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.CursorShape.SizeHorCursor)

    def _update_resize(self, global_x: int) -> None:
        key = self._resize_key
        if key is None or not self._resize_start_widths:
            return
        keys = self._visible_keys()
        if key not in keys:
            return
        idx = keys.index(key)
        delta = int(global_x - self._resize_start_x)
        widths = list(self._resize_start_widths)
        widths[idx] = max(COMPACT_CHIP_WIDTH, widths[idx] + delta)
        if idx + 1 < len(widths):
            widths[idx + 1] = max(COMPACT_CHIP_WIDTH, widths[idx + 1] - delta)
        elif idx > 0:
            widths[idx - 1] = max(COMPACT_CHIP_WIDTH, widths[idx - 1] - delta)
        spacing = self._track_lay.spacing() * max(0, len(keys) - 1)
        inner = max(self._track_inner_width() - spacing, len(keys) * COMPACT_CHIP_WIDTH)
        total = sum(widths)
        if total > 0:
            scale = inner / total
            widths = [max(int(w * scale), COMPACT_CHIP_WIDTH) for w in widths]
        drift = inner - sum(widths)
        if widths and drift:
            widths[-1] = max(COMPACT_CHIP_WIDTH, widths[-1] + drift)
        for k, w in zip(keys, widths):
            self._chip_weights[k] = float(w)
            chip = self._chips[k]
            compact = not chip.full_label_fits(w)
            if chip._compact != compact:
                chip.set_compact(compact)
            chip.set_spring_width(w)

    def _end_resize(self) -> None:
        if self._resize_key is not None:
            self._emit_persist()
        self._resize_key = None
        self._resize_start_widths = []
        while QtGui.QGuiApplication.overrideCursor() is not None:
            QtGui.QGuiApplication.restoreOverrideCursor()

    def _show_drop_at(self, insert_index: int) -> None:
        rects = self._visible_chip_rects(exclude_key=self._drag_key)
        if not rects:
            self._drop_line.hide()
            return
        if insert_index <= 0:
            x = rects[0][1].left() - 3
        elif insert_index >= len(rects):
            x = rects[-1][1].right() + 1
        else:
            x = (rects[insert_index - 1][1].right() + rects[insert_index][1].left()) // 2
        self._drop_line.setGeometry(x, 4, 2, max(self._track.height() - 8, 16))
        self._drop_line.show()
        self._drop_line.raise_()

    def _move_key_to_index(self, key: str, insert_index: int) -> None:
        visible = self._visible_keys()
        if key not in visible:
            return
        visible.remove(key)
        insert_index = max(0, min(insert_index, len(visible)))
        visible.insert(insert_index, key)
        hidden = [k for k in self._order if k in self._hidden]
        new_order = visible + [k for k in hidden if k not in visible]
        for k in self._chips:
            if k not in new_order:
                new_order.append(k)
        self._order = new_order
        self.rebuild()
        self._emit_persist()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if not isinstance(event, QtGui.QMouseEvent):
            return super().eventFilter(obj, event)
        chip_key: Optional[str] = None
        resize_mode = False
        for key, chip in self._chips.items():
            if obj is chip.resize_edge():
                chip_key = key
                resize_mode = True
                break
            if obj is chip.grip():
                chip_key = key
                break
        if chip_key is None:
            return super().eventFilter(obj, event)

        et = event.type()
        if resize_mode:
            gx = int(event.globalPosition().x())
            if et == QtCore.QEvent.Type.MouseButtonPress and event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._begin_resize(chip_key, gx)
                return True
            if et == QtCore.QEvent.Type.MouseMove and self._resize_key == chip_key:
                self._update_resize(gx)
                return True
            if et == QtCore.QEvent.Type.MouseButtonRelease and self._resize_key == chip_key:
                self._end_resize()
                return True
            return super().eventFilter(obj, event)

        if et == QtCore.QEvent.Type.MouseButtonPress and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._begin_drag(chip_key, event.globalPosition().toPoint())
            return True
        if et == QtCore.QEvent.Type.MouseMove and self._drag_key == chip_key:
            rects = self._visible_chip_rects(exclude_key=chip_key)
            grects = []
            for k, r in rects:
                top_left = self._chips[k].mapToGlobal(QtCore.QPoint(0, 0))
                grects.append((k, QtCore.QRect(top_left, r.size())))
            idx = snap_insert_index(event.globalPosition().toPoint().x(), grects)
            self._show_drop_at(idx)
            return True
        if et == QtCore.QEvent.Type.MouseButtonRelease and self._drag_key == chip_key:
            rects = self._visible_chip_rects(exclude_key=chip_key)
            grects = []
            for k, r in rects:
                top_left = self._chips[k].mapToGlobal(QtCore.QPoint(0, 0))
                grects.append((k, QtCore.QRect(top_left, r.size())))
            idx = snap_insert_index(event.globalPosition().toPoint().x(), grects)
            self._end_drag()
            self._move_key_to_index(chip_key, idx)
            return True
        return super().eventFilter(obj, event)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        child = self.childAt(event.pos())
        key: Optional[str] = None
        w: Optional[QtWidgets.QWidget] = child
        while w is not None and w is not self:
            if isinstance(w, TopBarChip):
                key = w.key()
                break
            w = w.parentWidget()
        if key is None:
            return
        menu = QtWidgets.QMenu(self)
        if key != "view":
            act_hide = menu.addAction(f"Hide “{self._labels.get(key, key)}”")
            act_hide.triggered.connect(lambda _=False, k=key: self.hide_chip(k))
        if self._hidden:
            sub = menu.addMenu("Show hidden")
            for hk in self._order:
                if hk in self._hidden:
                    act = sub.addAction(self._labels.get(hk, hk))
                    act.triggered.connect(lambda _=False, k=hk: self._show_chip(k))
        menu.exec(event.globalPos())

    def _show_chip(self, key: str) -> None:
        self._hidden.discard(key)
        chip = self._chips.get(key)
        if chip is not None:
            chip.show()
        self.rebuild()
        self._emit_persist()


class _LayoutToggleButton(QtWidgets.QToolButton):
    """Always shows «Layout»; double-click switches Standard ↔ Field."""

    def __init__(self, on_toggle: Callable[[], None], parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_toggle = on_toggle
        self.setObjectName("surveyQuickBtn")
        configure_topbar_button(
            self,
            "Layout",
            tooltip=(
                "Double-click to switch layout (Standard ↔ Field). "
                "Stop the bridge first."
            ),
        )

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._on_toggle()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


def build_ui_switch_inner(
    parent: QtWidgets.QWidget,
    *,
    on_toggle: Callable[[], None],
) -> QtWidgets.QToolButton:
    """Single Layout control — double-click toggles the other workspace."""
    btn = _LayoutToggleButton(on_toggle, parent)
    parent.btn_ui_layout = btn  # type: ignore[attr-defined]
    return btn

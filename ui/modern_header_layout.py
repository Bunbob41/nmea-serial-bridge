"""Multi-pass fluid layout for the Modern global header splitter."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6 import QtCore, QtGui, QtWidgets

from ui.modern_header_split import header_split_mins


@dataclass(frozen=True)
class HeaderLayoutPlan:
    """Computed header splitter sizes and chrome flags."""

    sizes: tuple[int, int, int, int]
    start_compact: bool
    header_tight: bool
    force_chips_icon_only: bool | None


def compact_status_display(state: str, title: str) -> str:
    """Short lowercase capsule label for top-chips header (dot is separate)."""
    key = str(state or "").strip().lower()
    mapping = {
        "stopped": "stopped",
        "running": "running",
        "starting": "starting…",
        "failed": "failed",
    }
    if key in mapping:
        return mapping[key]
    raw = str(title or "").strip()
    return raw.lower() if raw else "stopped"


def measure_run_cluster_width(
    cluster: QtWidgets.QWidget,
    *,
    compact: bool,
) -> int:
    """Pass 1: minimum width for Start/Stop cluster."""
    if cluster is None:
        from ui.modern_header_split import session_run_cluster_min_width

        base = session_run_cluster_min_width()
        return max(58, base - 24) if compact else base

    lay = cluster.layout()
    spacing = lay.spacing() if lay is not None else 6
    margin = 0
    if lay is not None:
        m = lay.contentsMargins()
        margin = m.left() + m.right()

    visible = [
        child
        for child in cluster.findChildren(
            QtWidgets.QWidget, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly
        )
        if child.isVisible()
    ]

    if not visible:
        from ui.modern_header_split import session_run_cluster_min_width

        base = session_run_cluster_min_width()
        return max(58, base - 24) if compact else base

    pad_slack = -16 if compact else 0
    total = margin
    for index, child in enumerate(visible):
        if index:
            total += spacing
        hint = max(child.minimumWidth(), child.sizeHint().width(), child.minimumSizeHint().width())
        if compact and isinstance(child, QtWidgets.QAbstractButton):
            hint = max(52, hint - 18)
        total += hint
    from ui.modern_header_split import session_run_cluster_min_width

    floor = session_run_cluster_min_width()
    if compact:
        return max(58, total + pad_slack, floor - 24)
    return max(floor, total)


def measure_status_capsule_width(
    label: QtWidgets.QWidget,
    display_text: str,
    *,
    include_dot: bool = True,
) -> int:
    """Pass 1: width for compact status capsule — never below readable text."""
    text = str(display_text or "stopped").strip() or "stopped"
    fm = label.fontMetrics() if label is not None else QtGui.QFontMetrics(QtGui.QFont())
    text_w = fm.horizontalAdvance(text)
    dot_slack = 10 if include_dot else 0  # 6px dot + spacing
    pad = 28  # banner padding + capsule margins + layout slack
    mins = header_split_mins()
    return max(mins[1], text_w + dot_slack + pad)


def plan_header_layout(
    total_width: int,
    *,
    run_cluster: QtWidgets.QWidget,
    status_display: str,
    status_label: QtWidgets.QWidget,
    chips_labeled_w: int,
    chips_icon_w: int,
    trail_w: int,
    handle_width: int,
    chips_icon_only: bool,
    chips_mode: str,
) -> HeaderLayoutPlan:
    """Three-pass planner: analyze → prioritize compression → allocate without clipping."""
    mins = header_split_mins()
    handles = 3 * max(1, int(handle_width))
    slack = handles + 8
    avail = max(0, int(total_width) - slack)

    # Pass 1 — measure natural minimums
    run_full = measure_run_cluster_width(run_cluster, compact=False)
    run_compact = measure_run_cluster_width(run_cluster, compact=True)
    status_w = measure_status_capsule_width(status_label, status_display)
    trail_w = max(mins[3], int(trail_w))
    chips_labeled = max(mins[2], int(chips_labeled_w))
    chips_icon = max(mins[2], int(chips_icon_w))

    # Pass 2 — prioritize: compress run padding, then chip labels → icons (auto only)
    start_compact = False
    icon_only = bool(chips_icon_only)
    force_icon: bool | None = None
    run_w = run_full
    mode = str(chips_mode or "auto").strip().lower()

    def _total(run: int, chips: int) -> int:
        return run + status_w + trail_w + chips

    chips_pick = chips_icon if icon_only else chips_labeled
    if _total(run_w, chips_pick) > avail:
        start_compact = True
        run_w = run_compact
        chips_pick = chips_icon if icon_only else chips_labeled
        if _total(run_w, chips_pick) > avail and mode == "auto" and not icon_only:
            icon_only = True
            force_icon = True
            chips_pick = chips_icon

    remaining = avail - run_w - status_w - trail_w
    chips_w = max(mins[2], min(chips_pick, remaining if remaining > 0 else mins[2]))

    header_tight = start_compact or _total(run_w, chips_w) > avail - 4

    sizes = (run_w, status_w, chips_w, trail_w)
    return HeaderLayoutPlan(
        sizes=sizes,
        start_compact=start_compact,
        header_tight=header_tight,
        force_chips_icon_only=force_icon,
    )


def apply_plan_sizes(splitter: QtWidgets.QSplitter, plan: HeaderLayoutPlan) -> None:
    """Apply planned sizes; shrink only the chip rail — status and trail stay readable."""
    if splitter is None:
        return
    clamped = list(plan.sizes)
    mins = header_split_mins()
    width = max(splitter.width(), 1)
    status_floor = max(mins[1], int(plan.sizes[1]))
    trail_floor = max(mins[3], int(plan.sizes[3]))
    for i in range(len(clamped)):
        clamped[i] = max(mins[i], int(clamped[i]))
    clamped[1] = max(clamped[1], status_floor)
    clamped[3] = max(clamped[3], trail_floor)

    total = sum(clamped)
    if total < width:
        clamped[2] += width - total
    elif total > width:
        over = total - width
        room = max(0, clamped[2] - mins[2])
        take = min(over, room)
        clamped[2] -= take
        over -= take
        if over > 0:
            run_room = max(0, clamped[0] - mins[0])
            take = min(over, run_room)
            clamped[0] -= take
            over -= take
        if over > 0 and clamped[2] > mins[2]:
            clamped[2] = max(mins[2], clamped[2] - over)
        clamped[1] = max(clamped[1], status_floor)
        clamped[3] = max(clamped[3], trail_floor)

    if len(clamped) >= 3:
        drift = width - sum(clamped)
        if drift > 0:
            clamped[2] += drift
        elif drift < 0:
            clamped[2] = max(mins[2], clamped[2] + drift)
            if sum(clamped) < width:
                clamped[2] += width - sum(clamped)

    splitter.setSizes(clamped)

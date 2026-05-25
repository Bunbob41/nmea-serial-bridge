"""Collapsible disclosure rows with clean parent-window reflow (dialogs, panels)."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtCore, QtWidgets

_WIDGET_SIZE_MAX = 16777215


def reflow_window(window: QtWidgets.QWidget) -> None:
    """Resize a window to match the current layout (after show/hide children)."""
    window.updateGeometry()
    lay = window.layout()
    if lay is not None:
        lay.activate()
    window.adjustSize()
    if isinstance(window, QtWidgets.QDialog):
        hint = window.sizeHint()
        window.resize(max(window.minimumWidth(), hint.width()), hint.height())


def enable_dialog_content_fit(
    dialog: QtWidgets.QDialog,
    *,
    min_width: int = 0,
    min_height: int = 0,
    fixed: bool = True,
) -> None:
    """Size dialog to content (fixed) or set minimum size only (resizable)."""
    lay = dialog.layout()
    if lay is None:
        return
    if fixed:
        lay.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
    elif min_width > 0 or min_height > 0:
        lay.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinAndMaxSize)
    if min_width > 0:
        dialog.setMinimumWidth(min_width)
    if min_height > 0:
        dialog.setMinimumHeight(min_height)


class DisclosureRow(QtWidgets.QWidget):
    """Checkable disclosure: toggle label + body that frees layout space when closed."""

    def __init__(
        self,
        title: str,
        body: QtWidgets.QWidget,
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        start_open: bool = False,
        indent_px: int = 20,
        button_object_name: str = "pickerDisclosure",
        fill_vertical: bool = False,
        on_layout_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._body = body
        self._indent = indent_px
        self._open_bottom = 4
        self._fill_vertical = fill_vertical
        self._on_layout_changed = on_layout_changed

        v_pol = (
            QtWidgets.QSizePolicy.Policy.Expanding
            if fill_vertical
            else QtWidgets.QSizePolicy.Policy.Maximum
        )
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, v_pol)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._btn = QtWidgets.QToolButton(self)
        self._btn.setObjectName(button_object_name)
        self._btn.setText(title)
        self._btn.setCheckable(True)
        self._btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._btn.setAutoRaise(True)
        # Expand to fill the full row width so the entire header strip is clickable.
        self._btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        outer.addWidget(self._btn)
        outer.addWidget(body)

        body.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding
            if fill_vertical
            else QtWidgets.QSizePolicy.Policy.Maximum,
        )
        self._btn.toggled.connect(self._set_expanded)
        self._btn.setChecked(start_open)
        self._set_expanded(start_open)

    def _set_body_margins(self, expanded: bool) -> None:
        lay = self._body.layout()
        if lay is None:
            return
        bottom = self._open_bottom if expanded else 0
        lay.setContentsMargins(self._indent, 0, 0, bottom)

    def _set_expanded(self, expanded: bool) -> None:
        self._btn.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow
        )
        if expanded:
            # Release the row's own height cap BEFORE making the body visible.
            # Without this the row stays clamped at _COLLAPSED_STRIP_HEIGHT while
            # the body tries to render, causing content to clip under the splitter
            # handle until the deferred _apply_connect_splitter_sizes timer fires.
            self.setMaximumHeight(_WIDGET_SIZE_MAX)
            self._body.setMaximumHeight(_WIDGET_SIZE_MAX)
            self._body.setVisible(True)
        else:
            self._body.setMaximumHeight(0)
            self._body.setVisible(False)
        self._set_body_margins(expanded)
        if self._fill_vertical:
            self.updateGeometry()
            if self._on_layout_changed is not None:
                QtCore.QTimer.singleShot(0, self._on_layout_changed)
            return
        host = self.window()
        if host is not None and isinstance(host, QtWidgets.QDialog):
            QtCore.QTimer.singleShot(0, lambda w=host: reflow_window(w))

    def set_expanded(self, expanded: bool) -> None:
        """Set open/closed state and sync body visibility (use when signals are blocked)."""
        if self._btn.isChecked() != expanded:
            self._btn.blockSignals(True)
            self._btn.setChecked(expanded)
            self._btn.blockSignals(False)
        self._set_expanded(expanded)

    def tool_button(self) -> QtWidgets.QToolButton:
        return self._btn

    def body_widget(self) -> QtWidgets.QWidget:
        return self._body

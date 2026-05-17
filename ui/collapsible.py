"""Collapsible disclosure rows with clean parent-window reflow (dialogs, panels)."""
from __future__ import annotations

from typing import Optional

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


def enable_dialog_content_fit(dialog: QtWidgets.QDialog, *, min_width: int = 0) -> None:
    """Keep dialog height/width tied to visible content (no empty area after collapse)."""
    lay = dialog.layout()
    if lay is None:
        return
    lay.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
    if min_width > 0:
        dialog.setMinimumWidth(min_width)


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
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._body = body
        self._indent = indent_px
        self._open_bottom = 4
        self._fill_vertical = fill_vertical

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
            self._body.setMaximumHeight(_WIDGET_SIZE_MAX)
            self._body.setVisible(True)
        else:
            self._body.setMaximumHeight(0)
            self._body.setVisible(False)
        self._set_body_margins(expanded)
        if self._fill_vertical:
            return
        host = self.window()
        if host is not None and isinstance(host, QtWidgets.QDialog):
            QtCore.QTimer.singleShot(0, lambda w=host: reflow_window(w))

    def tool_button(self) -> QtWidgets.QToolButton:
        return self._btn

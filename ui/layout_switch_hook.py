"""Optional hook: three-way Layout chip without editing ui/mixin.py."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.mixin import BridgeLogicMixin


def install_three_way_layout_cycle() -> None:
    """Patch BridgeLogicMixin so the Layout chip cycles Standard → Field → Modern."""
    from PySide6 import QtWidgets

    import ui.mixin as mixin_mod
    from ui.layout_cycle import layout_display_name, next_layout_id
    from ui.registry import normalize_ui_id

    def _toggle_ui_layout(self: "BridgeLogicMixin") -> bool:
        cur = normalize_ui_id(getattr(self, "_ui_mode", "standard"))
        nxt = next_layout_id(cur)
        return self._switch_ui_layout(nxt)

    def _refresh_switch_layout_menu(self: "BridgeLogicMixin") -> None:
        act = getattr(self, "_act_switch_layout", None)
        if act is None:
            return
        cur = normalize_ui_id(getattr(self, "_ui_mode", "standard"))
        nxt = next_layout_id(cur)
        act.setText(f"Switch to {layout_display_name(nxt)} layout")
        self._switch_layout_target = nxt
        running = self.bridge is not None or (
            self._worker is not None and self._worker.isRunning()
        )
        act.setEnabled(not running)
        if running:
            act.setStatusTip("Stop the bridge before switching layout.")
        else:
            act.setStatusTip(f"Reload the window in the {layout_display_name(nxt)} layout.")

    mixin_mod.BridgeLogicMixin._toggle_ui_layout = _toggle_ui_layout  # type: ignore[method-assign]
    mixin_mod.BridgeLogicMixin._refresh_switch_layout_menu = _refresh_switch_layout_menu  # type: ignore[method-assign]

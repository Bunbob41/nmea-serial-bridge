"""Optional hook: three-way Layout chip without editing ui/mixin.py."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.mixin import BridgeLogicMixin


def install_three_way_layout_cycle() -> None:
    """Patch BridgeLogicMixin so the Layout chip cycles Field → Modern."""
    import ui.mixin as mixin_mod
    from ui.layout_cycle import next_layout_id
    from ui.registry import normalize_ui_id

    def _toggle_ui_layout(self: "BridgeLogicMixin") -> bool:
        cur = normalize_ui_id(getattr(self, "_ui_mode", "field"))
        nxt = next_layout_id(cur)
        return self._switch_ui_layout(nxt)

    mixin_mod.BridgeLogicMixin._toggle_ui_layout = _toggle_ui_layout  # type: ignore[method-assign]

"""Navigate Standard Tools nav or Field/Minimal Tools drawer by tab label alias."""
from __future__ import annotations

from PySide6 import QtWidgets

_TAB_ALIASES: dict[str, tuple[str, ...]] = {
    "preset": ("preset", "presets"),
    "phone": ("phone",),
    "nmea": ("nmea",),
    "terminal": ("terminal", "shell"),
    "diag": ("diag", "diagnostic"),
    "send": ("inject", "send"),
    "theme": ("theme",),
    "guide": ("guide",),
}


def open_tools_tab(win: QtWidgets.QWidget, *aliases: str) -> None:
    """Open Tools and select the first nav/drawer tab matching any alias (case-insensitive)."""
    keys: list[str] = []
    for a in aliases:
        low = a.lower()
        keys.extend(_TAB_ALIASES.get(low, (low,)))
    keys = list(dict.fromkeys(keys))
    tools_nav = getattr(win, "_tools_nav", None)
    if tools_nav is not None:
        drawer_btn = getattr(win, "_drawer_btn", None)
        if drawer_btn is not None and not drawer_btn.isChecked():
            drawer_btn.setChecked(True)
        main_tabs = getattr(win, "_main_tabs", None)
        if main_tabs is not None:
            for i in range(main_tabs.count()):
                if main_tabs.tabText(i).lower() == "tools":
                    main_tabs.setCurrentIndex(i)
                    break
        for row in range(tools_nav.count()):
            item = tools_nav.item(row)
            if item is None:
                continue
            label = item.text().lower()
            if any(label.startswith(key) or key in label for key in keys):
                tools_nav.setCurrentRow(row)
                return
        return

    tabs = getattr(win, "_drawer_tabs", None) or getattr(win, "_main_tabs", None)
    if tabs is None:
        return
    drawer_btn = getattr(win, "_drawer_btn", None)
    if drawer_btn is not None and not drawer_btn.isChecked():
        drawer_btn.setChecked(True)
    for i in range(tabs.count()):
        label = tabs.tabText(i).lower()
        if any(label.startswith(key) or key in label for key in keys):
            tabs.setCurrentIndex(i)
            return

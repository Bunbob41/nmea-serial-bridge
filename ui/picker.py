"""Qt UI picker (used by frozen .exe and optional dev launch)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.registry import UI_DEFAULT, UI_LABELS, UI_ORDER

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_choice.json"


def load_saved_ui() -> Optional[str]:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        ui = data.get("ui")
        if ui in UI_ORDER:
            return ui
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return None


def save_ui_choice(ui: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"ui": ui}, indent=2), encoding="utf-8")


def pick_ui_dialog(parent: Optional[QtWidgets.QWidget] = None) -> Optional[str]:
    """Show modal dialog; return UI id or None if cancelled."""
    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle("NMEA Serial Bridge — choose layout")
    dlg.setMinimumWidth(420)
    lay = QtWidgets.QVBoxLayout(dlg)
    lay.addWidget(QtWidgets.QLabel("Pick a window layout (you can change this later by deleting\n"
        f"{CONFIG_PATH} and restarting):"))

    group = QtWidgets.QButtonGroup(dlg)
    radios: list[tuple[QtWidgets.QRadioButton, str]] = []
    saved = load_saved_ui() or UI_DEFAULT
    for uid in UI_ORDER:
        rb = QtWidgets.QRadioButton(UI_LABELS[uid])
        rb.setProperty("ui_id", uid)
        if uid == saved:
            rb.setChecked(True)
        group.addButton(rb)
        lay.addWidget(rb)
        radios.append((rb, uid))

    remember = QtWidgets.QCheckBox("Remember this choice")
    remember.setChecked(True)
    lay.addWidget(remember)

    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
        | QtWidgets.QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    ui_id = UI_DEFAULT
    for rb, uid in radios:
        if rb.isChecked():
            ui_id = uid
            break
    if remember.isChecked():
        save_ui_choice(ui_id)
    return ui_id


def resolve_ui_id(cli_ui: Optional[str], *, show_picker: bool) -> str:
    """CLI --ui > saved config > picker (if show_picker) > default."""
    if cli_ui and cli_ui in UI_ORDER:
        return cli_ui
    saved = load_saved_ui()
    if saved:
        return saved
    if show_picker:
        # Need QApplication; caller must create before calling this
        picked = pick_ui_dialog()
        if picked:
            return picked
    return UI_DEFAULT

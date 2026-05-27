"""Qt UI picker (used by frozen .exe and optional dev launch)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.app_icon import apply_app_icon
from ui.collapsible import DisclosureRow, enable_dialog_content_fit, reflow_window
from ui.registry import (
    UI_ALL_IDS,
    UI_DEFAULT,
    UI_DESCRIPTIONS,
    UI_FIELD,
    UI_LABELS,
    UI_ORDER,
    normalize_ui_id,
)
from ui.styles import UI_PICKER_STYLESHEET
from version import __version__

CONFIG_PATH = Path.home() / ".cursor-udp-com-bridge" / "ui_choice.json"


def load_saved_ui() -> Optional[str]:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        ui = normalize_ui_id(str(data.get("ui") or ""))
        if ui in UI_ORDER:
            return ui
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return None


def save_ui_choice(ui: str) -> None:
    ui = normalize_ui_id(ui)
    if ui not in UI_ORDER:
        ui = UI_DEFAULT
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"ui": ui}, indent=2), encoding="utf-8")


def clear_saved_ui_choice() -> None:
    try:
        CONFIG_PATH.unlink()
    except OSError:
        pass


def _hint_label(text: str, parent: QtWidgets.QWidget) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text, parent)
    lbl.setObjectName("pickerLayoutHint")
    lbl.setWordWrap(True)
    lbl.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Maximum,
    )
    return lbl


def _hint_body(text: str, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
    wrap = QtWidgets.QWidget(parent)
    lay = QtWidgets.QVBoxLayout(wrap)
    lay.setContentsMargins(20, 0, 0, 0)
    lay.setSpacing(0)
    lay.addWidget(_hint_label(text, wrap))
    return wrap


def pick_ui_dialog(parent: Optional[QtWidgets.QWidget] = None) -> Optional[str]:
    """Show modal dialog; return UI id or None if cancelled."""
    dlg = QtWidgets.QDialog(parent)
    dlg.setObjectName("UiPickerDialog")
    dlg.setStyleSheet(UI_PICKER_STYLESHEET)
    apply_app_icon(dlg)
    dlg.setWindowTitle(f"Serial Link v{__version__} — Ethernet ↔ serial")
    dlg.setMinimumWidth(440)

    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setSpacing(6)
    lay.setContentsMargins(14, 14, 14, 12)

    title = QtWidgets.QLabel("Choose a window layout:")
    title.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    lay.addWidget(title)

    about_text = (
        "If you tick “Remember this layout”, the app opens the same way next time "
        f"(saved to {CONFIG_PATH}).\n\n"
        "Leave it unchecked to see this dialog every launch.\n\n"
        "To reset a remembered layout, delete that file or uncheck Remember and press OK."
    )
    lay.addWidget(
        DisclosureRow(
            "About saved layout",
            _hint_body(about_text, dlg),
            dlg,
            start_open=False,
        )
    )

    group = QtWidgets.QButtonGroup(dlg)
    radios: list[tuple[QtWidgets.QRadioButton, str]] = []
    saved = load_saved_ui()
    default_uid = saved if saved else UI_FIELD
    for uid in UI_ORDER:
        block = QtWidgets.QWidget(dlg)
        block.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        block_lay = QtWidgets.QVBoxLayout(block)
        block_lay.setContentsMargins(0, 4, 0, 2)
        block_lay.setSpacing(2)

        rb = QtWidgets.QRadioButton(UI_LABELS[uid], block)
        rb.setProperty("ui_id", uid)
        rb.setToolTip(UI_DESCRIPTIONS[uid])
        if uid == default_uid:
            rb.setChecked(True)
        group.addButton(rb)
        block_lay.addWidget(rb)

        block_lay.addWidget(
            DisclosureRow(
                "Details",
                _hint_body(UI_DESCRIPTIONS[uid], block),
                block,
                start_open=False,
            )
        )
        lay.addWidget(block)
        radios.append((rb, uid))

    remember = QtWidgets.QCheckBox("Remember this layout for next launch", dlg)
    remember.setChecked(False)
    remember.setToolTip(
        f"When checked, writes your choice to:\n{CONFIG_PATH}\n\n"
        "When unchecked, this dialog appears again next time."
    )
    remember.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    lay.addWidget(remember)

    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
        | QtWidgets.QDialogButtonBox.StandardButton.Cancel
    )
    ok_btn = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
    cancel_btn = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
    if ok_btn is not None:
        ok_btn.setObjectName("pickerBtnOk")
    if cancel_btn is not None:
        cancel_btn.setObjectName("pickerBtnCancel")
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    enable_dialog_content_fit(dlg, min_width=440)
    reflow_window(dlg)

    if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    ui_id = UI_DEFAULT
    for rb, uid in radios:
        if rb.isChecked():
            ui_id = uid
            break
    if remember.isChecked():
        save_ui_choice(ui_id)
    else:
        clear_saved_ui_choice()
    return ui_id


def resolve_ui_id(cli_ui: Optional[str], *, show_picker: bool) -> str:
    """CLI --ui > saved config > picker (if show_picker) > default."""
    if cli_ui:
        ui = normalize_ui_id(cli_ui)
        if ui in UI_ORDER:
            return ui
        if ui in UI_ALL_IDS:
            return normalize_ui_id(ui)
    saved = load_saved_ui()
    if saved:
        return saved
    if show_picker:
        picked = pick_ui_dialog()
        if picked:
            return picked
    return UI_DEFAULT

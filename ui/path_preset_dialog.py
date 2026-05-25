"""Dialogs for naming presets and editing survey network fields."""
from __future__ import annotations

from typing import Any, Optional

from PySide6 import QtCore, QtWidgets

from bench_config import validate_preset_name


def ask_preset_name(
    parent: QtWidgets.QWidget,
    title: str,
    *,
    initial: str = "",
) -> Optional[str]:
    host = parent.window() if parent is not None else parent
    dialog = QtWidgets.QInputDialog(host)
    dialog.setWindowTitle(title)
    dialog.setLabelText("Preset name:")
    dialog.setTextValue(initial or "")
    dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
    if host is not None:
        host.raise_()
        host.activateWindow()
    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    text = dialog.textValue()
    name = text.strip()
    err = validate_preset_name(name)
    if err:
        QtWidgets.QMessageBox.warning(parent, title, err)
        return None
    return name


def edit_survey_network_dialog(
    parent: QtWidgets.QWidget,
    initial: dict[str, Any],
) -> Optional[dict[str, Any]]:
    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle("Survey network")
    lay = QtWidgets.QVBoxLayout(dlg)
    hint = QtWidgets.QLabel(
        "Optional — for boat / LAN workflows. COM and UDP listen come from the main connection fields."
    )
    hint.setWordWrap(True)
    lay.addWidget(hint)

    form = QtWidgets.QFormLayout()
    pc_ip = QtWidgets.QLineEdit(str(initial.get("pc_ip", "192.168.1.10")))
    subnet = QtWidgets.QLineEdit(str(initial.get("subnet_mask", "255.255.255.0")))
    ins_ip = QtWidgets.QLineEdit(str(initial.get("ins_ip", "192.168.1.20")))
    notes = QtWidgets.QPlainTextEdit(str(initial.get("notes", "")))
    notes.setMaximumHeight(72)
    form.addRow("Survey PC IP:", pc_ip)
    form.addRow("Subnet mask:", subnet)
    form.addRow("INS IP (reference):", ins_ip)
    form.addRow("Notes:", notes)
    lay.addLayout(form)

    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
        | QtWidgets.QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    return {
        "pc_ip": pc_ip.text().strip(),
        "subnet_mask": subnet.text().strip(),
        "ins_ip": ins_ip.text().strip(),
        "notes": notes.toPlainText().strip(),
    }


def edit_boat_preset_dialog(
    parent: QtWidgets.QWidget,
    initial: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Backward-compatible alias used by older save paths."""
    return edit_survey_network_dialog(parent, initial)

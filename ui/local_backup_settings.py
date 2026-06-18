"""Shared backup folder controls (Mission Review + Tools black-box card)."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from core.local_logger import allocate_session_folder, format_session_folder_name
from ui.ui_prefs import (
    effective_local_backup_base_dir,
    load_local_backup_prefs,
    save_local_backup_prefs,
)

if TYPE_CHECKING:
    from ui.mixin import BridgeLogicMixin


def mount_local_backup_location_row(
    win: BridgeLogicMixin,
    lay: QtWidgets.QVBoxLayout,
    *,
    show_session_file: bool = False,
) -> None:
    """Backup root path, dated-folder toggle, and optional current-session path."""
    hint = QtWidgets.QLabel(
        "Backup saves raw COM reads to a .raw file. Choose where future sessions write."
    )
    hint.setObjectName("modernIntentHint")
    hint.setWordWrap(True)
    lay.addWidget(hint)

    path_row = QtWidgets.QHBoxLayout()
    win.local_backup_path = QtWidgets.QLineEdit()
    win.local_backup_path.setObjectName("modernPathField")
    win.local_backup_path.setPlaceholderText("Default: logs/ beside the app")
    win.local_backup_path.setToolTip(
        "Root folder for black-box backups. Leave blank for the default logs/ folder."
    )
    win.local_backup_path.editingFinished.connect(win._save_local_backup_path_from_ui)
    btn_browse = QtWidgets.QPushButton("Browse…")
    btn_browse.setToolTip("Pick the backup root folder.")
    btn_browse.clicked.connect(win._browse_local_backup_dir)
    path_row.addWidget(win.local_backup_path, 1)
    path_row.addWidget(btn_browse)
    lay.addLayout(path_row)

    win.chk_local_backup_session_folders = QtWidgets.QCheckBox(
        "Create dated folder each Start (YYYY-MM-DD_HH-MM)"
    )
    win.chk_local_backup_session_folders.setToolTip(
        "Each bridge run writes into a new subfolder like 2026-06-16_19-58 under the path above."
    )
    win.chk_local_backup_session_folders.toggled.connect(win._save_local_backup_session_folders_pref)
    lay.addWidget(win.chk_local_backup_session_folders)

    folder_row = QtWidgets.QHBoxLayout()
    btn_new_folder = QtWidgets.QPushButton("New dated folder…")
    btn_new_folder.setToolTip(
        "Create a new timestamped folder under the backup root and select it for the next session."
    )
    btn_new_folder.clicked.connect(win._create_local_backup_dated_folder)
    folder_row.addWidget(btn_new_folder)
    folder_row.addStretch(1)
    lay.addLayout(folder_row)

    if show_session_file:
        win._mission_session_path_label = QtWidgets.QLabel()
        win._mission_session_path_label.setObjectName("modernIntentHint")
        win._mission_session_path_label.setWordWrap(True)
        lay.addWidget(win._mission_session_path_label)


def sync_local_backup_location_ui(win: BridgeLogicMixin) -> None:
    """Load persisted backup path prefs into shared controls."""
    path_edit = getattr(win, "local_backup_path", None)
    chk_folders = getattr(win, "chk_local_backup_session_folders", None)
    if path_edit is None and chk_folders is None:
        return
    prefs = load_local_backup_prefs()
    custom = str(prefs.get("base_dir") or "").strip()
    if path_edit is not None:
        path_edit.blockSignals(True)
        try:
            if custom:
                path_edit.setText(custom)
            else:
                path_edit.clear()
                path_edit.setPlaceholderText(str(effective_local_backup_base_dir()))
        finally:
            path_edit.blockSignals(False)
    if chk_folders is not None:
        chk_folders.blockSignals(True)
        try:
            chk_folders.setChecked(bool(prefs.get("session_folders", True)))
        finally:
            chk_folders.blockSignals(False)


def set_mission_session_path_label(win: BridgeLogicMixin, path: str) -> None:
    lbl = getattr(win, "_mission_session_path_label", None)
    if lbl is None:
        return
    path_s = str(path or "").strip()
    if path_s:
        lbl.setText(f"This session file: {path_s}")
    else:
        lbl.setText("This session file: (none recorded)")


def create_dated_backup_folder(*, parent: QtWidgets.QWidget) -> Path | None:
    """Create YYYY-MM-DD_HH-MM under the configured backup root."""
    root = effective_local_backup_base_dir()
    try:
        folder = allocate_session_folder(root)
    except OSError as exc:
        QtWidgets.QMessageBox.critical(
            parent,
            "Could not create folder",
            f"Failed to create a dated backup folder under:\n{root}\n\n{exc}",
        )
        return None
    save_local_backup_prefs(base_dir=str(folder), session_folders=False)
    return folder

"""Shared backup folder controls (Mission Review + Tools black-box card)."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets

from core.local_logger import allocate_session_folder, format_session_folder_name
from ui.ui_prefs import (
    effective_local_backup_base_dir,
    load_local_backup_prefs,
    save_local_backup_prefs,
)

if TYPE_CHECKING:
    from ui.mixin import BridgeLogicMixin


class ElidedPathLabel(QtWidgets.QLabel):
    """Single-line path display with middle-ellipsis on narrow panes."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("missionSessionPathValue")
        self._full_path = ""
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.setMinimumWidth(0)

    def set_full_path(self, path: str) -> None:
        self._full_path = str(path or "").strip()
        self.setToolTip(self._full_path if self._full_path else "")
        self._refresh_elide()

    def full_path(self) -> str:
        return self._full_path

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_elide()

    def _refresh_elide(self) -> None:
        if not self._full_path:
            self.setText("(none recorded)")
            return
        width = max(40, self.width())
        self.setText(self.fontMetrics().elidedText(
            self._full_path,
            QtCore.Qt.TextElideMode.ElideMiddle,
            width,
        ))


def _copy_session_path_to_clipboard(win: BridgeLogicMixin) -> None:
    lbl = getattr(win, "_mission_session_path_label", None)
    path = lbl.full_path() if isinstance(lbl, ElidedPathLabel) else ""
    if not path:
        return
    app = QtWidgets.QApplication.instance()
    if app is not None:
        app.clipboard().setText(path)
    log = getattr(win, "_log_ui", None)
    if callable(log):
        log("[Backup] Session file path copied to clipboard.")


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
        session_row = QtWidgets.QHBoxLayout()
        session_row.setSpacing(8)
        session_prefix = QtWidgets.QLabel("This session file:")
        session_prefix.setObjectName("modernToolsInlineSection")
        session_row.addWidget(session_prefix, 0)
        win._mission_session_path_label = ElidedPathLabel()
        session_row.addWidget(win._mission_session_path_label, 1)
        win._mission_session_path_copy = QtWidgets.QToolButton()
        win._mission_session_path_copy.setObjectName("missionSessionPathCopy")
        win._mission_session_path_copy.setText("📋")
        win._mission_session_path_copy.setToolTip("Copy session .raw path to clipboard")
        win._mission_session_path_copy.setFixedSize(28, 28)
        win._mission_session_path_copy.clicked.connect(
            lambda: _copy_session_path_to_clipboard(win)
        )
        session_row.addWidget(win._mission_session_path_copy, 0)
        lay.addLayout(session_row)


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
    if isinstance(lbl, ElidedPathLabel):
        lbl.set_full_path(str(path or "").strip())
        copy_btn = getattr(win, "_mission_session_path_copy", None)
        if copy_btn is not None:
            copy_btn.setEnabled(bool(lbl.full_path()))
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

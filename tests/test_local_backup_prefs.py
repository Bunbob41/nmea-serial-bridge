"""Backup folder preference helpers."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ui import ui_prefs


class TestLocalBackupDirPrefs(unittest.TestCase):
    def test_prepare_session_dir_uses_dated_subfolder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "survey"
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_local_backup_prefs(
                    enabled=True,
                    base_dir=str(root),
                    session_folders=True,
                )
                session_dir = ui_prefs.prepare_local_backup_dir_for_session()
            self.assertTrue(str(session_dir).startswith(str(root)))
            self.assertTrue(session_dir.is_dir())
            self.assertRegex(session_dir.name, r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}")

    def test_prepare_session_dir_uses_root_when_subfolders_off(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "flat"
            path = Path(tmp) / "ui_prefs.json"
            with patch.object(ui_prefs, "CONFIG_PATH", path):
                ui_prefs.save_local_backup_prefs(
                    enabled=True,
                    base_dir=str(root),
                    session_folders=False,
                )
                session_dir = ui_prefs.prepare_local_backup_dir_for_session()
            self.assertEqual(session_dir, root)
            self.assertTrue(root.is_dir())


if __name__ == "__main__":
    unittest.main()

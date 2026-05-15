# PyInstaller spec — NMEA serial bridge (Windows one-folder build)
# Build:  pyinstaller nmea_serial_bridge.spec --noconfirm
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
root = Path(SPECPATH)

pyside_datas, pyside_binaries, pyside_hidden = collect_all("PySide6")
qasync_datas, qasync_binaries, qasync_hidden = collect_all("qasync")

a = Analysis(
    ["bridge_gui.py"],
    pathex=[str(root)],
    binaries=pyside_binaries + qasync_binaries,
    datas=pyside_datas + qasync_datas,
    hiddenimports=[
        "serial_asyncio",
        "serial.tools.list_ports",
        "nmea_codec",
        "version",
        *pyside_hidden,
        *qasync_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="nmea-serial-bridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="version_info.txt" if (root / "version_info.txt").is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="nmea-serial-bridge",
)

# PyInstaller spec — NMEA serial bridge (Windows one-folder build)
# Build:  pyinstaller nmea_serial_bridge.spec --noconfirm
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
root = Path(SPECPATH)

pyside_datas, pyside_binaries, pyside_hidden = collect_all("PySide6")

HELPER_SCRIPTS = [
    "verify_all.py",
    "com_free.py",
    "check_setup.py",
    "nmea_static_sample.py",
    "bench_tcp_stress.py",
    "bench_capacity_probe.py",
    "bench_gui_smoke.py",
    "bridge_headless.py",
    "bench_stress.py",
]

# Python module files imported by the helper scripts when they run as subprocesses.
# QProcess spawns a fresh Python interpreter; it can only import from the working
# directory (sys._MEIPASS).  These files are bundled as raw .py so the subprocess
# can find them via the automatic sys.path[0] = working-directory rule.
HELPER_MODULES = [
    "bench_config.py",
    "bench_udp_test.py",
    "nmea_codec.py",
    "bridge_core.py",
    "py_interpreter.py",
]

helper_datas = [
    (str(root / name), ".")
    for name in HELPER_SCRIPTS + HELPER_MODULES
    if (root / name).is_file()
]

docs_datas = ([(str(root / "docs"), "docs")] if (root / "docs").is_dir() else [])

APP_HIDDEN = [
    "serial_asyncio",
    "serial.tools.list_ports",
    "nmea_codec",
    "version",
    "bridge_core",
    "bench_config",
    "nmea_static_sample",
    "bench_udp_test",
    "ui",
    "ui.registry",
    "ui.standard",
    "ui.field",
    "ui.minimal",
    "ui.logfirst",
    "ui.mixin",
    "ui.controls",
    "ui.tool_tabs",
    "ui.stats_line",
    "ui.stats_popout",
    "ui.styles",
    "ui.picker",
    "ui.app_icon",
    "ui.theme_choice",
    "ui.theme_palette",
]

a = Analysis(
    ["bridge_gui.py"],
    pathex=[str(root)],
    binaries=pyside_binaries,
    datas=pyside_datas
    + [(str(root / "bench_defaults.json"), ".")]
    + helper_datas
    + docs_datas
    + ([(str(root / "assets"), "assets")] if (root / "assets").is_dir() else []),
    hiddenimports=[*APP_HIDDEN, *pyside_hidden],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets", "qasync"],
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
    icon=str(root / "assets" / "app-icon.ico")
    if (root / "assets" / "app-icon.ico").is_file()
    else None,
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

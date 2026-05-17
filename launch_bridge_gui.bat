@echo off
REM Silent launch: pythonw + launcher.py v1.1+ (Standard or Field; saved UI or picker). Re-run create_desktop_shortcut after moving the repo.
cd /d "%~dp0"
where pythonw >nul 2>&1 && (
    start "" pythonw "%~dp0launcher.py"
    exit /b 0
)
if exist "C:\Program Files\Python314\pythonw.exe" (
    start "" "C:\Program Files\Python314\pythonw.exe" "%~dp0launcher.py"
    exit /b 0
)
echo [launch_bridge_gui] Could not find pythonw.exe. Install Python or add it to PATH.
echo Then run create_desktop_shortcut.bat again to refresh the desktop link.
pause
exit /b 1

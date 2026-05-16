@echo off
REM Creates Desktop shortcut -> launch_bridge_gui.bat (correct Start in folder)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"
pause

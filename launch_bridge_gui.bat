@echo off
REM Silent launch (no console menu): pythonw + launcher picks saved UI or Qt dialog.
cd /d "%~dp0"
setlocal
set "PYW=C:\Program Files\Python314\pythonw.exe"
if exist "%PYW%" (
    start "" "%PYW%" "%~dp0launcher.py"
) else (
    REM Fallback: python - launcher exits immediately after spawning GUI
    start "" pythonw "%~dp0launcher.py"
)
endlocal

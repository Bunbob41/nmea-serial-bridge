@echo off
REM Console layout menu: Standard or Field (v1.1+). Saves choice to %%USERPROFILE%%\.cursor-udp-com-bridge\ui_choice.json
cd /d "%~dp0"
where python >nul 2>&1 && (
    python "%~dp0launcher.py" --console-menu
    goto :end
)
if exist "C:\Program Files\Python314\python.exe" (
    "C:\Program Files\Python314\python.exe" "%~dp0launcher.py" --console-menu
    goto :end
)
echo [launch_bridge_gui_menu] Could not find python.exe on PATH.
pause
exit /b 1
:end
pause

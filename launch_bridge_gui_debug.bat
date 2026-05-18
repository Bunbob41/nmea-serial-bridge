@echo off
cd /d "%~dp0"
echo Starting bridge GUI with console (errors will print here)...
where python >nul 2>&1 && python "%~dp0bridge_gui.py" %* && goto :done
if exist "C:\Program Files\Python314\python.exe" (
    "C:\Program Files\Python314\python.exe" "%~dp0bridge_gui.py" %*
    goto :done
)
echo [launch_bridge_gui_debug] Could not find python.exe on PATH.
pause
exit /b 1
:done
echo.
echo Exit code: %ERRORLEVEL%
pause

@echo off
REM Wipe saved layout/UI prefs for first-launch testing. Close the GUI first.
cd /d "%~dp0"
where python >nul 2>&1 && (
    python "%~dp0reset_first_launch_prefs.py" %*
    goto :done
)
if exist "C:\Program Files\Python314\python.exe" (
    "C:\Program Files\Python314\python.exe" "%~dp0reset_first_launch_prefs.py" %*
    goto :done
)
echo Could not find python.exe on PATH.
pause
exit /b 1
:done
echo.
pause

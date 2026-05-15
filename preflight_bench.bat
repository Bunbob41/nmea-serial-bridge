@echo off
cd /d "%~dp0"
echo === Bench preflight (com0com / localhost) ===
python com_free.py
if errorlevel 1 goto fail
python check_setup.py --port 10110
if errorlevel 1 goto fail
echo.
echo OK — launch GUI: launch_bridge_gui.bat  then Bench preset - Start
goto end
:fail
echo.
echo Fix issues above, then retry.
:end
pause

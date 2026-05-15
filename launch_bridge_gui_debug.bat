@echo off
cd /d "%~dp0"
echo Starting bridge GUI with console (errors will print here)...
"C:\Program Files\Python314\python.exe" "%~dp0bridge_gui.py"
echo.
echo Exit code: %ERRORLEVEL%
pause

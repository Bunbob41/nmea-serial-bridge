@echo off
REM Launch Serial Link — same as: python bridge_gui.py
setlocal
cd /d "%~dp0"

for /f "tokens=2 delims==" %%I in ('wmic process where "name='python.exe' and CommandLine like '%%bridge_gui%%'" get ProcessId /value 2^>nul ^| find "="') do taskkill /PID %%I /F >nul 2>&1
for /f "tokens=2 delims==" %%I in ('wmic process where "name='pythonw.exe' and CommandLine like '%%bridge_gui%%'" get ProcessId /value 2^>nul ^| find "="') do taskkill /PID %%I /F >nul 2>&1
del "%TEMP%\nmea-serial-bridge.lock" >nul 2>&1

if exist "C:\Program Files\Python314\python.exe" (
  "C:\Program Files\Python314\python.exe" bridge_gui.py
) else (
  python bridge_gui.py
)

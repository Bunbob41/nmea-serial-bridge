@echo off
cd /d "%~dp0"
echo === Boat preflight (edit bench_defaults.json - production first) ===
python check_setup.py --production
python com_free.py
if errorlevel 1 goto fail
echo.
echo OK — GUI: Production preset - Start  (INS UDP -^> PC, bridge -^> Cube COM)
goto end
:fail
echo.
echo Fix COM / network, then retry.
:end
pause

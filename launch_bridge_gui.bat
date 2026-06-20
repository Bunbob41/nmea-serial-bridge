@echo off

REM Launch Serial Link (Field or Modern). Uses pythonw.exe — no console window.

cd /d "%~dp0"

where pythonw >nul 2>&1 && (

    start "" /D "%~dp0" pythonw "%~dp0bridge_gui.py"

    exit /b 0

)

where python >nul 2>&1 && (

    for /f "delims=" %%P in ('where python') do (

        if exist "%%~dpPpythonw.exe" (

            start "" /D "%~dp0" "%%~dpPpythonw.exe" "%~dp0bridge_gui.py"

            exit /b 0

        )

    )

)

if exist "C:\Program Files\Python314\pythonw.exe" (

    start "" /D "%~dp0" "C:\Program Files\Python314\pythonw.exe" "%~dp0bridge_gui.py"

    exit /b 0

)

echo [launch_bridge_gui] Could not find pythonw.exe on PATH.

pause

exit /b 1



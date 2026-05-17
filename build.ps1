# Build Windows one-folder distribution with PyInstaller
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python not found on PATH"
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller>=6.0

python tools\sync_version_info.py
python -m unittest discover -s . -p "test_*.py" -v
if (Test-Path "assets\app-icon.png") {
    python tools\make_app_icon.py
}
python -m PyInstaller nmea_serial_bridge.spec --noconfirm

Write-Host ""
Write-Host "Build output: dist\nmea-serial-bridge\nmea-serial-bridge.exe"
Write-Host "Copy that folder to a clean PC or create a shortcut to the .exe."

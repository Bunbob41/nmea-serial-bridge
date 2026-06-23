# Build Windows one-folder distribution with PyInstaller
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python not found on PATH"
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-web.txt
python -m pip install pyinstaller>=6.0

python tools\sync_version_info.py
python verify_all.py
if ($LASTEXITCODE -ne 0) {
    throw "verify_all failed"
}
python tools\run_unittests.py
if ($LASTEXITCODE -ne 0) { throw "unittest failed" }
if (Test-Path "assets\app-icon.png") {
    python tools\make_app_icon.py
}
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
python -m PyInstaller nmea_serial_bridge.spec --noconfirm 2>&1 | ForEach-Object { Write-Host $_ }
$pyiCode = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($pyiCode -ne 0) { throw "PyInstaller failed (exit $pyiCode)" }
python tools\check_frozen_bundle.py dist\serial-link
if ($LASTEXITCODE -ne 0) { throw "check_frozen_bundle failed" }

Write-Host ""
Write-Host "Build output: dist\serial-link\serial-link.exe"
Write-Host "Copy that folder to a clean PC or create a shortcut to the .exe."

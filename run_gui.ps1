# Launch Serial Link — same as: python bridge_gui.py
$ErrorActionPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match 'bridge_gui' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Remove-Item "$env:TEMP\nmea-serial-bridge.lock" -Force

$py = 'C:\Program Files\Python314\python.exe'
if (-not (Test-Path $py)) {
    $py = (Get-Command python.exe -All -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notmatch 'WindowsApps' } |
        Select-Object -First 1).Source
}
if (-not $py) {
    Write-Error 'python.exe not found. Install Python 3.10+ or run: python bridge_gui.py'
    exit 1
}

Write-Host "Starting Serial Link with $py"
& $py bridge_gui.py

$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $proj) { $proj = Get-Location }
$bat = Join-Path $proj "launch_bridge_gui.bat"
if (-not (Test-Path $bat)) {
    Write-Error "Not found: $bat"
    exit 1
}
$desk = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desk "NMEA Serial Bridge.lnk"
$w = New-Object -ComObject WScript.Shell
$s = $w.CreateShortcut($lnk)
$s.TargetPath = $bat
$s.WorkingDirectory = $proj
$s.Description = "NMEA UDP/TCP serial bridge (silent launcher)"
$s.Save()
Write-Host "Shortcut created: $lnk -> $bat"

$ErrorActionPreference = "Stop"
# Re-run this script after moving the repo or changing launch .bats — it overwrites the same .lnk files.
$proj = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $proj) { $proj = Get-Location }
$bat = Join-Path $proj "launch_bridge_gui.bat"
$batMenu = Join-Path $proj "launch_bridge_gui_menu.bat"
if (-not (Test-Path $bat)) {
    Write-Error "Not found: $bat"
    exit 1
}
$desk = [Environment]::GetFolderPath("Desktop")
$w = New-Object -ComObject WScript.Shell

function New-BridgeShortcut($name, $targetBat, $desc) {
    $lnk = Join-Path $desk $name
    $s = $w.CreateShortcut($lnk)
    $s.TargetPath = $targetBat
    $s.WorkingDirectory = $proj
    $s.Description = $desc
    $s.Save()
    Write-Host "OK: $lnk -> $targetBat"
}

New-BridgeShortcut "NMEA Serial Bridge.lnk" $bat "NMEA bridge: silent start, saved UI or layout picker (pythonw + launcher.py)"
if (Test-Path $batMenu) {
    New-BridgeShortcut "NMEA Serial Bridge (console menu).lnk" $batMenu "NMEA bridge: numbered UI menu in a console window"
}

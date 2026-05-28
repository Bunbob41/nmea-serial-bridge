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

$iconIco = Join-Path $proj "assets\app-icon.ico"

function New-BridgeShortcut($name, $targetPath, $desc, $iconPath) {
    $lnk = Join-Path $desk $name
    $s = $w.CreateShortcut($lnk)
    $s.TargetPath = $targetPath
    $s.WorkingDirectory = $proj
    $s.Description = $desc
    if ($iconPath -and (Test-Path $iconPath)) {
        $s.IconLocation = $iconPath
    }
    $s.Save()
    Write-Host "OK: $lnk -> $targetPath"
}

$launchTarget = $bat
$launchIcon = $iconIco
$exeCandidates = @(
    (Join-Path $proj "serial-link.exe"),
    (Join-Path $proj "dist\serial-link\serial-link.exe")
)
foreach ($exe in $exeCandidates) {
    if (Test-Path $exe) {
        $launchTarget = $exe
        # Use the embedded exe icon (full multi-size .ico from the build).
        $launchIcon = "$exe,0"
        break
    }
}

New-BridgeShortcut "Serial Link.lnk" $launchTarget "Serial Link: saved UI or layout picker" $launchIcon
if (Test-Path $batMenu) {
    New-BridgeShortcut "Serial Link (console menu).lnk" $batMenu "Serial Link: numbered UI menu in a console window" $launchIcon
}

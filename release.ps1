# Build Windows zip for GitHub Releases.
# Usage:
#   .\release.ps1              # build + zip only
#   .\release.ps1 -Publish     # also: git tag + gh release upload
#   .\release.ps1 -SkipTests   # faster iteration (skip unittest in build.ps1)
param(
    [switch]$Publish,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Version from version.py
$versionLine = Get-Content version.py | Where-Object { $_ -match '__version__' }
if ($versionLine -match '"([^"]+)"') {
    $Version = $Matches[1]
} else {
    throw "Could not read __version__ from version.py"
}

$distDir = Join-Path $PSScriptRoot "dist\nmea-serial-bridge"
$zipName = "nmea-serial-bridge-v$Version-win64.zip"
$zipPath = Join-Path $PSScriptRoot "dist\$zipName"

Write-Host "=== NMEA Serial Bridge release v$Version ===" -ForegroundColor Cyan

if ($SkipTests) {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    python -m pip install --upgrade pip -q 2>&1 | Out-Null
    python -m pip install -r requirements.txt -q 2>&1 | Out-Null
    python -m pip install "pyinstaller>=6.0" -q 2>&1 | Out-Null
    $ErrorActionPreference = $prevEap
    python -m PyInstaller nmea_serial_bridge.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} else {
    & "$PSScriptRoot\build.ps1"
}

if (-not (Test-Path (Join-Path $distDir "nmea-serial-bridge.exe"))) {
    throw "Build failed: missing $distDir\nmea-serial-bridge.exe"
}

Write-Host "Zipping -> dist\$zipName" -ForegroundColor Cyan
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $distDir -DestinationPath $zipPath -Force

$sizeMb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "OK: $zipPath ($sizeMb MB)" -ForegroundColor Green
Write-Host ""
Write-Host "On another PC: unzip and run nmea-serial-bridge\nmea-serial-bridge.exe"
Write-Host "First run shows a layout picker; choice is saved under %USERPROFILE%\.cursor-udp-com-bridge\"

if (-not $Publish) {
    Write-Host ""
    Write-Host "To publish on GitHub:" -ForegroundColor Yellow
    Write-Host "  .\release.ps1 -Publish"
    Write-Host "  # or upload dist\$zipName manually at https://github.com/Bunbob41/nmea-serial-bridge/releases/new"
    exit 0
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "gh CLI not found. Install GitHub CLI or upload the zip manually."
}

$tag = "v$Version"
$existing = git tag -l $tag
if (-not $existing) {
    git tag $tag
    git push origin $tag
} else {
    Write-Host "Tag $tag already exists; skipping tag create." -ForegroundColor Yellow
}

$notes = @"
Windows x64 one-folder build (PyInstaller).

- Unzip and run ``nmea-serial-bridge.exe`` (keep the whole folder).
- First launch: pick Standard / Minimal / Log-first UI.
- Bench preset uses ``bench_defaults.json`` beside the exe.
- SmartScreen may warn (unsigned app).

Source: branch feature/multi-ui-layouts-v0.5
"@

gh release view $tag 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Release $tag exists; uploading asset..." -ForegroundColor Yellow
    gh release upload $tag $zipPath --clobber
} else {
    gh release create $tag $zipPath --title $tag --notes $notes
}

Write-Host "Published: https://github.com/Bunbob41/nmea-serial-bridge/releases/tag/$tag" -ForegroundColor Green

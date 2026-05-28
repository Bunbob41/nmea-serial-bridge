# Build Windows zip for GitHub Releases.
# Usage:
#   .\release.ps1                 # build + zip only
#   .\release.ps1 -Publish        # build + zip + git tag + gh release upload
#   .\release.ps1 -PublishOnly    # skip build: upload existing dist\...zip (after gh auth)
#   .\release.ps1 -SkipTests      # faster iteration (skip unittest in build.ps1)
param(
    [switch]$Publish,
    [switch]$SkipTests,
    [switch]$PublishOnly
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

$distDir = Join-Path $PSScriptRoot "dist\serial-link"
$zipName = "serial-link-v$Version-win64.zip"
$zipPath = Join-Path $PSScriptRoot "dist\$zipName"

$doPublish = $Publish -or $PublishOnly
if ($PublishOnly -and $SkipTests) {
    Write-Host "Note: -SkipTests is ignored with -PublishOnly (no build)." -ForegroundColor DarkGray
}

Write-Host "=== Serial Link release v$Version ===" -ForegroundColor Cyan

if ($PublishOnly) {
    if (-not (Test-Path $zipPath)) {
        throw "Missing $zipPath. Run .\release.ps1 once to build and zip, then .\release.ps1 -PublishOnly"
    }
    Write-Host "PublishOnly: using existing zip (no build)." -ForegroundColor Cyan
} else {
    if ($SkipTests) {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        python -m pip install --upgrade pip -q 2>&1 | Out-Null
        python -m pip install -r requirements.txt -q 2>&1 | Out-Null
        python -m pip install -r requirements-web.txt -q 2>&1 | Out-Null
        python -m pip install "pyinstaller>=6.0" -q 2>&1 | Out-Null
        $ErrorActionPreference = $prevEap
        python -m PyInstaller nmea_serial_bridge.spec --noconfirm
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
        python "$PSScriptRoot\tools\check_frozen_bundle.py" $distDir
        if ($LASTEXITCODE -ne 0) { throw "check_frozen_bundle failed" }
    } else {
        python "$PSScriptRoot\tools\sync_version_info.py"
        if ($LASTEXITCODE -ne 0) { throw "sync_version_info failed" }
        & "$PSScriptRoot\build.ps1"
    }

    if (-not (Test-Path (Join-Path $distDir "serial-link.exe"))) {
        throw "Build failed: missing $distDir\serial-link.exe"
    }

    python "$PSScriptRoot\tools\check_frozen_bundle.py" $distDir
    if ($LASTEXITCODE -ne 0) {
        throw "check_frozen_bundle failed - Web dashboard will not work in the zip"
    }

    Write-Host "Zipping -> dist\$zipName" -ForegroundColor Cyan
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    $zipOk = $false
    $zipErr = $null
    for ($i = 0; $i -lt 5 -and -not $zipOk; $i++) {
        try {
            Compress-Archive -Path $distDir -DestinationPath $zipPath -Force
            $zipOk = $true
        } catch {
            $zipErr = $_
            if (Test-Path $zipPath) {
                Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
            }
            Start-Sleep -Milliseconds (600 + ($i * 400))
        }
    }
    if (-not $zipOk) {
        throw "Zip creation failed after retries: $zipErr"
    }
}

$sizeMb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "OK: $zipPath ($sizeMb MB)" -ForegroundColor Green

$envLockPath = Join-Path $PSScriptRoot "dist\build-env-v$Version.txt"
$manifestPath = Join-Path $PSScriptRoot "dist\release-manifest-v$Version.json"
$zipHash = (Get-FileHash $zipPath -Algorithm SHA256).Hash
$exePath = Join-Path $distDir "serial-link.exe"
$exeHash = ""
if (Test-Path $exePath) {
    $exeHash = (Get-FileHash $exePath -Algorithm SHA256).Hash
}
$requirementsHash = (Get-FileHash (Join-Path $PSScriptRoot "requirements.txt") -Algorithm SHA256).Hash
$pythonVersion = ((python --version) 2>&1 | Out-String).Trim()
$pipVersion = ((python -m pip --version) 2>&1 | Out-String).Trim()
$pyinstallerVersion = ((python -m PyInstaller --version) 2>&1 | Out-String).Trim()

@(
    "version=$Version",
    "timestamp_utc=$(Get-Date -Format o)",
    "python=$pythonVersion",
    "pip=$pipVersion",
    "pyinstaller=$pyinstallerVersion",
    "",
    "pip-freeze:",
    ((python -m pip freeze | Sort-Object) -join "`n")
) -join "`n" | Set-Content -Path $envLockPath -Encoding UTF8

$envLockHash = (Get-FileHash $envLockPath -Algorithm SHA256).Hash
$manifest = [ordered]@{
    version = $Version
    created_utc = (Get-Date -Format o)
    python = $pythonVersion
    pip = $pipVersion
    pyinstaller = $pyinstallerVersion
    requirements_sha256 = $requirementsHash
    env_lock_file = (Split-Path $envLockPath -Leaf)
    env_lock_sha256 = $envLockHash
    artifacts = @(
        [ordered]@{
            file = (Split-Path $zipPath -Leaf)
            sha256 = $zipHash
            size_bytes = (Get-Item $zipPath).Length
        },
        [ordered]@{
            file = (Split-Path $exePath -Leaf)
            sha256 = $exeHash
            size_bytes = if (Test-Path $exePath) { (Get-Item $exePath).Length } else { 0 }
        }
    )
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding UTF8
Write-Host "Build env lock: $envLockPath" -ForegroundColor DarkGray
Write-Host "Manifest: $manifestPath" -ForegroundColor DarkGray
Write-Host ""
Write-Host "On another PC: unzip and run serial-link\serial-link.exe"
Write-Host "First run shows a layout picker; choice is saved under %USERPROFILE%\.cursor-udp-com-bridge\"

if (-not $doPublish) {
    Write-Host ""
    Write-Host "To publish on GitHub:" -ForegroundColor Yellow
    Write-Host "  gh auth login    # once per machine"
    Write-Host "  .\release.ps1 -Publish"
    Write-Host "  .\release.ps1 -PublishOnly   # upload existing zip only (no rebuild; use after gh login)"
    Write-Host "  # or upload dist\$zipName manually at https://github.com/Bunbob41/nmea-serial-bridge/releases/new"
    exit 0
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "gh CLI not found. Install GitHub CLI or upload the zip manually."
}

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
$null = gh auth status 2>&1
$ghAuthed = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap
if (-not $ghAuthed) {
    throw "GitHub CLI is not logged in. Run: gh auth login`nThen: .\release.ps1 -PublishOnly   (uses existing zip without rebuilding)"
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
Windows x64 one-folder build (PyInstaller) — **v$Version**.

- Unzip and run ``serial-link.exe`` (keep the whole folder).
- First launch: pick Standard or Field UI; choice persists under ``%USERPROFILE%\.cursor-udp-com-bridge\``.
- **Survey HUD + Dashboard** (View / top bar **HUD**): metrics pop-out plus bridge-trust checklist.
- **Presets tab**: click to edit survey fields; **Load** or double-click applies COM/UDP/NMEA.
- **Terminal** (Tools): embedded shell + ping presets (Save / Delete / Quick chips).
- **Web dashboard** (optional): Tools → Phone → Enable Web API → **Open dashboard** (`http://127.0.0.1:8765/`).
- **Grid layout (beta)**: ``/static/layouts/gridstack/``.
- Layout switch + single-instance lock reduce duplicate ``python.exe`` after UI changes.
- Bench preset uses ``bench_defaults.json`` beside the exe.
- **Unsigned** — SmartScreen may warn. See ``docs/OPERATOR_GUIDE.md``.
"@

$ErrorActionPreference = "SilentlyContinue"
$null = gh release view $tag 2>&1
$releaseExists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = "Stop"

if ($releaseExists) {
    Write-Host "Release $tag exists; uploading asset..." -ForegroundColor Yellow
    gh release upload $tag $zipPath --clobber
    gh release upload $tag $manifestPath --clobber
    gh release upload $tag $envLockPath --clobber
} else {
    gh release create $tag $zipPath $manifestPath $envLockPath --title $tag --notes $notes
}

Write-Host "Published: https://github.com/Bunbob41/nmea-serial-bridge/releases/tag/$tag" -ForegroundColor Green

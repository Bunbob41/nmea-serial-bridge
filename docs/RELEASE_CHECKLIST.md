# Release checklist (Windows x64)

Use before tagging **`vX.Y.Z`** from `version.py`.

## 1. Version and docs

- [ ] `version.py` bumped; `python tools/sync_version_info.py` (updates `version_info.txt`)
- [ ] `CHANGELOG.md` has `## vX.Y.Z` at top
- [ ] `README.md` / `docs/OPERATOR_GUIDE.md` updated if operator-visible behavior changed

## 2. Automated gates

```powershell
python tools\sync_version_info.py
python verify_all.py
python -m unittest discover -s . -p "test_*.py" -q
```

- [ ] `verify_all.py` exit 0 (stop bridge GUI if UDP :10110 is in use, or accept skipped HW steps)
- [ ] Unit tests OK (Windows may show Qt `0xC0000409` after OK — `run_unittests.py` / `verify_all` treat as pass)

## 3. Build and zip

```powershell
.\build.ps1
# or full release pipeline:
.\release.ps1
```

- [ ] `dist\serial-link\serial-link.exe` exists
- [ ] `dist\serial-link\_internal\web\static\` includes dashboard + `layouts/gridstack/` + vendor (PyInstaller one-folder layout)
- [ ] `dist\serial-link-vX.Y.Z-win64.zip` created
- [ ] Note zip size (~650 MB) and SHA256 in `dist\release-manifest-vX.Y.Z.json`

## 4. Smoke on clean folder (unzipped copy)

- [ ] Launcher: Standard and Field open; Start/Stop visible
- [ ] `GET /` opens grid dashboard; `/static/index.html` is classic backup
- [ ] Optional: Grid layout beta loads at `/static/layouts/gridstack/`
- [ ] Bench preset loads; `check_setup.py` / Diagnostics checks usable

## 5. Publish (optional)

```powershell
gh auth login   # once
.\release.ps1 -Publish
# or upload only:
.\release.ps1 -PublishOnly
```

- [ ] Git tag `vX.Y.Z` matches `version.py`
- [ ] Release notes mention unsigned SmartScreen, web dashboard, grid beta URL

## Known risks

- **Unsigned** PyInstaller folder — SmartScreen warning until code-signed.
- **UDP 10110** — OpenCPN or another app binding the port breaks bench checks.
- **LAN web API** — off by default; token + firewall if enabled.

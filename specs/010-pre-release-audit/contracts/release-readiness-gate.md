# Contract: Release Readiness Gate

**Feature**: `010-pre-release-audit` (US4–6, FR-409–414, SC-404–SC-406)

## Public GitHub release MUST

All checks exit **0** on the release commit/tag:

```powershell
cd C:\Users\Morgan\Projects\udp-com-bridge
python tools\sync_version_info.py
python tools\make_app_icon.py
python verify_all.py
python -m unittest discover -s . -p "test_*.py"
python -m PyInstaller nmea_serial_bridge.spec --noconfirm
python tools\check_frozen_bundle.py dist\serial-link
.\release.ps1   # or build.ps1 + manual zip — NOT -SkipTests for first public release
```

Equivalent: **`.\release.ps1`** without `-SkipTests` (runs `build.ps1` internally).

## Gate matrix

| Gate | Command / artifact | Pass criterion |
|------|-------------------|----------------|
| G1 Version | `version.py`, `version_info.txt`, window title | Same semver string |
| G2 Compile + verify | `verify_all.py` | Exit 0 |
| G3 Unit tests | `unittest discover` | Exit 0 |
| G4 Icon assets | `test_app_icon.py` inside verify_all | Exit 0 |
| G5 Frozen bundle | `check_frozen_bundle.py dist\serial-link` | Exit 0; includes `assets/app-icon.ico` |
| G6 Audit P0 | `docs/pre-release-audit-inventory.md` | Zero open P0 |
| G7 Icon manual | [app-icon-acceptance.md](./app-icon-acceptance.md) | Sign-off row completed |
| G8 Modern UI | [quickstart.md](../quickstart.md) §3 | Zero new P0 |
| G9 Zip artifact | `dist\serial-link-vX.Y.Z-win64.zip` | Contains `serial-link.exe` |
| G10 Docs | CHANGELOG `## vX.Y.Z`, README frozen path | Matches artifact names |

## Waivers (require CHANGELOG note)

| Waiver | Allowed when |
|--------|--------------|
| `-SkipTests` build | Internal iteration only—not first public release |
| `-PublishOnly` | Re-upload existing zip; no code changes |
| Open P1 at ship | Each listed in CHANGELOG **Deferred** with one-line operator impact |
| Open P0 | **Not allowed** for public release without retag |

## Release notes template (GitHub)

```markdown
## Serial Link vX.Y.Z — Windows x64

### Install
1. Download `serial-link-vX.Y.Z-win64.zip`
2. Extract folder `serial-link\`
3. Run `serial-link.exe` — if SmartScreen warns: **More info → Run anyway**
4. See `docs\GETTING_STARTED.md` in the zip

### Highlights
- [Icon fix — readable taskbar/Explorer branding]
- [Audit fixes — list closed P0/P1 IDs]

### Deferred
- [P1/P2 items not in this release]

### Verified
- verify_all + full unittest on Windows 10/11
- Frozen bundle check passed
```

## Version bump

- **Minor** v1.34.0 for this epic (icon + release gates + inventory).
- Sync `version_info.txt` via `tools/sync_version_info.py` before PyInstaller.

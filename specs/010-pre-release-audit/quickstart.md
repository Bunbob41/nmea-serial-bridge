# Quickstart: Pre-Release Full App Audit

**Branch**: `2036-pre-release-audit` | **Target**: v1.34.0

## Prerequisites

- Windows 10/11 x64
- Python 3.10+ with project deps (`requirements.txt`, `requirements-web.txt`)
- Pillow installed (icon script)
- Modern UI default: `python bridge_gui.py`

## 1. Automated gates (must pass before tag)

```powershell
cd C:\Users\Morgan\Projects\udp-com-bridge
python tools\sync_version_info.py
python tools\make_app_icon.py
python verify_all.py
python -m unittest discover -s . -p "test_*.py"
python -m PyInstaller nmea_serial_bridge.spec --noconfirm
python tools\check_frozen_bundle.py dist\serial-link
```

Expected after implement: `verify_all` runs `test_app_icon`; frozen bundle includes `assets/app-icon.ico`.

**Full release dry-run**:

```powershell
.\release.ps1
# Produces dist\serial-link-v1.34.0-win64.zip (version from version.py)
```

Do **not** use `-SkipTests` for first public GitHub release.

## 2. Icon acceptance (SC-401, PKG-ICON-01)

Follow [app-icon-acceptance.md](./contracts/app-icon-acceptance.md):

1. Confirm `make_app_icon` logs **`from app-icon-source.png`**.
2. Open `dist\serial-link\serial-link.exe` in Explorer — glyph visible, not blue square.
3. Pin to taskbar; run app — title bar + taskbar match.
4. Run `.\create_desktop_shortcut.ps1` — shortcut icon matches.

**Fail if**: uniform dark/blue tile with no connector detail at medium Explorer icons.

## 3. Modern UI audit (SC-403)

Window sizes: **640×420** (minimum) and **1280×720**.

Toggle **View → Tools navigation → Sidebar / Top chips** for Setup + Control tabs.

| Page | 640×420 check | 1280×720 check |
|------|---------------|----------------|
| Control | Serial \| Network side-by-side; Start visible | Advanced net expanded readable |
| Presets | Live status visible | Save/load row intact |
| Hub | Banner + cards; no duplicate title | Refresh/Unlock toolbar |
| Phone | Cards stack; QR + port usable | Same, no horizontal clip |
| NMEA | Mode chips fit | Status chip tooltips |
| Activity | Terminal toolbar one row | Filters + wrap |
| Terminal | Toolbar fits | Hex/filter row |
| Guide | Links clickable | — |
| Checks | Cards expand | — |
| Inject | Send box usable | — |
| Black box / File log | Paths readable | — |

Log results in `docs/pre-release-audit-inventory.md` verification table.

## 4. Version integrity (SC-405)

After build:

- [ ] `version.py` matches zip name
- [ ] exe **Properties → Details** version matches
- [ ] Window title includes same version

## 5. Bridge spot-check (optional bench)

If com0com + UDP available:

1. Load Desk preset; UDP listen; Start.
2. Confirm Hz / drops update in status.
3. Stop; confirm UI responsive.

Otherwise: rely on automated suite + verification log note "automated only".

## 6. Release narrative

- [ ] CHANGELOG `## v1.34.0` — icon fix + closed audit IDs
- [ ] README frozen-build path matches `dist\serial-link\serial-link.exe`
- [ ] OPERATOR_GUIDE SmartScreen line present (§install)
- [ ] Open P1 deferred items listed in CHANGELOG if any

## 7. GitHub publish (when ready)

```powershell
.\release.ps1 -Publish
```

Requires `gh auth login` and maintainer sign-off on gates G1–G10 in [release-readiness-gate.md](./contracts/release-readiness-gate.md).

## Fail-fast summary

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Blue square icon | Missing source PNG / weak shell layer | Restore `app-icon-source.png`; tune `make_app_icon.py` |
| Old icon after rebuild | Windows icon cache | VM test or cache bust (acceptance §F) |
| verify_all icon fail | Stale ICO | Regenerate; commit assets |
| check_frozen_bundle missing ico | Manifest gap | Add to `frozen_bundle_manifest.py` |
| Phone clipped at min | Regression | Compare v1.33.1 stack threshold |

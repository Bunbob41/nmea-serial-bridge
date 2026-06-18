# Contract: App Icon Acceptance

**Feature**: `010-pre-release-audit` (US1, FR-401–403, SC-401)

## Goal

Frozen **Serial Link** branding is **recognizable at Windows shell sizes** (taskbar, Explorer, shortcuts, title bar)—not a featureless dark/blue square.

## Automated gate (CI)

Run before merge / release:

```powershell
python tools\make_app_icon.py
python -m unittest test_app_icon.py -v
```

**Must pass**:

| Test | Requirement |
|------|-------------|
| `test_png_artwork_fills_canvas` | Glyph bbox fill ≥ 72% of 512px canvas |
| `test_32px_shell_layer_has_bright_glyph` | ≥40 bright pixels; ≥80 high-ink pixels at 32×32 |
| `test_16px_shell_layer_has_bright_glyph` | Same thresholds at 16×16 (implement phase) |
| `test_ico_includes_windows_dpi_sizes` | ICO contains 32, 48, 256 (and 16 after implement) |

**Also**: `verify_all.py` includes `test_app_icon`; `check_frozen_bundle` confirms `assets/app-icon.ico` in dist.

## Manual acceptance checklist

Perform on **fresh full build** (`.\build.ps1` or `.\release.ps1` without `-SkipTests`):

### A. Build hygiene

- [ ] `assets/app-icon-source.png` exists (not PNG-only self-loop)
- [ ] Console shows `from app-icon-source.png` when running `make_app_icon.py`
- [ ] `dist\serial-link\serial-link.exe` timestamp matches build

### B. Explorer

- [ ] Medium icons: connector glyph visible on dark squircle tile
- [ ] **Fail** if icon appears as uniform blue/dark square with no interior detail

### C. Running app

- [ ] Taskbar button shows same glyph (pin to taskbar)
- [ ] Title bar icon matches
- [ ] Alt+Tab thumbnail icon readable

### D. Shortcut

- [ ] `.\create_desktop_shortcut.ps1` → shortcut uses same icon as EXE

### E. Dev parity

- [ ] `python bridge_gui.py` title bar icon matches frozen family

### F. Icon cache (if rebuild looks wrong)

- [ ] Rename exe temporarily OR test on clean VM OR clear `%LocalAppData%\IconCache.db` (document in verification log)

## Reviewer sign-off

| Reviewer | Date | Pass (Y/N) | Notes |
|----------|------|------------|-------|
| | | | |

**SC-401**: ≥1 maintainer pass required; ideal 3/3 reviewers identify “serial/network bridge” at taskbar size.

## Non-goals

- Code signing / SmartScreen removal
- macOS / Linux icon variants
- Favicon for web dashboard (separate if needed)

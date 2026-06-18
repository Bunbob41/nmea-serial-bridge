# Research: Pre-Release Full App Audit

**Feature**: `010-pre-release-audit` | **Date**: 2026-06-17

## R1 — EXE icon “blue square” root cause

**Decision**: Treat **PKG-ICON-01** as a **pipeline + art + shell-contrast** problem, not a PyInstaller wiring bug. Fix in order: (1) restore **`assets/app-icon-source.png`**, (2) strengthen **shell-tier** (≤48px) contrast in `tools/make_app_icon.py`, (3) add **automated gates** (`verify_all` + frozen bundle manifest), (4) validate on **fresh build** with icon-cache note.

**Findings**:

| Layer | Status | Notes |
|-------|--------|-------|
| PyInstaller embed | ✅ Wired | `nmea_serial_bridge.spec` sets `icon=assets/app-icon.ico` on `EXE` block |
| Runtime window icon | ✅ Wired | `ui/app_icon.py` loads `assets/app-icon.ico` / `.png` from bundle |
| Build path | ⚠️ Partial | `build.ps1` runs `make_app_icon.py` before PyInstaller; **`release.ps1 -SkipTests` does not** |
| Source art | ❌ Missing | **`app-icon-source.png` absent** — script falls back to **`app-icon.png`** (self-referential regeneration) |
| Automated tests | ⚠️ Orphan | `test_app_icon.py` passes but is **not** in `verify_all.py` |
| Frozen bundle check | ❌ Gap | `check_frozen_bundle.py` does **not** assert `assets/app-icon.ico` in dist |
| Operator symptom | ❌ Open | Dark squircle `#1a1d27` / shell `#242a3a` reads as **uniform blue/dark tile** when thin RJ-45/DB-9 strokes vanish at 16–32px |

**Rationale**:

- `make_app_icon.py` already implements shell vs detail masters and ICO multi-size layers (16–256px).
- Existing unit tests assert bright pixels at 32px — yet operator still sees a blue square on **frozen EXE**, implying either (a) degraded source art loop, (b) insufficient stroke weight at 16px taskbar, or (c) stale ICO in a `-SkipTests` build / Windows icon cache.
- Missing `app-icon-source.png` prevents editing high-resolution matte art per `assets/README.md`.

**Fix strategy** (implement phase):

1. Add **`app-icon-source.png`** — export current best art or simplified **bold connector** on white/transparent matte (editable source of truth).
2. Tune shell path: increase **`SHELL_INK_FILL`**, **`SHELL_DILATE_PX`**, and/or use **near-white glyph** on slightly lighter tile for ≤32px; add **`test_16px_shell_layer_has_bright_glyph`**.
3. Add **`test_app_icon.py`** to `verify_all.py` step list.
4. Add `assets/app-icon.ico` + `assets/app-icon.png` to **`tools/frozen_bundle_manifest.py`** / `FROZEN_STATIC_FILES`.
5. Call `make_app_icon.py` in **`release.ps1`** before PyInstaller even on `-SkipTests`.
6. Document manual acceptance in contract `app-icon-acceptance.md` (Explorer + taskbar + shortcut + cache-bust).

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Only clear Windows icon cache | Does not fix art/pipeline; false confidence |
| Single 256px ICO layer only | Windows shell picks wrong downscale; taskbar unreadable |
| Replace with generic Qt/stock icon | Loses Serial Link branding |
| Embed icon only in `version_info.txt` | Windows exe icon comes from PyInstaller `icon=` + embedded ICO, not version resource alone |
| Purchase code signing now | Out of scope (spec); docs cover SmartScreen instead |

---

## R2 — Audit inventory structure

**Decision**: Create **`docs/pre-release-audit-inventory.md`** extending 008 matrix with **Modern + packaging** ID prefixes; keep **`docs/ui-audit-inventory.md`** as historical Standard/Field record (no duplicate rows).

**ID prefixes**:

| Prefix | Surface |
|--------|---------|
| `PKG-*` | Packaging, icon, version, zip |
| `MOD-*` | Modern UI tab/area |
| `BRG-*` | Bridge reliability spot-check |
| `WEB-*` | Phone dashboard / web static |
| `DOC-*` | README, CHANGELOG, OPERATOR_GUIDE |

**Severity**: Reuse [008 ui-audit-matrix](../008-ui-journey-modernization/contracts/ui-audit-matrix.md) P0/P1/P2 definitions; add packaging P0 for unreadable exe icon.

**Ship gate**: Zero open P0; P1 fixed or CHANGELOG **Deferred** (one line each).

---

## R3 — Modern UI audit surfaces

**Decision**: Manual checklist covers **11 Modern nav sections** at **640×420** and **1280×720**, each with **sidebar** and **top-chips** navigation (where applicable).

**Pages** (from `build_modern_tools_nav_groups()`):

| section_id | Label | Min-width risk |
|------------|-------|----------------|
| `control` | Control | Side-by-side forms (v1.32.7 guard) |
| `presets` | Presets | Live status strip |
| `hub` | Hub | Card grid + banner |
| `nmea` | NMEA | Mode chips |
| `phone` | Phone | Stack at &lt;880px (v1.33.1 guard) |
| `activity` | Activity | Terminal toolbar |
| `black_box` | Black box | Path controls |
| `file_log` | File log | Log controls |
| `guide` | Guide | Doc links |
| `inject` | Inject | Send panel |
| `terminal` | Terminal | Filter bar + wrap |
| `checks` | Checks | Diagnostics cards |

**Automation**: Extend `test_ui_tabs.py` only where cheap regression hooks exist; otherwise log manual row in inventory verification table.

---

## R4 — Release gate automation

**Decision**: Public GitHub release MUST use **`.\release.ps1`** (full `build.ps1` path), not `-SkipTests` / `-PublishOnly`, unless maintainer waiver in CHANGELOG.

**Existing gates**:

| Gate | Script | In full build? |
|------|--------|----------------|
| Compile | `verify_all.py` | ✅ |
| Unittests | `run_unittests.py` | ✅ |
| Version sync | `sync_version_info.py` | ✅ |
| Frozen bundle | `check_frozen_bundle.py` | ✅ |
| Icon assets | `test_app_icon.py` | ❌ → add |

**Post-build manual**: Icon acceptance checklist; Modern UI smoke; optional com0com UDP spot-check.

---

## R5 — Documentation & SmartScreen

**Decision**: **Verify** existing OPERATOR_GUIDE §install SmartScreen line (already present at line ~46); add **release notes template** bullet in quickstart if README zip path drift found.

**Finding**: SmartScreen guidance exists; **DOC-SMART-01** closes by confirmation + link from pre-release inventory, not rewrite.

---

## R6 — Scope deferrals

**Decision**: **`docs/ROADMAP.md`** items (MAVLink injector, kernel COM) stay **deferred**; **009 T021** manual smoke recorded in inventory verification log during implement (MOD-SMOKE-01).

**No bridge_core changes** expected unless audit discovers P0 protocol bug.

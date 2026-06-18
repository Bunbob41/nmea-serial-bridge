# Implementation Plan: Pre-Release Full App Audit

**Branch**: `2036-pre-release-audit` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Full app audit before GitHub release—EXE icon fix, Modern UI polish pass, audit inventory, packaging gates, docs, bridge spot-check.

**Builds on**: [008-ui-journey-modernization](../008-ui-journey-modernization/spec.md); [009-modern-control-polish](../009-modern-control-polish/spec.md) (v1.33.x baseline).

**Target release**: **v1.34.0** (minor—icon/branding fix + release-readiness gates + audit inventory).

## Summary

Structured pre-release epic in **priority order**:

1. **Fix frozen EXE icon** (P0 `PKG-ICON-01`) — restore source art, strengthen shell-tier ICO layers, wire automated + frozen-bundle checks.
2. **Publish audit inventory** — `docs/pre-release-audit-inventory.md` with Modern + packaging rows and ship gates.
3. **Modern UI manual pass** at 640×420 and 1280×720; fix any new P0/P1 layout defects found.
4. **Harden release pipeline** — icon regen on all build paths, `test_app_icon` in `verify_all`, version sync verification.
5. **Bridge + docs + release dry-run** — full test suite, CHANGELOG/README, optional `release.ps1` zip without `-Publish`.

No `bridge_core.py` changes unless audit discovers a P0 protocol defect.

## Technical Context

**Language/Version**: Python 3.10+; PySide6; PyInstaller ≥6.0; Pillow (icon script, dev/CI)  
**Primary Dependencies**: Existing `tools/make_app_icon.py`, `nmea_serial_bridge.spec`, `build.ps1`, `release.ps1`, `verify_all.py`, `check_frozen_bundle.py`; **no new mandatory pip packages**  
**Storage**: Static assets under `assets/`; audit inventory under `docs/`  
**Testing**: `test_app_icon.py` (extend); `test_ui_tabs.py` (regression as needed); full `verify_all.py` + unittest discover; manual icon + Modern UI checklists in quickstart  
**Target Platform**: Windows 10/11 x64 desktop; Modern UI primary  
**Performance Goals**: Icon script &lt;5s; no runtime bridge impact  
**Constraints**: Constitution I–V; unsigned builds (document SmartScreen); ROADMAP epics out of scope  
**Scale/Scope**: ~6–10 files (assets, tools, tests, docs, scripts); 3 contracts; 1 inventory doc; manual smoke ~45 min

## Constitution Check

| Principle | Gate | Pre-design | Post-design |
|-----------|------|------------|-------------|
| I. Bridge-Core Separation | Icon/audit UI/docs only; no protocol logic in GUI | ✅ | ✅ |
| II. Survey Operator Trust | Icon + layout fixes improve first-run trust; Start/Stop unchanged | ✅ | ✅ |
| III. Verifiable Changes | `test_app_icon` in verify_all; inventory + quickstart gates | ✅ | ✅ |
| IV. Version & Release | v1.34.0 + CHANGELOG; version_info sync on build | ✅ | ✅ |
| V. Resilience | Bridge spot-check via existing tests; no new queues | ✅ | ✅ |

**Gate result**: ✅ PASS

## Architecture

### Icon pipeline (US1, FR-401–403)

```text
assets/app-icon-source.png  ← EDIT (restore / replace bold connector art)
        │
        ▼  tools/make_app_icon.py
        ├── assets/app-icon.png   (512px detail squircle)
        └── assets/app-icon.ico   (multi-size: 16–256, shell≤48px)
                │
                ├── nmea_serial_bridge.spec  icon=  → serial-link.exe
                ├── ui/app_icon.py           → Qt window icon
                └── create_desktop_shortcut.ps1
```

**Validation layers**:

| Layer | Check |
|-------|-------|
| Unit | `test_app_icon.py` — PNG fill, 16/32px bright glyph, ICO sizes |
| CI | `verify_all.py` includes icon tests |
| Frozen | `check_frozen_bundle.py` — `assets/app-icon.ico` in dist |
| Manual | [app-icon-acceptance.md](./contracts/app-icon-acceptance.md) |

### Audit inventory (US2, FR-404–406)

```text
docs/pre-release-audit-inventory.md
  ├── Seed rows from spec (PKG-ICON-01, …)
  ├── Modern UI findings (MOD-*)
  ├── Verification log (date, resolution, P0 open)
  └── Deferred / ROADMAP pointer
```

Extends severity definitions from [008 ui-audit-matrix](../008-ui-journey-modernization/contracts/ui-audit-matrix.md) via [modern-ui-audit-matrix.md](./contracts/modern-ui-audit-matrix.md).

### Release readiness (US4–6, FR-409–414)

```text
build.ps1 / release.ps1
  → sync_version_info.py
  → make_app_icon.py          (all paths)
  → verify_all.py (+ icon)
  → PyInstaller
  → check_frozen_bundle.py (+ icon asset)
  → zip serial-link-vX.Y.Z-win64.zip
```

## Project Structure

### Documentation

```text
specs/010-pre-release-audit/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── app-icon-acceptance.md
│   ├── release-readiness-gate.md
│   └── modern-ui-audit-matrix.md
└── tasks.md              # /speckit-tasks

docs/
├── pre-release-audit-inventory.md   # NEW — implement
└── ui-audit-inventory.md            # KEEP — 008 historical
```

### Source Code (expected touch list)

```text
assets/app-icon-source.png     # NEW or restored
assets/app-icon.png            # regenerated
assets/app-icon.ico            # regenerated
tools/make_app_icon.py         # shell contrast tuning
tools/frozen_bundle_manifest.py
tools/check_frozen_bundle.py   # (if manifest-only insufficient)
verify_all.py                  # add test_app_icon step
release.ps1                    # make_app_icon on SkipTests path
test_app_icon.py               # 16px layer test
docs/pre-release-audit-inventory.md
docs/OPERATOR_GUIDE.md         # verify SmartScreen (minimal)
README.md / CHANGELOG.md       # release narrative
version.py                     # 1.34.0
version_info.txt               # synced
```

## Implementation Phases

### Phase A — EXE icon fix (US1, FR-401–403) **P0**

1. Restore **`assets/app-icon-source.png`** (bold RJ-45/DB-9 on white/transparent matte).
2. Tune `make_app_icon.py` shell tier for **16–32px readability** (stroke weight / contrast).
3. Regenerate PNG + ICO; extend **`test_app_icon.py`** with 16px shell test.
4. Add icon tests to **`verify_all.py`**; add ICO to **frozen bundle manifest**.
5. Ensure **`release.ps1 -SkipTests`** runs `make_app_icon.py` before PyInstaller.
6. Full `build.ps1`; manual **app-icon-acceptance** checklist.

**Exit**: SC-401 satisfied; `PKG-ICON-01` → fixed; icon tests in verify_all.

### Phase B — Audit inventory (US2, FR-404–406) **P1**

1. Create **`docs/pre-release-audit-inventory.md`** with seed rows + verification log template.
2. Cross-reference 008 inventory; link Modern matrix contract.
3. Record 009 T021 smoke outcome (`MOD-SMOKE-01`).

**Exit**: Inventory exists; P0 filter documented; gate rules in contract.

### Phase C — Modern UI pass (US3, FR-407–408) **P1**

1. Run quickstart Modern checklist at **640×420** and **1280×720** (sidebar + top-chips).
2. Fix any **P0/P1** findings; add regression tests where cheap.
3. Update inventory rows to **fixed** or **deferred**.

**Exit**: SC-403 — zero open P0 from UI pass.

### Phase D — Packaging gates (US4, FR-409–411) **P2**

1. Confirm version sync on release build (SC-405).
2. Run full `verify_all` + unittest + `check_frozen_bundle`.
3. Produce zip via `release.ps1` (no `-Publish` until maintainer ready).

**Exit**: SC-404, SC-405 pass.

### Phase E — Bridge spot-check + release narrative (US5–7, FR-412–416) **P2–P3**

1. No new bridge tests unless regression found; document spot-check in verification log.
2. CHANGELOG v1.34.0; README frozen-build lines; confirm OPERATOR_GUIDE SmartScreen.
3. List deferrals (ROADMAP, unfixed P2) in inventory + CHANGELOG.

**Exit**: SC-406 ready; release zip artifact produced.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |

## Next Step

Run **`/speckit-tasks`** to generate ordered `tasks.md` from this plan.

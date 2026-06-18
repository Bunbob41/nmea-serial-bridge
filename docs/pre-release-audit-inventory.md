# Pre-release audit inventory — feature 010

**Feature**: `specs/010-pre-release-audit` (FR-401–416)  
**Target release**: v1.34.0  
**Gate**: Zero open **P0** at tag  
**Related**: Historical Standard/Field audit → [`ui-audit-inventory.md`](ui-audit-inventory.md) (008)  
**Matrix**: [`specs/010-pre-release-audit/contracts/modern-ui-audit-matrix.md`](../specs/010-pre-release-audit/contracts/modern-ui-audit-matrix.md)  
**Release gates**: [`specs/010-pre-release-audit/contracts/release-readiness-gate.md`](../specs/010-pre-release-audit/contracts/release-readiness-gate.md)

## Ship gate summary

| Gate | Rule |
|------|------|
| P0 | **Zero open** at tag (waiver → CHANGELOG) |
| P1 | Fixed **or** one-line entry in CHANGELOG **Deferred** |
| P2 | May defer in inventory without blocking tag |
| Tests | `verify_all.py` + full unittest discover exit 0 |
| Icon | Manual sign-off in `specs/010-pre-release-audit/contracts/app-icon-acceptance.md` |

---

## Findings

| ID | Surface | Type | Severity | Status | Notes |
|----|---------|------|----------|--------|-------|
| PKG-ICON-01 | packaging | branding | P0 | **fixed** | v1.34.0 — restored `app-icon-source.png`, stronger shell ICO layers, verify_all + frozen bundle gates |
| AUDIT-INV-01 | docs | process | P1 | **fixed** | v1.34.0 — this inventory replaces ad-hoc 008-only tracking for Modern release |
| MOD-SMOKE-01 | modern-all | process | P1 | **fixed** | v1.34.0 — Modern UI pass logged below; Control/Phone min-width guards in `test_ui_tabs.py` |
| PKG-VERSION-01 | packaging | copy | P2 | **fixed** | v1.34.0 — `sync_version_info.py` in build/release path verified |
| DOC-SMART-01 | docs | copy | P2 | **fixed** | OPERATOR_GUIDE §install SmartScreen line confirmed |
| ROADMAP-SCOPE-01 | docs | scope | P3 | deferred | MAVLink GPS injector + kernel COM — see `ROADMAP.md` |

### Modern UI pass (no new P0)

| ID | Surface | Type | Severity | Status | Notes |
|----|---------|------|----------|--------|-------|
| MOD-CONTROL-01 | modern-control | layout | P2 | fixed | v1.32.7 — side-by-side at 640×420 (`test_ui_tabs`) |
| MOD-PHONE-01 | modern-phone | layout | P2 | fixed | v1.33.1 — stack below 880px content width |
| MOD-HUB-01 | modern-hub | layout | P2 | fixed | v1.32.5 — page banner, no duplicate title |

---

## Deferred (post v1.34.0)

| ID | Notes | Target |
|----|-------|--------|
| ROADMAP-SCOPE-01 | MAVLink GPS injector epic | `docs/ROADMAP.md` — promote to spec when ready |
| — | Code signing / SmartScreen removal | Separate packaging epic |

---

## Verification log

| Date | Scope | Resolution / nav | P0 open | Notes |
|------|-------|------------------|---------|-------|
| 2026-06-17 | Icon pipeline + automated gates | N/A | 0 | `make_app_icon` from source; `test_app_icon` 16/32/48/256px; verify_all app_icon step |
| 2026-06-17 | Modern UI — primary tabs | 640×420 sidebar | 0 | Control, Hub, Presets, Phone — layout guards green in `test_ui_tabs.py` |
| 2026-06-17 | Modern UI — primary tabs | 640×420 top-chips | 0 | Same; chip nav sync covered by existing tests |
| 2026-06-17 | Modern UI — full nav | 1280×720 sidebar | 0 | All 11 pages reviewed; no new P0 (009 Control/Phone polish baseline) |
| 2026-06-17 | Bridge spot-check | automated | 0 | `verify_all.py` + unittest discover (no com0com bench this pass) |
| 2026-06-17 | Packaging | version sync | 0 | `version.py` ↔ `version_info.txt` ↔ window title v1.34.0 |

**Manual icon sign-off** (Explorer + taskbar): maintainer to confirm after fresh `release.ps1` build — see app-icon-acceptance contract.

---

## Icon acceptance sign-off

| Reviewer | Date | Pass | Notes |
|----------|------|------|-------|
| Implement (automated) | 2026-06-17 | Y | 16/32px bright-pixel tests pass; source PNG committed |
| Maintainer (manual) | | | Explorer + taskbar after frozen build |

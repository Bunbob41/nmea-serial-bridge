# Data Model: Pre-Release Full App Audit

**Feature**: `010-pre-release-audit` | **Date**: 2026-06-17

## AuditRow

Single finding in `docs/pre-release-audit-inventory.md`. Not persisted in app runtime.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | e.g. `PKG-ICON-01`, `MOD-PHONE-01` |
| `surface` | enum | `packaging` \| `modern-{tab}` \| `bridge` \| `web` \| `docs` |
| `type` | enum | `branding` \| `layout` \| `copy` \| `process` \| `dead_control` \| `placeholder` |
| `severity` | enum | `P0` \| `P1` \| `P2` |
| `status` | enum | `open` \| `fixed` \| `deferred` |
| `notes` | string | Operator impact + fix version |

**Invariants**:

- At ship: count(`severity=P0` ∧ `status=open`) = **0** (unless waived in CHANGELOG).
- At ship: each open P1 MUST have CHANGELOG deferred line OR move to `fixed`.

---

## ShipGate

Release readiness checklist (logical aggregate).

| Field | Type | Rule |
|-------|------|------|
| `p0_open` | int | MUST be 0 |
| `verify_all_ok` | bool | MUST be true |
| `unittest_ok` | bool | MUST be true |
| `frozen_bundle_ok` | bool | MUST be true |
| `icon_tests_ok` | bool | MUST be true |
| `version` | semver | Single source: `version.py` |
| `version_info_synced` | bool | Matches `version.py` after sync script |
| `zip_artifact` | path | `dist/serial-link-v{version}-win64.zip` |

**Lifecycle**: `audit_open → fixes_applied → gates_green → tagged_release`

---

## IconAssetSet

Static branding files under `assets/`.

| File | Role | Editable? |
|------|------|-----------|
| `app-icon-source.png` | Master art on white/transparent matte | **Yes** |
| `app-icon.png` | 512px detail squircle (generated) | No — regenerate |
| `app-icon.ico` | Multi-size Windows ICO (generated) | No — regenerate |

**IconPipelineState**:

| Field | Type | Notes |
|-------|------|-------|
| `source_present` | bool | `app-icon-source.png` exists |
| `shell_max_px` | int | 48 — sizes ≤ this use high-contrast shell master |
| `ico_sizes` | set | Must include 16, 32, 48, 256 |
| `embedded_in_exe` | bool | PyInstaller `icon=` on build |
| `bundled_in_dist` | bool | `assets/app-icon.ico` in frozen folder |

**Acceptance**: Manual checklist SC-401 + automated bright-pixel tests at 16px and 32px.

---

## ModernUiAuditPass

Manual verification record (verification log table).

| Field | Type | Notes |
|-------|------|-------|
| `date` | date | ISO date |
| `resolution` | string | e.g. `640×420`, `1280×720` |
| `nav_mode` | enum | `sidebar` \| `top_chips` |
| `pages_checked` | list | section_ids from Modern nav |
| `p0_found` | int | New P0 during this pass |
| `tester` | string | Initials or role |

**Rule**: Both resolutions × both nav modes for primary tabs (Control, Hub, Presets, Phone) minimum; full 11 pages at 1280×720.

---

## ReleaseArtifact

GitHub release deliverable.

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | `serial-link-vX.Y.Z-win64.zip` |
| `exe_path` | string | `serial-link/serial-link.exe` inside zip |
| `unsigned` | bool | true until signing epic |
| `smartscreen_doc` | bool | OPERATOR_GUIDE covers More info → Run anyway |

---

## VerificationLogEntry

Append-only row in inventory verification section.

| Field | Type | Example |
|-------|------|---------|
| `date` | date | 2026-06-17 |
| `scope` | string | Icon acceptance + Modern 640×420 |
| `p0_open` | int | 0 |
| `notes` | string | Full build.ps1; taskbar icon readable |

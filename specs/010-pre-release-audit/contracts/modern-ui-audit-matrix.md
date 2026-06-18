# Contract: Modern UI Audit Matrix

**Feature**: `010-pre-release-audit` (US3, FR-407–408)

**Extends**: [008 ui-audit-matrix](../../008-ui-journey-modernization/contracts/ui-audit-matrix.md)

## Inventory format

Rows in **`docs/pre-release-audit-inventory.md`** use:

| Column | Description |
|--------|-------------|
| ID | `MOD-{AREA}-{NN}` or `PKG-*`, `BRG-*`, `WEB-*`, `DOC-*` |
| Surface | Modern tab or packaging/bridge/web/docs |
| Type | `layout` \| `copy` \| `branding` \| `process` \| `dead_control` \| `placeholder` |
| Severity | P0 \| P1 \| P2 |
| Status | open \| fixed \| deferred |
| Notes | Version fixed / operator impact |

**Layout** column from 008 is replaced by **Surface** for this audit (Modern-only primary).

## P0 definition (ship blocker)

- Unreadable or missing **EXE/taskbar icon** (`PKG-ICON-01`)
- Clipped **Start/Stop**, run control, or connection health at **640×420**
- Dead control that implies behavior but does nothing
- Misleading placeholder when real data exists (e.g. Phone QR without token)

## P1 definition

- Terminology mismatch vs `docs/OPERATOR_GUIDE.md`
- Min-width layout regression (stack/clipping) on Control, Phone, Hub, Terminal
- Missing audit inventory or unrecorded manual smoke (MOD-SMOKE-01)

## P2 definition

- Cosmetic hierarchy, spacing, or copy nits that do not block connect→run
- Version metadata verification chores
- Standard/Field cosmetic-only issues

## Modern pages — required manual pass

At **640×420** and **1280×720**; test **sidebar** and **top-chips** nav for Control + Setup tabs:

| ID prefix | Page | Primary checks |
|-----------|------|----------------|
| MOD-CONTROL | Control | Side-by-side Serial/Network; preset strip; advanced net expanded |
| MOD-PRESETS | Presets | Live status; load/save row |
| MOD-HUB | Hub | Banner; Refresh/Unlock; card grid |
| MOD-NMEA | NMEA | Mode chips; status |
| MOD-PHONE | Phone | Stack/wrap; QR; port spinbox; Open dashboard |
| MOD-ACTIVITY | Activity | Terminal toolbar single row |
| MOD-TERMINAL | Terminal | Filters + wrap toggle |
| MOD-INJECT | Inject | Send panel |
| MOD-GUIDE | Guide | Doc links |
| MOD-CHECKS | Checks | Diagnostics cards expand |
| MOD-LOG-* | Black box / File log | Path controls readable |

## Verification

| Resolution | Nav modes | Minimum pages |
|------------|-----------|---------------|
| 640×420 | sidebar + top-chips | Control, Hub, Presets, Phone |
| 1280×720 | sidebar + top-chips | All 11 Modern nav pages |

Record results in inventory **Verification log** table.

## Ship gate

- Zero open **P0**
- **P1** fixed or CHANGELOG deferred (one line each)
- **P2** may defer in inventory without blocking tag

## Relationship to 008 inventory

- **`docs/ui-audit-inventory.md`**: historical Standard/Field (008)—do not duplicate fixed STD/FIELD rows.
- **`docs/pre-release-audit-inventory.md`**: active gate for v1.34.x GitHub release.

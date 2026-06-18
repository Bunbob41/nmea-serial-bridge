# Implementation Plan: Modern Control Tab Polish

**Branch**: `2035-modern-control-polish` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Audit follow-ups from Control tab redesign (v1.32.4–v1.32.7)—preset status parity, advanced network styling, visual consistency, responsive clarity, tests, QSS cleanup, operator guide.

**Builds on**: [008-ui-journey-modernization](../008-ui-journey-modernization/spec.md) (Modern tools page shell); [006-phase-b-dashboard](../006-phase-b-dashboard/spec.md) (position map); [004-hub-network-discovery](../004-hub-network-discovery/spec.md) (Hub banner pattern).

**Target release**: **v1.33.0** (minor—shared live-status helper + cross-tab visual contract).

## Summary

Close seven polish items on the **Modern Control** tab without touching `bridge_core.py` or legacy layouts. Primary work:

1. **Unify preset summary styling** — Control preset strip uses the same `modernToolsLiveStatus` + `statusKind` semantics as Presets (FR-201/202).
2. **Style advanced network panel** inside the Network form card (FR-203).
3. **Fix icon/typography hierarchy** — distinct preset icon; Position track title aligned with section titles (FR-204/205).
4. **Lock minimum-width side-by-side layout** with documented sub-minimum stack threshold (FR-206/207).
5. **Add chrome unit tests** + QSS dedupe + OPERATOR_GUIDE note (FR-208–211).

Validation: extended `test_ui_tabs.py`, `verify_all.py`, manual quickstart at 640×420.

## Technical Context

**Language/Version**: Python 3.10+; PySide6; asyncio bridge unchanged  
**Primary Dependencies**: Existing `ui/modern.py`, `ui/modern_styles.py`, `ui/tool_tabs.py`, `ui/backup_status.py`, `ui/controls.py` (`advancedNetPanel`); **no new mandatory pip packages**  
**Storage**: N/A (visual prefs only; existing `ui_prefs.json` for map collapse unchanged)  
**Testing**: Extend `test_ui_tabs.py`; optional `test_modern_live_status.py` if helper extracted; `verify_all.py` + full unittest discover  
**Target Platform**: Windows 10+ desktop; Modern UI mode only  
**Performance Goals**: No new timers or bridge-thread callbacks; stylesheet parse size unchanged or smaller after dedupe  
**Constraints**: Constitution I–V; window min 640×420; v1.32.7 Control layout non-regression; Field/Standard `connectGroupBox` untouched  
**Scale/Scope**: ~8 Python/QSS files; 2 UI contracts; 1 doc section; 3–5 new unit tests

## Constitution Check

| Principle | Gate | Pre-design | Post-design |
|-----------|------|------------|-------------|
| I. Bridge-Core Separation | UI-only in `ui/`; no protocol changes | ✅ | ✅ |
| II. Survey Operator Trust | Start/Stop in header unchanged; preset clarity improves connect-first flow | ✅ | ✅ |
| III. Verifiable Changes | New `test_ui_tabs` chrome tests + verify_all in quickstart | ✅ | ✅ |
| IV. Version & Release | v1.33.0 + CHANGELOG; sync `version_info.txt` if packaging touched | ✅ | ✅ |
| V. Resilience | No new queues/events; `_apply_intent_hint_display` remains lightweight | ✅ | ✅ |

**Gate result**: ✅ PASS

## Architecture

### Preset status unification (US1)

```text
┌─────────────────────────────────────────────────────────────┐
│ Presets tab                                                  │
│  lbl_presets_live_status (modernToolsLiveStatus)             │
│    ← format_presets_page_status() → kind: ok|warn|idle       │
│    ← mixin._apply_live_chip() → statusKind + summaryKind     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ shared helper (NEW)
┌─────────────────────────────────────────────────────────────┐
│ ui/modern_live_status.py                                     │
│  apply_modern_live_status(lbl, line, tip, kind)              │
│  map_summary_kind_to_status_kind("ok") → "ready"             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Control tab                                                  │
│  intent_hint → objectName modernToolsLiveStatus              │
│  preset_bar (modernControlPresetBar) — frame only, no blue   │
│    bespoke QSS; background from statusKind on inner label    │
│  _apply_intent_hint_display():                               │
│    line from _intent_hint_text(); kind="ready" if preset     │
└─────────────────────────────────────────────────────────────┘
```

**Kind mapping** (Control shows loaded/active only):

| State | Presets `summaryKind` | Control `statusKind` |
|-------|-------------------------|----------------------|
| Loaded preset | `ok` | `ready` |
| No preset / empty hint | hidden | (bar hidden) |

### Advanced network styling (US2)

Scope QSS under `QFrame#modernControlFormCard QWidget#advancedNetPanel`:

- Nested `QGroupBox` (Mode, UDP remote, TCP server/client) — lighter border, 8px radius
- `QLineEdit`, `QRadioButton`, `QFormLayout` labels — reuse `modernControlFormLabel` equivalent via descendant selector
- No widget tree changes in `controls.py` unless a one-line `setProperty("modernEmbedded", true)` helps QSS scoping

### Module boundaries

| Module | Change |
|--------|--------|
| `ui/modern_live_status.py` | **NEW** — `apply_modern_live_status`, kind mapping, optional `create_modern_live_status_label` |
| `ui/modern.py` | Preset bar wiring; intent hint uses live status; `_apply_intent_hint_display` sets kind |
| `ui/mixin.py` | Delegate `_apply_live_chip` to shared helper (thin wrapper) |
| `ui/modern_styles.py` | Remove `modernControlPresetBar` blue bespoke block; add `advancedNetPanel` rules; dedupe `modernControlTab`; map title 11pt |
| `ui/control_map.py` | Optional: `modernControlMapTitle` objectName unchanged; QSS only |
| `ui/tool_tabs.py` | Import shared label factory from `modern_live_status` |
| `test_ui_tabs.py` | Chrome tests for Control + Hub |
| `docs/OPERATOR_GUIDE.md` | Modern Control + tools nav subsection |

## Project Structure

### Documentation

```text
specs/009-modern-control-polish/
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── control-preset-status-parity.md
│   └── advanced-network-modern-styling.md
└── tasks.md             # /speckit-tasks
```

### Source Code

```text
ui/modern_live_status.py       # NEW — shared live status apply + kind map
ui/modern.py                   # Control preset strip + intent hint kind
ui/mixin.py                    # Use shared apply helper
ui/modern_styles.py            # advancedNetPanel, dedupe, map title
ui/control_map.py              # (optional) title tooltip only
ui/tool_tabs.py                # Import shared label helper
test_ui_tabs.py                # Chrome + regression tests
docs/OPERATOR_GUIDE.md         # ≤150 words new copy
version.py                     # 1.33.0
CHANGELOG.md
```

## Implementation Phases

### Phase A — Preset status parity (US1, FR-201/202) **P1**

1. Add `ui/modern_live_status.py` with `apply_modern_live_status` and `summary_kind_to_status_kind`.
2. Change Control `intent_hint` to `objectName="modernToolsLiveStatus"`; remove bespoke blue `modernControlPresetBar` QSS (frame transparent or inherits ready tint from label).
3. Override `_apply_intent_hint_display` in `modern.py`: after compact elide, set `statusKind="ready"` when text non-empty; call shared apply helper.
4. Refactor mixin `_apply_live_chip` to call shared helper.

**Exit**: Loaded preset on Control and Presets read as same status class (green ready family); strip hidden when empty.

### Phase B — Advanced network + visual hierarchy (US2–US3, FR-203–205) **P2**

1. Add `advancedNetPanel` descendant rules under `modernControlFormCard` in `modern_styles.py`.
2. Change Control preset strip icon from 📋 to **📌** (or remove icon—prefer 📌 per contract).
3. Align `QLabel#modernControlMapTitle` to 11pt / weight 700 (match `modernControlSectionTitle`).

**Exit**: Advanced network expanded at 640×420 readable; no 📋 collision with Activity banner.

### Phase C — Responsive clarity + tests + hygiene (US4–US6, FR-206–210) **P3**

1. Document `CONTROL_FORMS_STACK_BELOW_W = 520` as sub-minimum test-only in `modern.py` + research.md.
2. Add tests: `test_modern_control_page_chrome`, `test_modern_hub_page_banner_no_duplicate_title`.
3. Merge duplicate `QWidget#modernControlTab` QSS blocks.

**Exit**: Tests green; single QSS block; 640px side-by-side regression test still passes.

### Phase D — Docs & release (US7, FR-211) **P3**

1. OPERATOR_GUIDE: Modern Control layout + View → Tools navigation paragraph.
2. Bump `version.py` → **1.33.0**; CHANGELOG; run quickstart gates.

**Exit**: SC-201–SC-205 satisfied; `verify_all.py` pass.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |

## Next Step

Run **`/speckit-tasks`** to generate ordered `tasks.md` from this plan.

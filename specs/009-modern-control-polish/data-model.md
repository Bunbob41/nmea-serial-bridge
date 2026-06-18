# Data Model: Modern Control Tab Polish

**Feature**: `009-modern-control-polish` | **Date**: 2026-06-17

## PresetSummaryPresentation

Runtime UI state for how preset/session summary text is shown on Modern surfaces. Not persisted.

| Field | Type | Notes |
|-------|------|-------|
| `line` | string | Single-line elided text (Control intent hint or Presets live status) |
| `tooltip` | string | Full text on hover |
| `summary_kind` | enum | `ok` \| `warn` \| `idle` — from `format_presets_page_status` on Presets |
| `status_kind` | enum | `ready` \| `idle` \| `recording` \| `error` — Qt property on `modernToolsLiveStatus` |
| `visible` | bool | False when line empty (Control preset bar hidden) |

**Mapping** (`summary_kind` → `status_kind` for Control):

| summary_kind | status_kind | When |
|--------------|-------------|------|
| `ok` | `ready` | Loaded preset active |
| `idle` | `idle` | Session UI only (Presets); Control bar hidden |
| `warn` | — | Presets preview only; not shown on Control |

**Lifecycle**: `hidden → ready (on preset load) → hidden (clear preset / empty hint)`

---

## ControlPageChrome

Logical regions on Modern Control tab (v1.32.7 baseline + this epic).

| Region | objectName(s) | Stretch behavior |
|--------|---------------|------------------|
| Page header | `modernToolsPageHeader`, `modernToolsPageTitle` | Fixed |
| Forms host | `modernControlFormsHost`, `modernControlFormCard` ×2 | Side-by-side ≥640px width |
| Preset strip | `modernControlPresetBar`, inner `modernToolsLiveStatus` | Fixed; hidden when idle |
| Position track | `modernControlMapCard`, `modernControlMap` | Collapsed: stretch tail; expanded: stretch map |

**Invariants**:

- Serial and Network cards remain side-by-side at window minimum 640×420.
- Preset strip MUST NOT show orphan icon when label hidden.
- Page banner icon (🎛) matches Control nav chip.

---

## ResponsiveFormsLayout

| Field | Type | Notes |
|-------|------|-------|
| `stack_below_width` | int | `520` — `CONTROL_FORMS_STACK_BELOW_W` |
| `is_vertical` | bool | `_control_forms_vertical` on Modern window |
| `window_min_width` | int | `640` — app minimum |

**Rule**: At `width >= 640`, `is_vertical` MUST be `false`.

---

## AdvancedNetworkPanelScope

Embedded widget tree under Network card when `chk_advanced_net` checked.

| Child | objectName | Modern styling scope |
|-------|------------|----------------------|
| Root | `advancedNetPanel` | Descendant of `modernControlFormCard` |
| Mode group | `QGroupBox` "Mode" | Nested group — lighter border in Modern QSS |
| UDP/TCP boxes | `_udp_box`, `_tcp_srv_box`, `_tcp_cli_box` | Form fields match card inputs |

**Validation**: Expanded panel at 640×420 — no clipped host/port rows (manual SC-202).

---

## LiveStatusHelper (behavioral)

Module: `ui/modern_live_status.py`

| Operation | Input | Effects |
|-----------|-------|---------|
| `apply_modern_live_status(lbl, line, tip, kind)` | QLabel, strings, kind | setText, tooltip, `statusKind` property, unpolish/polish |
| `summary_kind_to_status_kind(summary_kind)` | string | Returns mapped status kind |

**Consumers**: `BridgeLogicMixin._refresh_tools_page_status`, `BridgeWindowModern._apply_intent_hint_display`.

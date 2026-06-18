# Research: Modern Control Tab Polish

**Feature**: `009-modern-control-polish` | **Date**: 2026-06-17

## R1 — Preset status styling strategy

**Decision**: Reuse **`modernToolsLiveStatus`** widget + **`statusKind`** dynamic property on Control `intent_hint`; extract **`apply_modern_live_status()`** to `ui/modern_live_status.py` shared by mixin Presets refresh and Modern Control.

**Rationale**:

- Presets tab already uses `format_presets_page_status()` → `_apply_live_chip()` with `summaryKind` `ok|warn|idle` ([`ui/backup_status.py`](../../ui/backup_status.py), [`ui/mixin.py`](../../ui/mixin.py)).
- Control preset strip uses bespoke `modernControlPresetBar` blue QSS ([`ui/modern_styles.py`](../../ui/modern_styles.py) ~448)—same semantic info, different visual language (audit finding).
- Control shows **loaded/active** preset only via `_intent_hint_text()`—no preview/warn state needed on Control (spec assumption).

**Kind mapping**:

| Presets `summaryKind` | `modernToolsLiveStatus` `statusKind` |
|-----------------------|--------------------------------------|
| `ok` | `ready` |
| `warn` | (Presets only—not used on Control) |
| `idle` | `idle` |
| `recording` | (Black box / activity—not Control preset) |

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Keep blue `modernControlPresetBar` and tint Presets green to match | Wrong direction—Presets pattern is established across Tools pages |
| Duplicate QSS on `modernIntentHint` mimicking ready colors | Drift on next theme edit (FR-202) |
| Replace intent_hint with `lbl_presets_live_status` on Control | Different text sources; intent hint is bridge-state aware |

---

## R2 — Advanced network panel styling

**Decision**: **Stylesheet descendant selectors** only—no structural refactor of `controls.py` advanced panel.

**Rationale**:

- `advancedNetPanel` is built once in `create_connection_controls()` with nested `QGroupBox` widgets ([`ui/controls.py`](../../ui/controls.py) ~351+).
- Modern Network card wraps the same widgets; QSS scope `QFrame#modernControlFormCard QWidget#advancedNetPanel …` styles all modes without breaking Standard/Field (panel outside `modernControlFormCard` there).

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Split `create_advanced_net_panel(modern=True)` | Duplicates wiring; higher regression risk |
| Inline advanced fields without GroupBoxes in Modern only | Breaks parity with Standard advanced net layout |

---

## R3 — Icon and typography

**Decision**:

- Control preset strip icon: **📌** (loaded/active bookmark semantics).
- Activity page banner keeps **📋** (wire-tap / log housekeeping).
- Position track: bump **`modernControlMapTitle`** QSS to 11pt / weight 700 via stylesheet only.

**Rationale**: Minimal diff; satisfies FR-204/205 without renaming Activity page.

---

## R4 — Responsive stack threshold

**Decision**: **Retain** vertical stack code path at `CONTROL_FORMS_STACK_BELOW_W = 520` with explicit comment **“below window minimum; test-only”**; keep unit test that exercises stack at 480px simulated width.

**Rationale**:

- Operator-approved layout at 640×420 requires side-by-side (v1.32.7 fix).
- Removing stack code simplifies but loses regression test for future min-width changes.
- Documented dead path is honest (FR-207) without deleting test coverage.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Remove stack entirely | Loses test hook if min width ever drops |
| Raise threshold to 640 | Stack never runs even in tests |

---

## R5 — Test strategy

**Decision**: Extend **`test_ui_tabs.py`** with:

1. `test_modern_control_page_chrome` — `modernToolsPageHeader`, `modernControlPresetBar`, `modernToolsLiveStatus` on intent hint.
2. `test_modern_hub_page_banner` — header exists; `connectionHubTitle` absent when embedded in Modern Hub page.

**Rationale**: Constitution III; no QTest pixel tests; matches 008 local-only validation pattern.

---

## R6 — Stylesheet deduplication

**Decision**: Merge duplicate `QWidget#modernControlTab { background-color }` into the Control tab section (~line 375); remove duplicate in Tools page list block (~line 951) by keeping single rule in Control section only.

**Rationale**: SC-204; zero operator-visible change if colors identical.

---

## R7 — Operator guide scope

**Decision**: Add **≤150 words** in `docs/OPERATOR_GUIDE.md` under existing Connect/setup flow:

- Modern Control: banner, Serial/Network cards, preset strip, Hub/Presets before Start.
- View → Tools navigation: Sidebar vs Top chips.

**Rationale**: Constitution workflow gate; no README change required.

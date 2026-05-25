# UI audit inventory — feature 008

**Feature**: `specs/008-ui-journey-modernization` (US2, FR-101–105)  
**Gate**: Zero open **P0** at ship  
**Layouts**: STD = Standard, FIELD = Field, MIN/LOG = legacy aliases → Field

| ID | Layout | Area | Type | Severity | Status | Notes / release |
|----|--------|------|------|----------|--------|-----------------|
| STD-CONNECT-01 | standard | Connect / Run | layout | P0 | fixed | Start/Stop fixed height + max width; run panel uses Maximum vertical policy (v1.9.81+) |
| STD-CONNECT-02 | standard | Connect / toolbar | dead_control | P0 | fixed | **Reset sizes** removed; prefs strip `reset_sizes` (v1.9.84) |
| STD-CONNECT-03 | standard | Connect / Serial+Network | layout | P0 | fixed | Side-by-side row at 1280×720 (v1.9.81) |
| STD-STATUS-01 | standard | Status banner | layout | P1 | fixed | Rich HTML banner wraps; min window 900×480 |
| FIELD-CONNECT-01 | field | Control strip | layout | P0 | fixed | Start/Stop in strip; min 720×480 |
| FIELD-STATUS-01 | field | status_line | copy | P1 | fixed | Plain-text status; preset shown in connect summary (v1.9.86) |
| MIN-CONNECT-01 | field | — | layout | P0 | fixed | Minimal → Field alias (`ui/registry.py`) |
| LOG-CONNECT-01 | field | — | layout | P0 | fixed | Log-first → Field alias |
| STD-TOOLS-PRESETS-01 | standard | Tools / Presets | copy | P1 | fixed | NMEA in preset save/load; hints aligned with operator guide |
| STD-TOOLS-PHONE-01 | standard | Tools / Phone | placeholder | P0 | fixed | QR shows when token saved; auto **Show QR** on prefs restore (v1.9.86) |
| STD-TOOLS-PHONE-02 | standard | Tools / Phone | layout | P0 | fixed | `webPortSpin` step buttons visible (v1.9.82–83) |
| STD-TOOLS-PHONE-03 | standard | Connect overlay | placeholder | P0 | fixed | Floating QR hidden on Tools → Phone (v1.9.83) |
| FIELD-TOOLS-PHONE-01 | field | Tools / Phone | placeholder | P0 | fixed | Same Phone tab + QR behavior as Standard |
| STD-TOOLS-NMEA-01 | standard | Tools / NMEA | copy | P1 | fixed | Mode chips + status chip tooltips |
| STD-TOOLS-GUIDE-01 | standard | Tools / Guide | copy | P2 | fixed | Operator guide linked from Guide tab |
| STD-TOOLS-DIAG-01 | standard | Tools / Diagnostics | copy | P1 | fixed | Bench scripts documented in operator guide |
| STD-VIEW-DEMO-01 | standard | View / Demo | copy | P1 | fixed | Session restore on close (v1.9.85) |
| STD-MENU-RECENT-01 | all | Survey bar / Recent | copy | P1 | fixed | Label includes `nmea_mode` suffix |
| WEB-DASH-01 | web | dashboard | copy | P2 | deferred | US4 — dashboard empty-state vs desktop token (T037–T040) |

## Verification log

| Date | Layouts | Resolution | P0 open |
|------|---------|------------|---------|
| 2026-05-24 | STD, FIELD @ 1280×720 | Manual + `test_ui_prefs` toolbar migration | 0 |

## Deferred (non-P0)

- **WEB-DASH-01**: Phone handoff copy on static dashboard (Phase US4).

# Contract: UI & Information Audit Matrix

**Feature**: `008-ui-journey-modernization` (US2, FR-101–105)

## Inventory format

Each row in `docs/ui-audit-inventory.md` (created during implement) follows:

| Column | Description |
|--------|-------------|
| ID | `{LAYOUT}-{AREA}-{NN}` e.g. `STD-CONNECT-01` |
| Layout | standard \| field \| minimal \| logfirst |
| Area | Connect, Tools/Presets, Tools/Phone, Tools/NMEA, Guide, Status, View menu, Demo |
| Type | copy \| layout \| placeholder \| dead_control |
| Severity | P0 \| P1 \| P2 |
| Status | open \| fixed \| deferred |

## P0 definition (ship blocker)

- Misleading placeholder when real data exists (e.g. QR “generate token” with token set)
- Clipped Start/Stop or status chips at 1280×720 default window
- Dead toolbar control that implies behavior but does nothing

## P1 definition

- Terminology mismatch vs `docs/OPERATOR_GUIDE.md`
- Redundant or obsolete hints after layout refactor (e.g. splitter/Reset sizes references)

## Verification

- Manual pass per layout at 1280×720 and 1440×900
- Optional: screenshot filenames in `docs/screenshots/audit-008/` (operator doc only)
- No agent-browser requirement

## Ship gate

Zero open P0; P1 either fixed or listed in `CHANGELOG.md` deferred section with one-line operator note.

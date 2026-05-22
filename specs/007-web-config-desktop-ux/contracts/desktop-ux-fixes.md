# Contract: Desktop UX Fixes (Field + Standard)

## Field — Guide tab Web control (FR-301/302)

- `build_guide_tab` root: `QScrollArea` → inner widget with `QVBoxLayout`
- Web group box minimum height ≥ 220px
- Form layout vertical spacing ≥ 8px
- All rows fully visible at 1024×768 with Tools drawer open on Guide tab

## Standard — COM dropdown (FR-401)

- After `refresh_ports()`: if previous `currentText()` still in list, reselect it
- If list empty: show placeholder item "(no ports — click Refresh)"
- `InsertPolicy.NoInsert` after population

## Standard — Connect resize (FR-402/403)

- `_connect_panel_splitter` objectName `connectPanelSplitter`
- Handles visible (min 6px per styles.py)
- Toolbar **Reset sizes** restores `_DEFAULT_PANEL_HEIGHTS` and splitter distribution
- `splitterMoved` persists to `connect_panel` prefs

## Verification

- Manual: 3 launches Field @ 1024×768, zero clip
- Manual: Standard COM 10× open/close dropdown
- Manual: drag Connect splitter, restart, ±10% size restore

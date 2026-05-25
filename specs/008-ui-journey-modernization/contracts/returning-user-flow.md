# Contract: Returning User Flow

**Feature**: `008-ui-journey-modernization` (US1, FR-201–205)

## Launch restore

On cold start with bridge **stopped**:

1. Load `last_preset` from `bench_config` / `path_presets.json`.
2. Call `_activate_preset_by_name(last_preset, log=False)` or equivalent single path.
3. Surface active preset in UI (preset list selection + quick menu check state).

## Recent sessions

- Menu label format: `{com} @ {baud} · {host}:{port} · {nmea_mode}` (already in mixin; verify all layouts expose menu).
- Apply via `_apply_recent_session` when stopped; running → stop-first message.

## Layout prefs

- `load_connect_panel_prefs(ui_mode)` migrates toolbar order (drops removed keys).
- Ignores invalid saved panel heights per `_MIN_VALID_SAVED_HEIGHT`.

## Web handoff (US4)

- `_restore_web_ui_prefs` triggers `_refresh_phone_tab_qr`.
- Floating QR hidden on Tools → Phone tab (007/008 behavior).

## Verification (local)

- `test_path_presets.py` (existing) + `test_ui_prefs.py` toolbar migration
- Manual quickstart § Returning user

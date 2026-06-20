# Contract: Fleet Persistence

**Feature**: [`spec.md`](../spec.md)  
**Model**: [`data-model.md`](../data-model.md)

---

## File location

| File | Path |
|------|------|
| Fleet config | `%USERPROFILE%\.cursor-udp-com-bridge\fleet_config.json` |
| Per-stream backup logs | `%USERPROFILE%\.cursor-udp-com-bridge\logs\{stream_label}\` (if enabled) |

Use same config root as existing prefs (`bench_config` / mixin helpers).

---

## Schema versioning

- `schema_version: 1` for initial ship
- Unknown future fields: preserve on load (forward compatible)
- Breaking change: bump version + migration function in `fleet_config.py`

---

## Import / export

| Action | Behavior |
|--------|----------|
| Export | Save As JSON; include `schema_version`, optional `exported_at` |
| Import | Merge or replace — **v1: replace with confirm** |
| Invalid import | Show validation errors; do not partial-apply |

---

## Preset integration (optional helper)

- Button: **Load from preset…** on stream dialog
- Copies compatible fields from `path_presets.json` entry into row
- Does not auto-link — fleet row is snapshot unless operator re-loads

---

## Auto-start preference

Stored in `FleetConfig.auto_start_on_launch` (not separate file).

---

## Security

- No secrets in fleet JSON beyond existing prefs norms
- NTRIP credentials remain out of fleet v1 scope

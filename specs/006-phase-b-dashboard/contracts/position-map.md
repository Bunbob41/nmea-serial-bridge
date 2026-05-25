# Position map (web dashboard)

**Status**: Shipped (web only). **HUD**: reserved — consume `bridge.navigation_position()` or `/status` `position_*` fields later.

## `/status` fields

| Field | Type | Description |
|-------|------|-------------|
| `position_lat` | float \| null | WGS84 latitude (decimal degrees) |
| `position_lon` | float \| null | WGS84 longitude |
| `position_source` | string | `gga` or `rmc` (last parser that updated the fix) |
| `position_stale` | bool | True when GGA quality is stale / idle (same ~2 s window as GNSS chip) |

Parsing lives in `nmea_position.py` on the bridge thread. Raw NMEA mode does not populate position.

## Web UI

- Dashboard panel **Position map** — checkbox **Show map** (`localStorage` key `nmea-bridge-map-enabled`).
- Vendored **Leaflet** under `web/static/vendor/leaflet/`.
- Raster tiles: **OpenStreetMap** (`tile.openstreetmap.org`) when the PC has network; not bundled.

## Future HUD (not implemented)

- Read-only: `SerialNetBridge.navigation_position()` → `{ lat, lon, source, stale }`.
- Optional track ring buffer may move server-side later; web currently keeps a short client-side polyline.

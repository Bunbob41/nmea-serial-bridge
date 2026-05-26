# Dashboard — GridStack layout (beta)

**Status:** Experimental — does **not** replace the default dashboard.

| URL (with Web API running) | Layout |
|----------------------------|--------|
| `http://127.0.0.1:8765/` or `/static/layouts/gridstack/` | **GridStack** (default — customizable tiles) |
| `http://127.0.0.1:8765/static/index.html` | **Classic standard** (backup — single-page accordion layout) |

## What this is

- Same **`dashboard.js`** and FastAPI routes as the standard page.
- **[GridStack](https://gridstackjs.com/)** 10.3.1 (vendored under `web/static/vendor/gridstack/`) for drag-and-resize tiles.
- Layout persisted in browser `localStorage` key `nmea-gridstack-layout-v2` (separate from standard panel order). Use **Reset layout** in the blue banner if tiles are stuck on the left.
- **▲▼** on each section header — swap tile position with the neighbor above/below (same as standard dashboard).
- **Drag** header to move; **resize** from tile corners; **collapse** shrinks tile height.
- **Lock layout:** header checkbox **Lock layout** — when checked, tiles cannot be dragged, resized, or ▲▼ reordered; current layout is saved. Uncheck to customize again.
- **Resize:** blue bar on **bottom** (height), **left** and **right** edges (width). **Hide resize bars** via ⋯ or long-press menu (saved in browser).
- **Layout options (phone):** tap **⋯** on the section header, or **long-press** the section (~½ second). Desktop: right-click still works.
- Menu: hide header, hide all headers, **Terminal only** (log), **Prioritize map** (map), Survey monitor **Rows / Columns / Simple**. Tap again to restore.
- **Map ⋯** — Center on fix, fit/clear track, show/hide track, refresh map size. **Log ⋯** — pause, auto-scroll, clear, expand. **Discovery / COM / Tools** — refresh and unlock shortcuts.

## Frozen baseline

The standard dashboard before this experiment is snapshotted at:

- `web/static/layouts/1.0/` (updated to match **v1.10.0** when GridStack work started)

To restore standard layout manually, copy those three files back to `web/static/`.

## Regenerate grid HTML

If `web/static/index.html` changes, regenerate the grid page:

```powershell
python tools/build_gridstack_index.py
```

## Roadmap (grid-first)

- **Resize-aware panels** — tune Survey monitor, log, and tools density when tiles are short vs tall.
- **Map tile** — stronger small/medium/large tile behavior (track, zoom, invalidate on resize).
- **More tile tools** — extend chrome menus and panel actions without changing the standard layout.

## Known limits

- Phone/touch drag is less polished than ▲▼ nudge on standard layout.
- Map tile still needs network (OSM).
- Do not edit `layouts/gridstack/index.html` by hand — use the builder script.

"""One-off generator: web/static/layouts/gridstack/index.html from live index.html."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "web" / "static"
# x, y, w, h on 12-column grid (survey-friendly 2-column default)
GRID_ITEMS = {
    "com-setup": (0, 0, 6, 4),
    "status": (6, 0, 6, 5),
    "map": (0, 5, 6, 4),
    "configuration": (6, 5, 6, 4),
    "tools": (0, 9, 4, 4),
    "discovery": (4, 9, 8, 4),
    "log": (0, 13, 12, 6),
}


def main() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    html = html.replace("<body>", '<body class="layout-gridstack">', 1)
    html = html.replace(
        "<title>NMEA Bridge Dashboard</title>",
        "<title>NMEA Bridge Dashboard (Grid beta)</title>",
        1,
    )
    html = html.replace(
        '<link rel="stylesheet" href="/static/vendor/leaflet/leaflet.css" />',
        '<link rel="stylesheet" href="/static/vendor/leaflet/leaflet.css" />\n'
        '  <link rel="stylesheet" href="/static/vendor/gridstack/gridstack.min.css" />\n'
        '  <link rel="stylesheet" href="/static/layouts/gridstack/gridstack-layout.css" />',
        1,
    )
    html = html.replace(
        '<main class="dashboard" id="dashboard-panels">',
        '<p class="layout-beta-banner"><a href="/static/index.html">&larr; Standard layout</a> '
        "&middot; Customize tiles, then check <strong>Lock layout</strong> in the header. "
        "Blue bars resize; ⋯ or long-press for options. "
        '<button type="button" class="layout-beta-reset" id="btn-gridstack-reset">Reset layout</button></p>\n'
        '  <main class="dashboard layout-gridstack-main">\n'
        '  <div class="grid-stack" id="dashboard-panels">',
        1,
    )

    def wrap_open(m: re.Match[str]) -> str:
        tag = m.group(0)
        pm = re.search(r'data-panel="([^"]+)"', tag)
        pid = pm.group(1) if pm else "panel"
        x, y, w, h = GRID_ITEMS.get(pid, (0, 0, 4, 3))
        return (
            f'<div class="grid-stack-item" gs-id="{pid}" gs-x="{x}" gs-y="{y}" '
            f'gs-w="{w}" gs-h="{h}">'
            f'<div class="grid-stack-item-content">{tag}'
        )

    html = re.sub(
        r'<section class="card [^"]*dashboard-panel[^"]*"[^>]*data-panel="[^"]+"[^>]*>',
        wrap_open,
        html,
    )

    lines = html.splitlines()
    result: list[str] = []
    in_grid = False
    for i, line in enumerate(lines):
        result.append(line)
        if 'id="dashboard-panels"' in line and "grid-stack" in line:
            in_grid = True
            continue
        if not in_grid:
            continue
        if line.strip() != "</section>":
            continue
        nxt = ""
        for j in range(i + 1, min(i + 5, len(lines))):
            s = lines[j].strip()
            if s:
                nxt = s
                break
        if nxt.startswith("<!--") or nxt.startswith("</div>") or nxt.startswith("</main>"):
            result.append("    </div></div>")

    html = "\n".join(result)
    html = html.replace("  </main>", "  </div>\n  </main>", 1)
    html = html.replace(
        '<script src="/static/vendor/leaflet/leaflet.js"></script>\n'
        "  <script src=\"/static/dashboard.js\"></script>",
        '<script src="/static/vendor/leaflet/leaflet.js"></script>\n'
        '  <script src="/static/vendor/gridstack/gridstack-all.js"></script>\n'
        '  <script src="/static/dashboard.js"></script>\n'
        '  <script src="/static/layouts/gridstack/gridstack-layout.js"></script>',
        1,
    )

    out_dir = ROOT / "layouts" / "gridstack"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html + "\n", encoding="utf-8")
    print(f"Wrote {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()

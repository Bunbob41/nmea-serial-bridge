"""One-off generator: web/static/layouts/gridstack/index.html from live index.html."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "web" / "static"
REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from tools.read_version import read_app_version
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
    ver = read_app_version()
    dash_src = f"/static/dashboard.js?v={ver}"
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    html = html.replace("<body>", '<body class="layout-gridstack">', 1)
    html = html.replace(
        "<title>Serial Link Dashboard</title>",
        "<title>Serial Link Dashboard (Grid)</title>",
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
    html = re.sub(
        r'<script src="/static/vendor/leaflet/leaflet\.js"></script>\s*<script src="/static/dashboard\.js[^"]*"></script>',
        '<script src="/static/vendor/leaflet/leaflet.js"></script>\n'
        '  <script src="/static/vendor/gridstack/gridstack-all.js"></script>\n'
        f'  <script src="{dash_src}"></script>\n'
        '  <script src="/static/layouts/gridstack/gridstack-layout.js"></script>',
        html,
        count=1,
    )
    html = html.replace(
        '<span class="footer-layout-link"> · <a href="/">Grid dashboard (default)</a></span>',
        '<span class="footer-layout-link"> · <a href="/static/index.html">Classic layout</a></span>\n'
        '    <span class="footer-layout-actions"> · '
        '<button type="button" class="footer-layout-reset" id="btn-gridstack-reset" '
        'title="Restore default tile positions (clears saved grid layout)">Reset layout</button></span>',
        1,
    )

    out_dir = ROOT / "layouts" / "gridstack"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html + "\n", encoding="utf-8")
    print(f"Wrote {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()

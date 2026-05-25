"""Inject LAN API token into agent-browser session for dashboard QA."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOKEN_KEY = "nmea-bridge-web-token"
PREFS = Path.home() / ".cursor-udp-com-bridge" / "ui_prefs.json"


def main() -> int:
    raw = json.loads(PREFS.read_text(encoding="utf-8"))
    tok = str(raw.get("web_ui", {}).get("token") or "").strip()
    if not tok:
        print("No web_ui.token in ui_prefs.json", file=sys.stderr)
        return 1
    js = (
        f"localStorage.setItem({json.dumps(TOKEN_KEY)}, {json.dumps(tok)}); "
        f"token = {json.dumps(tok)};"
    )
    subprocess.run(["agent-browser", "eval", js], check=True)
    subprocess.run(["agent-browser", "reload"], check=True)
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

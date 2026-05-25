import json
from pathlib import Path

prefs = Path.home() / ".cursor-udp-com-bridge" / "ui_prefs.json"
out = Path(__file__).resolve().parents[1] / ".cursor" / "artifacts" / "inject-token.js"
t = str(json.loads(prefs.read_text(encoding="utf-8"))["web_ui"]["token"]).strip()
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    f"localStorage.setItem('nmea-bridge-web-token', {json.dumps(t)}); token = {json.dumps(t)};",
    encoding="utf-8",
)
print(out)
